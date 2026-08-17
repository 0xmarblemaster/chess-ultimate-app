/**
 * POST /api/chess-empire/gamification/sync
 *
 * CRON_SECRET-guarded gamification ingestion (PRD §5.3). For every org with a
 * gamification_settings row it: pulls new CE tournament_results from the sync
 * cursor forward, awards XP+coins idempotently, replays streak bonuses, reverses
 * deleted results, and recomputes the player_gamification read model.
 *
 * Zero-start (D-5): on first run the cursor is pinned to "now" so historical
 * results are never awarded. Read-only against the CE DB.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase-admin';
import {
  getExistingResultIds,
  getTournamentResultsSince,
} from '@/lib/chess-empire-client';
import { getOrgConfig, getRanks, recomputePlayers } from '@/lib/gamification/store';
import {
  type AwardedResult,
  type CoinLedgerInsert,
  type XpLedgerInsert,
  planReversals,
  planStreakAwards,
  planTournamentAwards,
} from '@/lib/gamification/sync-core';

export const dynamic = 'force-dynamic';

const MAX_RESULTS_PER_RUN = 500;

function authorized(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET;
  if (!secret) return false; // fail closed if unconfigured
  const bearer = req.headers.get('authorization')?.replace(/^Bearer\s+/i, '');
  const header = req.headers.get('x-cron-secret');
  return bearer === secret || header === secret;
}

async function insertLedgers(xpRows: XpLedgerInsert[], coinRows: CoinLedgerInsert[]) {
  if (xpRows.length) {
    await supabaseAdmin
      .from('xp_ledger')
      .upsert(xpRows, { onConflict: 'idempotency_key', ignoreDuplicates: true });
  }
  if (coinRows.length) {
    await supabaseAdmin
      .from('coin_ledger')
      .upsert(coinRows, { onConflict: 'idempotency_key', ignoreDuplicates: true });
  }
}

function num(v: unknown): number {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return Number.isFinite(n) ? n : 0;
}

/** Reverse awarded tournament results that no longer exist in CE (§5.2). */
async function runReversalPass(orgId: string): Promise<Set<string>> {
  // Awarded tournament rows not yet reversed.
  const { data: awardedXp } = await supabaseAdmin
    .from('xp_ledger')
    .select('student_id,source_id,amount,wins,occurred_at')
    .eq('organization_id', orgId)
    .eq('reason', 'tournament');
  const { data: reversed } = await supabaseAdmin
    .from('xp_ledger')
    .select('source_id')
    .eq('organization_id', orgId)
    .eq('reason', 'ce_result_reversed');
  const { data: coinRowsData } = await supabaseAdmin
    .from('coin_ledger')
    .select('source_id,amount')
    .eq('organization_id', orgId)
    .eq('source', 'earn_xp');

  const reversedIds = new Set((reversed ?? []).map((r) => r.source_id as string));
  const coinBySource = new Map<string, number>();
  for (const c of coinRowsData ?? []) coinBySource.set(c.source_id as string, num(c.amount));

  const awarded: AwardedResult[] = (awardedXp ?? [])
    .filter((r) => r.source_id && !reversedIds.has(r.source_id as string))
    .map((r) => ({
      organization_id: orgId,
      student_id: r.student_id as string,
      source_id: r.source_id as string,
      amount: num(r.amount),
      coin_amount: coinBySource.get(r.source_id as string) ?? num(r.amount),
      wins: num(r.wins),
      occurred_at: r.occurred_at as string,
    }));

  if (awarded.length === 0) return new Set();

  const existing = await getExistingResultIds(awarded.map((a) => a.source_id));
  const { xpRows, coinRows, touchedStudents } = planReversals(awarded, existing);
  await insertLedgers(xpRows, coinRows);
  return touchedStudents;
}

interface OrgSyncSummary {
  organization_id: string;
  awarded: number;
  reversed: number;
  streakAwards: number;
  touched: number;
  skipped: number;
  cursor: string | null;
  status: string;
  error?: string;
}

async function syncOrg(orgId: string): Promise<OrgSyncSummary> {
  const nowIso = new Date().toISOString();
  const summary: OrgSyncSummary = {
    organization_id: orgId,
    awarded: 0,
    reversed: 0,
    streakAwards: 0,
    touched: 0,
    skipped: 0,
    cursor: null,
    status: 'ok',
  };

  try {
    // 1. Resolve / initialize the cursor (zero-start).
    const { data: state } = await supabaseAdmin
      .from('gamification_sync_state')
      .select('*')
      .eq('organization_id', orgId)
      .maybeSingle();

    if (!state) {
      await supabaseAdmin.from('gamification_sync_state').insert({
        organization_id: orgId,
        cursor_initialized_at: nowIso,
        last_result_created_at: nowIso,
        last_run_at: nowIso,
        last_status: 'initialized',
      });
      summary.status = 'initialized';
      summary.cursor = nowIso;
      return summary; // no historical awards
    }

    const cursor = (state.last_result_created_at || state.cursor_initialized_at || nowIso) as string;

    // 2. Fetch + plan tournament awards.
    const results = await getTournamentResultsSince(cursor, MAX_RESULTS_PER_RUN);
    const plan = planTournamentAwards(orgId, results, await getOrgConfig(orgId));
    await insertLedgers(plan.xpRows, plan.coinRows);
    summary.awarded = plan.xpRows.length;
    summary.skipped = plan.skipped;

    // 3. Reverse deleted/re-uploaded results.
    const reversalTouched = await runReversalPass(orgId);
    summary.reversed = reversalTouched.size;

    // 4. Streaks — replay each touched student's full participation history.
    const config = await getOrgConfig(orgId);
    const touched = new Set<string>([...plan.touchedStudents, ...reversalTouched]);
    for (const sid of touched) {
      const { data: partRows } = await supabaseAdmin
        .from('xp_ledger')
        .select('occurred_at')
        .eq('organization_id', orgId)
        .eq('student_id', sid)
        .eq('reason', 'tournament');
      const occurredAts = (partRows ?? []).map((r) => r.occurred_at as string);
      const streak = planStreakAwards(orgId, sid, occurredAts, config);
      await insertLedgers(streak.xpRows, streak.coinRows);
      summary.streakAwards += streak.xpRows.length;
      await supabaseAdmin.from('streak_state').upsert(
        {
          organization_id: orgId,
          student_id: sid,
          current_weeks: streak.state.current_weeks,
          best_weeks: streak.state.best_weeks,
          run_start_week: streak.state.run_start_week,
          last_active_week: streak.state.last_active_week,
          updated_at: nowIso,
        },
        { onConflict: 'organization_id,student_id' },
      );
    }

    // 5. Recompute read model.
    const ranks = await getRanks(orgId);
    await recomputePlayers(orgId, [...touched], ranks);
    summary.touched = touched.size;

    // 6. Advance cursor.
    const newCursor = plan.maxCreatedAt && plan.maxCreatedAt > cursor ? plan.maxCreatedAt : cursor;
    summary.cursor = newCursor;
    await supabaseAdmin
      .from('gamification_sync_state')
      .update({
        last_result_created_at: newCursor,
        last_run_at: nowIso,
        last_status: 'ok',
        last_error: null,
      })
      .eq('organization_id', orgId);
  } catch (err) {
    summary.status = 'error';
    summary.error = (err as Error)?.message ?? String(err);
    await supabaseAdmin
      .from('gamification_sync_state')
      .update({ last_run_at: nowIso, last_status: 'error', last_error: summary.error })
      .eq('organization_id', orgId);
  }

  return summary;
}

export async function POST(req: NextRequest) {
  if (!authorized(req)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { data: orgs } = await supabaseAdmin
    .from('gamification_settings')
    .select('organization_id');

  const results: OrgSyncSummary[] = [];
  for (const o of orgs ?? []) {
    results.push(await syncOrg(o.organization_id as string));
  }

  return NextResponse.json({ ok: true, ran_at: new Date().toISOString(), orgs: results });
}

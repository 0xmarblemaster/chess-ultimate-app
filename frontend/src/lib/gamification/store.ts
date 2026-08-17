/**
 * Gamification persistence helpers (service-role Supabase IO).
 *
 * Thin wrappers over `supabaseAdmin` for reading org config / rank ladder and
 * recomputing the `player_gamification` read model from the ledgers. All balance
 * columns are SUM(ledger) — never incremented in place (§5.2).
 */
import 'server-only';
import { supabaseAdmin } from '@/lib/supabase-admin';
import {
  type GamificationConfig,
  type RankRow,
  normalizeConfig,
  rankForXp,
  roundHalf,
} from './economy';
import {
  type GamificationProfile,
  type PlayerRow,
  type StreakRow,
  buildProfile,
} from './profile';

function num(v: unknown): number {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return Number.isFinite(n) ? n : 0;
}

/** Org gamification config, merged over defaults. */
export async function getOrgConfig(orgId: string): Promise<GamificationConfig> {
  const { data } = await supabaseAdmin
    .from('gamification_settings')
    .select('config')
    .eq('organization_id', orgId)
    .maybeSingle();
  return normalizeConfig(data?.config);
}

/** Org rank ladder, ascending by sort_order. */
export async function getRanks(orgId: string): Promise<RankRow[]> {
  const { data } = await supabaseAdmin
    .from('gamification_ranks')
    .select('code,name_ru,name_kk,name_en,min_xp,icon_url,sort_order')
    .eq('organization_id', orgId)
    .order('sort_order', { ascending: true });
  return (data ?? []).map((r) => ({ ...r, min_xp: num(r.min_xp) })) as RankRow[];
}

/**
 * Load the full client-facing gamification profile for a linked student.
 * Shared by the profile API route and the Empire homepage render pipeline.
 */
export async function loadGamificationProfile(
  orgId: string,
  studentId: string,
): Promise<GamificationProfile> {
  const [{ data: player }, { data: streak }, ranks, config] = await Promise.all([
    supabaseAdmin
      .from('player_gamification')
      .select('xp_total,coin_balance,rank_code,tournaments_played,wins_total')
      .eq('organization_id', orgId)
      .eq('student_id', studentId)
      .maybeSingle(),
    supabaseAdmin
      .from('streak_state')
      .select('current_weeks,best_weeks,run_start_week,last_active_week')
      .eq('organization_id', orgId)
      .eq('student_id', studentId)
      .maybeSingle(),
    getRanks(orgId),
    getOrgConfig(orgId),
  ]);
  return buildProfile(
    studentId,
    (player as PlayerRow | null) ?? null,
    (streak as StreakRow | null) ?? null,
    ranks,
    config,
  );
}

export interface PlayerAggregate {
  xp_total: number;
  coin_balance: number;
  rank_code: string | null;
  tournaments_played: number;
  wins_total: number;
}

/**
 * Recompute the read model for a set of students from their ledger rows and
 * upsert `player_gamification`. Returns the computed aggregates by student id.
 */
export async function recomputePlayers(
  orgId: string,
  studentIds: string[],
  ranks: RankRow[],
): Promise<Record<string, PlayerAggregate>> {
  const out: Record<string, PlayerAggregate> = {};
  const nowIso = new Date().toISOString();

  for (const sid of studentIds) {
    const [{ data: xpRows }, { data: coinRows }] = await Promise.all([
      supabaseAdmin
        .from('xp_ledger')
        .select('amount,reason,wins')
        .eq('organization_id', orgId)
        .eq('student_id', sid),
      supabaseAdmin
        .from('coin_ledger')
        .select('amount')
        .eq('organization_id', orgId)
        .eq('student_id', sid),
    ]);

    let xpTotal = 0;
    let winsTotal = 0;
    let tournaments = 0;
    for (const r of xpRows ?? []) {
      xpTotal += num(r.amount);
      winsTotal += num(r.wins);
      if (r.reason === 'tournament') tournaments += 1;
      else if (r.reason === 'ce_result_reversed') tournaments -= 1;
    }
    const coinBalance = (coinRows ?? []).reduce((s, r) => s + num(r.amount), 0);

    const agg: PlayerAggregate = {
      xp_total: roundHalf(xpTotal),
      coin_balance: roundHalf(coinBalance),
      rank_code: rankForXp(ranks, roundHalf(xpTotal))?.code ?? null,
      tournaments_played: Math.max(0, tournaments),
      wins_total: roundHalf(winsTotal),
    };
    out[sid] = agg;

    await supabaseAdmin.from('player_gamification').upsert(
      { organization_id: orgId, student_id: sid, ...agg, updated_at: nowIso },
      { onConflict: 'organization_id,student_id' },
    );
  }

  return out;
}

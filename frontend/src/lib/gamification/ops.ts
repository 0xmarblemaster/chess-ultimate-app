/**
 * Admin Ops helpers (PRD §9.4 item 7, §5.3).
 *
 * Backs the admin Ops tab: sync status, a ledger browser, an idempotent ledger
 * reversal (compensating negative entry — never a delete), and a manual trophy
 * grant. All IO runs service-role via `supabaseAdmin`; the pure transforms
 * (`mergeLedgerEntries`, `buildReversalRows`) are exported for unit testing.
 *
 * The append-only contract (§5.2) is preserved: a reversal inserts a negative
 * `admin_adjust` row keyed `admin_reversal:<ledger>:<id>` so re-pressing "Reverse"
 * can never double-apply, and the original row is left untouched for audit.
 */
import 'server-only';
import { supabaseAdmin } from '@/lib/supabase-admin';
import { roundHalf } from './economy';
import { type LedgerEntry, type LedgerKind, buildReversalRows, mergeLedgerEntries } from './ops-core';
import { getRanks, recomputePlayers } from './store';

export { type LedgerEntry, type LedgerKind, buildReversalRows, mergeLedgerEntries } from './ops-core';

function num(v: unknown): number {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return Number.isFinite(n) ? n : 0;
}

// ---------------------------------------------------------------------------
// Sync status (§5.3)
// ---------------------------------------------------------------------------

export interface SyncStatus {
  last_result_created_at: string | null;
  cursor_initialized_at: string | null;
  last_run_at: string | null;
  last_status: string | null;
  last_error: string | null;
}

export async function getSyncStatus(orgId: string): Promise<SyncStatus | null> {
  const { data } = await supabaseAdmin
    .from('gamification_sync_state')
    .select('last_result_created_at,cursor_initialized_at,last_run_at,last_status,last_error')
    .eq('organization_id', orgId)
    .maybeSingle();
  if (!data) return null;
  return {
    last_result_created_at: data.last_result_created_at ?? null,
    cursor_initialized_at: data.cursor_initialized_at ?? null,
    last_run_at: data.last_run_at ?? null,
    last_status: data.last_status ?? null,
    last_error: data.last_error ?? null,
  };
}

// ---------------------------------------------------------------------------
// Ledger browser (§9.4 audit log)
// ---------------------------------------------------------------------------

export interface LedgerFilter {
  studentId?: string;
  ledger?: LedgerKind | 'all';
  limit?: number;
}

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 200;

export async function browseLedger(orgId: string, filter: LedgerFilter = {}): Promise<LedgerEntry[]> {
  const limit = Math.min(MAX_LIMIT, Math.max(1, Math.floor(filter.limit || DEFAULT_LIMIT)));
  const which = filter.ledger ?? 'all';

  const xpRows: LedgerEntry[] = [];
  const coinRows: LedgerEntry[] = [];

  if (which === 'xp' || which === 'all') {
    let q = supabaseAdmin
      .from('xp_ledger')
      .select('id,organization_id,student_id,amount,reason,wins,source_type,source_id,idempotency_key,occurred_at,created_at')
      .eq('organization_id', orgId);
    if (filter.studentId) q = q.eq('student_id', filter.studentId);
    const { data } = await q.order('created_at', { ascending: false }).limit(limit);
    for (const r of data ?? []) {
      xpRows.push({
        ledger: 'xp',
        id: r.id as string,
        organization_id: r.organization_id as string,
        student_id: r.student_id as string,
        amount: num(r.amount),
        reason: (r.reason as string) ?? null,
        wins: r.wins == null ? null : num(r.wins),
        source_type: (r.source_type as string) ?? null,
        source_id: (r.source_id as string) ?? null,
        idempotency_key: r.idempotency_key as string,
        occurred_at: r.occurred_at as string,
        created_at: r.created_at as string,
      });
    }
  }

  if (which === 'coin' || which === 'all') {
    let q = supabaseAdmin
      .from('coin_ledger')
      .select('id,organization_id,student_id,amount,source,source_id,idempotency_key,occurred_at,created_at')
      .eq('organization_id', orgId);
    if (filter.studentId) q = q.eq('student_id', filter.studentId);
    const { data } = await q.order('created_at', { ascending: false }).limit(limit);
    for (const r of data ?? []) {
      coinRows.push({
        ledger: 'coin',
        id: r.id as string,
        organization_id: r.organization_id as string,
        student_id: r.student_id as string,
        amount: num(r.amount),
        source: (r.source as string) ?? null,
        source_id: (r.source_id as string) ?? null,
        idempotency_key: r.idempotency_key as string,
        occurred_at: r.occurred_at as string,
        created_at: r.created_at as string,
      });
    }
  }

  return mergeLedgerEntries(xpRows, coinRows, limit);
}

// ---------------------------------------------------------------------------
// Ledger reversal — compensating idempotent entry, never a delete (§5.2)
// ---------------------------------------------------------------------------

export type ReverseResult =
  | { status: 'ok'; student_id: string; amount: number; ledger: LedgerKind }
  | { status: 'not_found' };

/**
 * Reverse a single ledger entry: read it, insert a compensating negative
 * `admin_adjust` row (idempotent on the reversal key), then recompute the
 * affected student's read model so balances reflect the reversal immediately.
 */
export async function reverseLedgerEntry(
  orgId: string,
  ledger: LedgerKind,
  entryId: string,
): Promise<ReverseResult> {
  const table = ledger === 'xp' ? 'xp_ledger' : 'coin_ledger';
  const { data } = await supabaseAdmin
    .from(table)
    .select('*')
    .eq('organization_id', orgId)
    .eq('id', entryId)
    .maybeSingle();
  if (!data) return { status: 'not_found' };

  const entry: LedgerEntry = {
    ledger,
    id: data.id as string,
    organization_id: data.organization_id as string,
    student_id: data.student_id as string,
    amount: num(data.amount),
    wins: data.wins == null ? null : num(data.wins),
    occurred_at: data.occurred_at as string,
    created_at: (data.created_at as string) ?? '',
    source_id: (data.source_id as string) ?? null,
    idempotency_key: data.idempotency_key as string,
  };

  const { xpRow, coinRow } = buildReversalRows(entry);
  if (xpRow) {
    await supabaseAdmin
      .from('xp_ledger')
      .upsert([xpRow], { onConflict: 'idempotency_key', ignoreDuplicates: true });
  }
  if (coinRow) {
    await supabaseAdmin
      .from('coin_ledger')
      .upsert([coinRow], { onConflict: 'idempotency_key', ignoreDuplicates: true });
  }

  // Refresh the read model so the reversal shows up without waiting for sync.
  const ranks = await getRanks(orgId);
  await recomputePlayers(orgId, [entry.student_id], ranks);

  return { status: 'ok', student_id: entry.student_id, amount: roundHalf(-entry.amount), ledger };
}

// ---------------------------------------------------------------------------
// Manual trophy grant (§8.4 grace path)
// ---------------------------------------------------------------------------

export type TrophyGrantResult =
  | { status: 'ok'; granted: number }
  | { status: 'item_not_found' };

/**
 * Grant a trophy item to a student manually (e.g. a late-linking kid inside the
 * admin grace window). Idempotent via UNIQUE(org, student, item); a second grant
 * is a no-op. The item must exist in the org.
 */
export async function grantTrophy(
  orgId: string,
  params: { studentId: string; itemId: string; seasonId?: string | null },
): Promise<TrophyGrantResult> {
  const { data: item } = await supabaseAdmin
    .from('items')
    .select('id')
    .eq('organization_id', orgId)
    .eq('id', params.itemId)
    .maybeSingle();
  if (!item) return { status: 'item_not_found' };

  const { data } = await supabaseAdmin
    .from('player_items')
    .upsert(
      [
        {
          organization_id: orgId,
          student_id: params.studentId,
          item_id: params.itemId,
          acquired_via: 'trophy',
          season_id: params.seasonId ?? null,
        },
      ],
      { onConflict: 'organization_id,student_id,item_id', ignoreDuplicates: true },
    )
    .select('id');

  return { status: 'ok', granted: data?.length ?? 0 };
}

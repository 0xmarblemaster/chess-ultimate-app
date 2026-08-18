/**
 * Pure Ops transforms (PRD §5.2, §9.4) — no IO, unit-testable.
 *
 * Split from `ops.ts` (which does the service-role IO) so the ledger-merge and
 * reversal-row math can be tested without a Supabase client, mirroring the
 * `standings.ts` / `standings-store.ts` split.
 */
import { roundHalf } from './economy';
import type { CoinLedgerInsert, XpLedgerInsert } from './sync-core';

export type LedgerKind = 'xp' | 'coin';

export interface LedgerEntry {
  ledger: LedgerKind;
  id: string;
  organization_id: string;
  student_id: string;
  amount: number;
  occurred_at: string;
  created_at: string;
  source_id: string | null;
  idempotency_key: string;
  // xp-only
  reason?: string | null;
  wins?: number | null;
  source_type?: string | null;
  // coin-only
  source?: string | null;
}

/** Merge XP + coin rows into one recency-ordered list, capped at `limit`. */
export function mergeLedgerEntries(
  xp: LedgerEntry[],
  coin: LedgerEntry[],
  limit: number,
): LedgerEntry[] {
  return [...xp, ...coin]
    .sort((a, b) => (a.created_at < b.created_at ? 1 : a.created_at > b.created_at ? -1 : 0))
    .slice(0, limit);
}

/**
 * Compensating negative row for a ledger entry (§5.2). Idempotency key is stable
 * (`admin_reversal:<ledger>:<id>`) so re-applying the reversal is a no-op. The
 * original row is never touched.
 */
export function buildReversalRows(entry: LedgerEntry): {
  xpRow?: XpLedgerInsert;
  coinRow?: CoinLedgerInsert;
  key: string;
} {
  const key = `admin_reversal:${entry.ledger}:${entry.id}`;
  if (entry.ledger === 'xp') {
    return {
      key,
      xpRow: {
        organization_id: entry.organization_id,
        student_id: entry.student_id,
        amount: roundHalf(-entry.amount),
        reason: 'admin_adjust',
        wins: entry.wins == null ? null : roundHalf(-entry.wins),
        source_type: 'admin_reversal',
        source_id: entry.id,
        idempotency_key: key,
        occurred_at: entry.occurred_at,
      },
    };
  }
  return {
    key,
    coinRow: {
      organization_id: entry.organization_id,
      student_id: entry.student_id,
      amount: roundHalf(-entry.amount),
      source: 'admin_adjust',
      source_id: entry.id,
      idempotency_key: key,
      occurred_at: entry.occurred_at,
    },
  };
}

/**
 * Gamification sync — pure planning layer.
 *
 * Turns fetched CE tournament rows + org config + prior state into the exact
 * ledger rows to insert (idempotent via idempotency_key) and the streak state
 * to persist. No IO here so it is fully unit-testable; the route (sync/route.ts)
 * does the CE fetch + Supabase writes.
 */

import {
  type GamificationConfig,
  computeStreak,
  computeTournamentAward,
  roundHalf,
} from './economy';

// --- CE input shape (subset of tournament_results joined to the upload) -----
export interface CETournamentResult {
  id: string;
  student_id: string;
  score: number | null;
  created_at: string;
  upload: { kind: string | null; tournament_date: string | null } | null;
}

// --- Ledger row inserts (match column names in the migration) ---------------
export interface XpLedgerInsert {
  organization_id: string;
  student_id: string;
  amount: number;
  reason: string;
  wins: number | null;
  source_type: string | null;
  source_id: string | null;
  idempotency_key: string;
  occurred_at: string;
}

export interface CoinLedgerInsert {
  organization_id: string;
  student_id: string;
  amount: number;
  source: string;
  source_id: string | null;
  idempotency_key: string;
  occurred_at: string;
}

export interface AwardPlan {
  xpRows: XpLedgerInsert[];
  coinRows: CoinLedgerInsert[];
  touchedStudents: Set<string>;
  /** Max tournament_results.created_at seen — the new sync cursor. */
  maxCreatedAt: string | null;
  /** Results skipped because they lacked a usable tournament date. */
  skipped: number;
}

/**
 * Plan XP + coin awards for a batch of CE results (one ledger row per result).
 * Idempotency key `ce_result:<id>` makes re-runs and Swiss re-uploads safe —
 * the DB ON CONFLICT DO NOTHING drops duplicates.
 */
export function planTournamentAwards(
  orgId: string,
  results: CETournamentResult[],
  config: GamificationConfig,
): AwardPlan {
  const xpRows: XpLedgerInsert[] = [];
  const coinRows: CoinLedgerInsert[] = [];
  const touched = new Set<string>();
  let maxCreatedAt: string | null = null;
  let skipped = 0;

  for (const r of results) {
    if (r.created_at && (!maxCreatedAt || r.created_at > maxCreatedAt)) {
      maxCreatedAt = r.created_at;
    }
    const occurredAt = r.upload?.tournament_date;
    if (!occurredAt || !r.student_id) {
      skipped += 1;
      continue; // cannot attribute to a season / student → skip (cursor still advances)
    }
    const award = computeTournamentAward(config, r.upload?.kind, r.score ?? 0);
    const key = `ce_result:${r.id}`;
    xpRows.push({
      organization_id: orgId,
      student_id: r.student_id,
      amount: award.xp,
      reason: 'tournament',
      wins: award.wins,
      source_type: 'ce_result',
      source_id: r.id,
      idempotency_key: key,
      occurred_at: occurredAt,
    });
    coinRows.push({
      organization_id: orgId,
      student_id: r.student_id,
      amount: award.coins,
      source: 'earn_xp',
      source_id: r.id,
      idempotency_key: key,
      occurred_at: occurredAt,
    });
    touched.add(r.student_id);
  }

  return { xpRows, coinRows, touchedStudents: touched, maxCreatedAt, skipped };
}

/**
 * Plan streak bonus/milestone awards for one student, replaying all of their
 * tournament participation dates. Deterministic + idempotent (keys tie to the
 * ISO week / run-start), so it is safe to recompute the full history each sync.
 */
export function planStreakAwards(
  orgId: string,
  studentId: string,
  occurredAts: string[],
  config: GamificationConfig,
): { xpRows: XpLedgerInsert[]; coinRows: CoinLedgerInsert[]; state: ReturnType<typeof computeStreak> } {
  const state = computeStreak(occurredAts, config.streak);
  const xpRows: XpLedgerInsert[] = [];
  const coinRows: CoinLedgerInsert[] = [];

  for (const a of state.awards) {
    const prefix = a.kind === 'streak_bonus' ? 'streak' : 'streak_ms';
    const key = `${prefix}:${studentId}${a.idempotencySuffix}`;
    const coins = roundHalf(a.amount * config.coin_per_xp);
    xpRows.push({
      organization_id: orgId,
      student_id: studentId,
      amount: a.amount,
      reason: a.kind,
      wins: null,
      source_type: 'streak',
      source_id: null,
      idempotency_key: key,
      occurred_at: `${a.week}T00:00:00Z`,
    });
    coinRows.push({
      organization_id: orgId,
      student_id: studentId,
      amount: coins,
      source: 'streak',
      source_id: null,
      idempotency_key: key,
      occurred_at: `${a.week}T00:00:00Z`,
    });
  }

  return { xpRows, coinRows, state };
}

/** A previously-awarded tournament row we may need to reverse. */
export interface AwardedResult {
  organization_id: string;
  student_id: string;
  source_id: string; // tournament_results.id
  amount: number; // original xp amount (positive)
  coin_amount: number; // original coin amount (positive)
  wins: number; // original Swiss score contribution (positive)
  occurred_at: string;
}

/**
 * Plan compensating reversals for awarded results that no longer exist in CE
 * (admin deleted/re-uploaded a bad import). Negative ledger rows, idempotent
 * via `ce_result_reversed:<id>`. `existingIds` is the set of CE result ids that
 * still exist among the uploads we previously awarded.
 */
export function planReversals(
  awarded: AwardedResult[],
  existingIds: Set<string>,
): { xpRows: XpLedgerInsert[]; coinRows: CoinLedgerInsert[]; touchedStudents: Set<string> } {
  const xpRows: XpLedgerInsert[] = [];
  const coinRows: CoinLedgerInsert[] = [];
  const touched = new Set<string>();

  for (const a of awarded) {
    if (existingIds.has(a.source_id)) continue; // still present → no reversal
    const key = `ce_result_reversed:${a.source_id}`;
    xpRows.push({
      organization_id: a.organization_id,
      student_id: a.student_id,
      amount: roundHalf(-a.amount),
      reason: 'ce_result_reversed',
      wins: roundHalf(-a.wins), // cancels the original in SUM(wins)
      source_type: 'ce_result',
      source_id: a.source_id,
      idempotency_key: key,
      occurred_at: a.occurred_at,
    });
    coinRows.push({
      organization_id: a.organization_id,
      student_id: a.student_id,
      amount: roundHalf(-a.coin_amount),
      source: 'admin_adjust',
      source_id: a.source_id,
      idempotency_key: key,
      occurred_at: a.occurred_at,
    });
    touched.add(a.student_id);
  }

  return { xpRows, coinRows, touchedStudents: touched };
}

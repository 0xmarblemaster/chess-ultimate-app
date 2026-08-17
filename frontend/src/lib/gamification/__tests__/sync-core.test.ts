import { describe, expect, it } from 'vitest';
import { DEFAULT_CONFIG } from '../economy';
import {
  type AwardedResult,
  type CETournamentResult,
  planReversals,
  planStreakAwards,
  planTournamentAwards,
} from '../sync-core';

const ORG = 'org-1';

function result(id: string, student: string, score: number, kind: string, date: string, created: string): CETournamentResult {
  return { id, student_id: student, score, created_at: created, upload: { kind, tournament_date: date } };
}

describe('planTournamentAwards — ledger + idempotency + cursor', () => {
  const results = [
    result('r1', 's1', 1, 'league_c', '2026-01-05', '2026-01-06T10:00:00Z'),
    result('r2', 's1', 0.5, 'league_b', '2026-01-12', '2026-01-13T10:00:00Z'),
  ];

  it('produces one xp + one coin row per result keyed by ce_result:<id>', () => {
    const plan = planTournamentAwards(ORG, results, DEFAULT_CONFIG);
    expect(plan.xpRows).toHaveLength(2);
    expect(plan.coinRows).toHaveLength(2);
    expect(plan.xpRows[0].idempotency_key).toBe('ce_result:r1');
    expect(plan.coinRows[0].idempotency_key).toBe('ce_result:r1');
    expect(plan.xpRows[0].amount).toBe(2); // 1 + 1×1
    expect(plan.xpRows[1].amount).toBe(2); // 1 + 0.5×2
    expect(plan.xpRows[0].occurred_at).toBe('2026-01-05'); // tournament_date, not created_at
    expect(plan.xpRows[0].wins).toBe(1);
  });

  it('re-running over the same results yields identical idempotency keys', () => {
    const a = planTournamentAwards(ORG, results, DEFAULT_CONFIG).xpRows.map((r) => r.idempotency_key);
    const b = planTournamentAwards(ORG, results, DEFAULT_CONFIG).xpRows.map((r) => r.idempotency_key);
    expect(a).toEqual(b); // DB ON CONFLICT DO NOTHING then drops the dupes → no double award
  });

  it('advances the cursor to the max created_at', () => {
    const plan = planTournamentAwards(ORG, results, DEFAULT_CONFIG);
    expect(plan.maxCreatedAt).toBe('2026-01-13T10:00:00Z');
  });

  it('skips results with no tournament date (cursor still advances)', () => {
    const bad: CETournamentResult = { id: 'r3', student_id: 's2', score: 3, created_at: '2026-02-01T00:00:00Z', upload: null };
    const plan = planTournamentAwards(ORG, [...results, bad], DEFAULT_CONFIG);
    expect(plan.xpRows).toHaveLength(2);
    expect(plan.skipped).toBe(1);
    expect(plan.maxCreatedAt).toBe('2026-02-01T00:00:00Z');
    expect(plan.touchedStudents.has('s2')).toBe(false);
  });
});

describe('planStreakAwards — keys + idempotency', () => {
  it('keys bonuses per week and milestones per run start', () => {
    const { xpRows, coinRows, state } = planStreakAwards(
      ORG,
      's1',
      ['2026-01-05', '2026-01-12', '2026-01-19'],
      DEFAULT_CONFIG,
    );
    expect(state.current_weeks).toBe(3);
    const keys = xpRows.map((r) => r.idempotency_key);
    expect(keys).toContain('streak:s1:2026-01-12');
    expect(keys).toContain('streak:s1:2026-01-19');
    expect(keys).toContain('streak_ms:s1:2026-01-05:3');
    // coin rows mirror xp rows 1:1
    expect(coinRows).toHaveLength(xpRows.length);
  });

  it('is stable across re-runs (idempotent)', () => {
    const run = () =>
      planStreakAwards(ORG, 's1', ['2026-01-05', '2026-01-12', '2026-01-19'], DEFAULT_CONFIG).xpRows
        .map((r) => r.idempotency_key)
        .sort();
    expect(run()).toEqual(run());
  });
});

describe('planReversals — compensating negatives (§5.2)', () => {
  const awarded: AwardedResult[] = [
    { organization_id: ORG, student_id: 's1', source_id: 'r1', amount: 2, coin_amount: 2, wins: 1, occurred_at: '2026-01-05' },
    { organization_id: ORG, student_id: 's1', source_id: 'r2', amount: 7, coin_amount: 7, wins: 3, occurred_at: '2026-01-12' },
  ];

  it('reverses only results missing from CE, zeroing their contribution', () => {
    const existing = new Set(['r1']); // r2 was deleted
    const { xpRows, coinRows, touchedStudents } = planReversals(awarded, existing);
    expect(xpRows).toHaveLength(1);
    expect(xpRows[0].idempotency_key).toBe('ce_result_reversed:r2');
    expect(xpRows[0].amount).toBe(-7);
    expect(xpRows[0].wins).toBe(-3);
    expect(coinRows[0].amount).toBe(-7);
    expect(coinRows[0].source).toBe('admin_adjust');
    expect(touchedStudents.has('s1')).toBe(true);
  });

  it('no reversals when every result still exists', () => {
    const { xpRows } = planReversals(awarded, new Set(['r1', 'r2']));
    expect(xpRows).toHaveLength(0);
  });
});

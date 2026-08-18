import { describe, it, expect } from 'vitest';
import { type LedgerEntry, buildReversalRows, mergeLedgerEntries } from '../ops-core';

function xpEntry(over: Partial<LedgerEntry> = {}): LedgerEntry {
  return {
    ledger: 'xp',
    id: 'xp-1',
    organization_id: 'org-1',
    student_id: 'stu-1',
    amount: 3.5,
    reason: 'tournament',
    wins: 2.5,
    source_type: 'ce_result',
    source_id: 'res-9',
    idempotency_key: 'ce_result:res-9',
    occurred_at: '2026-03-01T00:00:00Z',
    created_at: '2026-03-01T00:05:00Z',
    ...over,
  };
}

function coinEntry(over: Partial<LedgerEntry> = {}): LedgerEntry {
  return {
    ledger: 'coin',
    id: 'coin-1',
    organization_id: 'org-1',
    student_id: 'stu-1',
    amount: 3.5,
    source: 'earn_xp',
    source_id: 'res-9',
    idempotency_key: 'ce_result:res-9',
    occurred_at: '2026-03-01T00:00:00Z',
    created_at: '2026-03-01T00:04:00Z',
    ...over,
  };
}

describe('mergeLedgerEntries', () => {
  it('orders by created_at descending and caps at the limit', () => {
    const a = xpEntry({ id: 'a', created_at: '2026-03-01T00:01:00Z' });
    const b = coinEntry({ id: 'b', created_at: '2026-03-01T00:03:00Z' });
    const c = xpEntry({ id: 'c', created_at: '2026-03-01T00:02:00Z' });
    const merged = mergeLedgerEntries([a, c], [b], 10);
    expect(merged.map((e) => e.id)).toEqual(['b', 'c', 'a']);
  });

  it('slices to the requested limit', () => {
    const rows = [1, 2, 3, 4].map((n) =>
      xpEntry({ id: `x${n}`, created_at: `2026-03-0${n}T00:00:00Z` }),
    );
    expect(mergeLedgerEntries(rows, [], 2)).toHaveLength(2);
  });
});

describe('buildReversalRows', () => {
  it('negates an XP entry into a compensating admin_adjust row', () => {
    const { xpRow, coinRow, key } = buildReversalRows(xpEntry());
    expect(coinRow).toBeUndefined();
    expect(key).toBe('admin_reversal:xp:xp-1');
    expect(xpRow).toMatchObject({
      student_id: 'stu-1',
      amount: -3.5,
      reason: 'admin_adjust',
      wins: -2.5,
      source_type: 'admin_reversal',
      source_id: 'xp-1',
      idempotency_key: 'admin_reversal:xp:xp-1',
      occurred_at: '2026-03-01T00:00:00Z',
    });
  });

  it('preserves a null wins on the reversal', () => {
    const { xpRow } = buildReversalRows(xpEntry({ wins: null }));
    expect(xpRow?.wins).toBeNull();
  });

  it('negates a coin entry into a compensating admin_adjust row', () => {
    const { coinRow, xpRow, key } = buildReversalRows(coinEntry());
    expect(xpRow).toBeUndefined();
    expect(key).toBe('admin_reversal:coin:coin-1');
    expect(coinRow).toMatchObject({
      student_id: 'stu-1',
      amount: -3.5,
      source: 'admin_adjust',
      source_id: 'coin-1',
      idempotency_key: 'admin_reversal:coin:coin-1',
    });
  });

  it('keeps 0.5 granularity on the negated amount', () => {
    const { xpRow } = buildReversalRows(xpEntry({ amount: 0.5 }));
    expect(xpRow?.amount).toBe(-0.5);
  });
});

import { describe, it, expect } from 'vitest';
import {
  type PurchaseRow,
  buildPurchaseCreditRow,
  buildRefundRow,
  canTransition,
  nextStatus,
} from '../purchases-core';

function purchase(over: Partial<PurchaseRow> = {}): PurchaseRow {
  return {
    id: 'pur-1',
    organization_id: 'org-1',
    student_id: 'stu-1',
    package_id: 'pkg-1',
    coins: 500,
    amount_kzt: 2500,
    provider: 'kaspi',
    provider_ref: null,
    status: 'pending',
    created_at: '2026-08-18T00:00:00Z',
    paid_at: null,
    ...over,
  };
}

const AT = '2026-08-18T12:00:00Z';

describe('purchase state machine', () => {
  it('allows only the legal transitions', () => {
    expect(canTransition('pending', 'confirm')).toBe(true);
    expect(canTransition('pending', 'reject')).toBe(true);
    expect(canTransition('paid', 'refund')).toBe(true);
    // illegal
    expect(canTransition('paid', 'confirm')).toBe(false);
    expect(canTransition('pending', 'refund')).toBe(false);
    expect(canTransition('refunded', 'refund')).toBe(false);
    expect(canTransition('failed', 'confirm')).toBe(false);
  });

  it('maps actions to their target status', () => {
    expect(nextStatus('pending', 'confirm')).toBe('paid');
    expect(nextStatus('pending', 'reject')).toBe('failed');
    expect(nextStatus('paid', 'refund')).toBe('refunded');
    expect(nextStatus('paid', 'confirm')).toBeNull();
  });
});

describe('buildPurchaseCreditRow (confirm)', () => {
  it('credits the package coins, source=purchase, keyed on the payment id', () => {
    const row = buildPurchaseCreditRow(purchase(), AT);
    expect(row).toEqual({
      organization_id: 'org-1',
      student_id: 'stu-1',
      amount: 500,
      source: 'purchase',
      source_id: 'pur-1',
      idempotency_key: 'purchase:pur-1',
      occurred_at: AT,
    });
  });

  it('is a coin-only row — a purchase grants +0 XP (§14.1)', () => {
    const row = buildPurchaseCreditRow(purchase(), AT);
    // No XP-ledger fields ever leak in: reason/wins are xp_ledger columns.
    expect(row).not.toHaveProperty('reason');
    expect(row).not.toHaveProperty('wins');
    expect(row.source).toBe('purchase');
  });

  it('keys stably so a double-confirm can only ever credit once', () => {
    const a = buildPurchaseCreditRow(purchase(), AT);
    const b = buildPurchaseCreditRow(purchase(), '2026-09-01T00:00:00Z');
    expect(a.idempotency_key).toBe(b.idempotency_key); // same payment id → same key
  });
});

describe('buildRefundRow (refund)', () => {
  it('is a compensating negative coin entry, source=refund, keyed refund:<id>', () => {
    const row = buildRefundRow(purchase({ status: 'paid' }), AT);
    expect(row).toEqual({
      organization_id: 'org-1',
      student_id: 'stu-1',
      amount: -500,
      source: 'refund',
      source_id: 'pur-1',
      idempotency_key: 'refund:pur-1',
      occurred_at: AT,
    });
  });

  it('never emits XP-ledger fields', () => {
    const row = buildRefundRow(purchase({ status: 'paid' }), AT);
    expect(row).not.toHaveProperty('reason');
    expect(row).not.toHaveProperty('wins');
  });
});

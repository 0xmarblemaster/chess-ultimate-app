/**
 * Coin-purchase state machine + ledger-row builders — pure, no IO (PRD §10, §14.1).
 *
 * Split from `purchases.ts` (service-role IO) so the transitions and the
 * idempotent credit/refund row math unit-test without a Supabase client,
 * mirroring the `ops-core.ts` / `ops.ts` split.
 *
 * GUARDRAIL (§14.1): a coin purchase grants **+0 XP, ever**. These builders emit
 * ONLY `coin_ledger` rows — there is deliberately no XP-row builder here, so the
 * sync + streak jobs stay the only writers of `xp_ledger`.
 */
import type { CoinLedgerInsert } from '@/lib/gamification/sync-core';

export type PurchaseStatus = 'pending' | 'paid' | 'failed' | 'refunded';
export type PurchaseAction = 'confirm' | 'reject' | 'refund';

export interface PurchaseRow {
  id: string;
  organization_id: string;
  student_id: string;
  package_id: string | null;
  coins: number;
  amount_kzt: number;
  provider: string;
  provider_ref: string | null;
  status: PurchaseStatus;
  created_at: string;
  paid_at: string | null;
}

/** Allowed transitions in the manual-confirm queue (§10). */
const TRANSITIONS: Record<PurchaseAction, { from: PurchaseStatus; to: PurchaseStatus }> = {
  confirm: { from: 'pending', to: 'paid' },
  reject: { from: 'pending', to: 'failed' },
  refund: { from: 'paid', to: 'refunded' },
};

export function canTransition(from: PurchaseStatus, action: PurchaseAction): boolean {
  return TRANSITIONS[action]?.from === from;
}

/** Target status for an action from `from`, or null if the transition is illegal. */
export function nextStatus(from: PurchaseStatus, action: PurchaseAction): PurchaseStatus | null {
  const t = TRANSITIONS[action];
  return t && t.from === from ? t.to : null;
}

/**
 * Coin credit for a confirmed purchase (§10). Positive `coins`, source='purchase',
 * idempotency key `purchase:<id>` — upserting on that key makes a double-confirm
 * (or double-click) a no-op, so coins are credited at most once per payment id.
 */
export function buildPurchaseCreditRow(purchase: PurchaseRow, atIso: string): CoinLedgerInsert {
  return {
    organization_id: purchase.organization_id,
    student_id: purchase.student_id,
    amount: purchase.coins,
    source: 'purchase',
    source_id: purchase.id,
    idempotency_key: `purchase:${purchase.id}`,
    occurred_at: atIso,
  };
}

/**
 * Compensating refund for a paid purchase (§10). Negative `coins`, source='refund',
 * idempotency key `refund:<id>`. Balance may floor at 0 downstream; items are
 * never auto-revoked (kid-friendliness > strictness).
 */
export function buildRefundRow(purchase: PurchaseRow, atIso: string): CoinLedgerInsert {
  return {
    organization_id: purchase.organization_id,
    student_id: purchase.student_id,
    amount: -purchase.coins,
    source: 'refund',
    source_id: purchase.id,
    idempotency_key: `refund:${purchase.id}`,
    occurred_at: atIso,
  };
}

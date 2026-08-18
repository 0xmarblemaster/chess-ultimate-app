/**
 * Coin-purchase persistence (service-role Supabase IO) — the manual-confirm
 * queue behind /coins and the admin Coins tab (PRD §10).
 *
 * The append-only coin_ledger contract (§5.2) holds: confirming a purchase
 * inserts a positive `purchase` row keyed `purchase:<id>`; refunding inserts a
 * negative `refund` row keyed `refund:<id>`. Both upsert on the idempotency key
 * so re-pressing the button can never double-credit / double-refund. Neither
 * path ever touches `xp_ledger` (§14.1 — purchases grant +0 XP).
 *
 * Pure transforms live in `purchases-core.ts`; this module is IO only.
 */
import 'server-only';
import { supabaseAdmin } from '@/lib/supabase-admin';
import { getRanks, recomputePlayers } from '@/lib/gamification/store';
import {
  type PurchaseRow,
  type PurchaseStatus,
  buildPurchaseCreditRow,
  buildRefundRow,
  canTransition,
} from './purchases-core';

const PURCHASE_COLS =
  'id,organization_id,student_id,package_id,coins,amount_kzt,provider,provider_ref,status,created_at,paid_at';

function num(v: unknown): number {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return Number.isFinite(n) ? n : 0;
}

function toRow(r: Record<string, unknown>): PurchaseRow {
  return {
    id: r.id as string,
    organization_id: r.organization_id as string,
    student_id: r.student_id as string,
    package_id: (r.package_id as string | null) ?? null,
    coins: num(r.coins),
    amount_kzt: num(r.amount_kzt),
    provider: r.provider as string,
    provider_ref: (r.provider_ref as string | null) ?? null,
    status: r.status as PurchaseStatus,
    created_at: r.created_at as string,
    paid_at: (r.paid_at as string | null) ?? null,
  };
}

// ---------------------------------------------------------------------------
// Packages — the parent-facing grid reads active rows only (§10, D-6)
// ---------------------------------------------------------------------------

export interface CoinPackage {
  id: string;
  coins: number;
  price_kzt: number;
  active: boolean;
  sort_order: number;
}

/** Active coin packages for the /coins grid, ascending by sort_order. */
export async function getActiveCoinPackages(orgId: string): Promise<CoinPackage[]> {
  const { data } = await supabaseAdmin
    .from('coin_packages')
    .select('id,coins,price_kzt,active,sort_order')
    .eq('organization_id', orgId)
    .eq('active', true)
    .order('sort_order', { ascending: true });
  return (data ?? []).map((r) => ({
    id: r.id as string,
    coins: num(r.coins),
    price_kzt: num(r.price_kzt),
    active: r.active !== false,
    sort_order: num(r.sort_order),
  }));
}

/** A single package by id (any active state) — used to build payment instructions. */
export async function getCoinPackage(orgId: string, packageId: string): Promise<CoinPackage | null> {
  const { data } = await supabaseAdmin
    .from('coin_packages')
    .select('id,coins,price_kzt,active,sort_order')
    .eq('organization_id', orgId)
    .eq('id', packageId)
    .maybeSingle();
  if (!data) return null;
  return {
    id: data.id as string,
    coins: num(data.coins),
    price_kzt: num(data.price_kzt),
    active: data.active !== false,
    sort_order: num(data.sort_order),
  };
}

// ---------------------------------------------------------------------------
// Claim — parent taps «Я оплатил(а)» → a pending_verification row (§10)
// ---------------------------------------------------------------------------

export type CreatePendingResult =
  | { status: 'ok'; purchase: PurchaseRow }
  | { status: 'package_unavailable' };

/**
 * Create a pending purchase from an active package. Coins + KZT are snapshotted
 * off the package so a later price edit never rewrites history. status='pending'
 * means "awaiting admin verification" until the admin marks it paid.
 */
export async function createPendingPurchase(
  orgId: string,
  params: { studentId: string; packageId: string; provider: string; providerRef?: string | null },
): Promise<CreatePendingResult> {
  const { data: pkg } = await supabaseAdmin
    .from('coin_packages')
    .select('id,coins,price_kzt,active')
    .eq('organization_id', orgId)
    .eq('id', params.packageId)
    .maybeSingle();
  if (!pkg || pkg.active === false) return { status: 'package_unavailable' };

  const { data } = await supabaseAdmin
    .from('coin_purchases')
    .insert({
      organization_id: orgId,
      student_id: params.studentId,
      package_id: pkg.id,
      coins: num(pkg.coins),
      amount_kzt: num(pkg.price_kzt),
      provider: params.provider,
      provider_ref: params.providerRef ?? null,
      status: 'pending',
    })
    .select(PURCHASE_COLS)
    .maybeSingle();

  return { status: 'ok', purchase: toRow((data ?? {}) as Record<string, unknown>) };
}

// ---------------------------------------------------------------------------
// Listing — admin queue + a student's own history
// ---------------------------------------------------------------------------

export interface PurchaseFilter {
  status?: PurchaseStatus;
  studentId?: string;
  limit?: number;
}

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 200;

export async function listPurchases(orgId: string, filter: PurchaseFilter = {}): Promise<PurchaseRow[]> {
  const limit = Math.min(MAX_LIMIT, Math.max(1, Math.floor(filter.limit || DEFAULT_LIMIT)));
  let q = supabaseAdmin.from('coin_purchases').select(PURCHASE_COLS).eq('organization_id', orgId);
  if (filter.status) q = q.eq('status', filter.status);
  if (filter.studentId) q = q.eq('student_id', filter.studentId);
  const { data } = await q.order('created_at', { ascending: false }).limit(limit);
  return (data ?? []).map((r) => toRow(r as Record<string, unknown>));
}

// ---------------------------------------------------------------------------
// Confirm / refund / reject — the admin actions (§10)
// ---------------------------------------------------------------------------

export type ConfirmResult =
  | { status: 'ok'; student_id: string; coins: number; already: boolean }
  | { status: 'not_found' }
  | { status: 'invalid_state'; current: PurchaseStatus };

async function loadPurchase(orgId: string, purchaseId: string): Promise<PurchaseRow | null> {
  const { data } = await supabaseAdmin
    .from('coin_purchases')
    .select(PURCHASE_COLS)
    .eq('organization_id', orgId)
    .eq('id', purchaseId)
    .maybeSingle();
  return data ? toRow(data as Record<string, unknown>) : null;
}

/**
 * Mark a pending purchase paid and credit coins idempotently. Safe to call
 * twice: an already-paid purchase re-affirms without a second credit (the
 * ledger key `purchase:<id>` also blocks double-credit at the DB level).
 */
export async function confirmPurchase(orgId: string, purchaseId: string): Promise<ConfirmResult> {
  const purchase = await loadPurchase(orgId, purchaseId);
  if (!purchase) return { status: 'not_found' };
  if (purchase.status === 'paid') {
    return { status: 'ok', student_id: purchase.student_id, coins: purchase.coins, already: true };
  }
  if (!canTransition(purchase.status, 'confirm')) {
    return { status: 'invalid_state', current: purchase.status };
  }

  const nowIso = new Date().toISOString();
  const row = buildPurchaseCreditRow(purchase, nowIso);
  await supabaseAdmin
    .from('coin_ledger')
    .upsert([row], { onConflict: 'idempotency_key', ignoreDuplicates: true });

  await supabaseAdmin
    .from('coin_purchases')
    .update({ status: 'paid', paid_at: nowIso })
    .eq('organization_id', orgId)
    .eq('id', purchaseId);

  const ranks = await getRanks(orgId);
  await recomputePlayers(orgId, [purchase.student_id], ranks);

  return { status: 'ok', student_id: purchase.student_id, coins: purchase.coins, already: false };
}

/**
 * Refund a paid purchase with a compensating negative ledger entry. Balance
 * floors at 0 in the read model; items are never auto-revoked (§10). Idempotent.
 */
export async function refundPurchase(orgId: string, purchaseId: string): Promise<ConfirmResult> {
  const purchase = await loadPurchase(orgId, purchaseId);
  if (!purchase) return { status: 'not_found' };
  if (purchase.status === 'refunded') {
    return { status: 'ok', student_id: purchase.student_id, coins: purchase.coins, already: true };
  }
  if (!canTransition(purchase.status, 'refund')) {
    return { status: 'invalid_state', current: purchase.status };
  }

  const nowIso = new Date().toISOString();
  const row = buildRefundRow(purchase, nowIso);
  await supabaseAdmin
    .from('coin_ledger')
    .upsert([row], { onConflict: 'idempotency_key', ignoreDuplicates: true });

  await supabaseAdmin
    .from('coin_purchases')
    .update({ status: 'refunded' })
    .eq('organization_id', orgId)
    .eq('id', purchaseId);

  const ranks = await getRanks(orgId);
  await recomputePlayers(orgId, [purchase.student_id], ranks);

  return { status: 'ok', student_id: purchase.student_id, coins: purchase.coins, already: false };
}

/** Reject an unmatched claim: pending → failed. No ledger write. */
export async function rejectPurchase(orgId: string, purchaseId: string): Promise<ConfirmResult> {
  const purchase = await loadPurchase(orgId, purchaseId);
  if (!purchase) return { status: 'not_found' };
  if (purchase.status === 'failed') {
    return { status: 'ok', student_id: purchase.student_id, coins: purchase.coins, already: true };
  }
  if (!canTransition(purchase.status, 'reject')) {
    return { status: 'invalid_state', current: purchase.status };
  }
  await supabaseAdmin
    .from('coin_purchases')
    .update({ status: 'failed' })
    .eq('organization_id', orgId)
    .eq('id', purchaseId);
  return { status: 'ok', student_id: purchase.student_id, coins: purchase.coins, already: false };
}

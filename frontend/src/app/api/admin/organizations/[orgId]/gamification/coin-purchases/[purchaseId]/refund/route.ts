/**
 * POST /api/admin/organizations/[orgId]/gamification/coin-purchases/[purchaseId]/refund
 *
 * Admin refund of a paid purchase → compensating negative coin_ledger entry
 * (source='refund', key `refund:<id>`) + read-model refresh (§10). Balance
 * floors at 0; items are never auto-revoked. Idempotent. Admin/owner gated.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { refundPurchase } from '@/lib/empire-payments/purchases';

export const dynamic = 'force-dynamic';

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ orgId: string; purchaseId: string }> },
) {
  const { orgId, purchaseId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const result = await refundPurchase(orgId, purchaseId);
  const status =
    result.status === 'ok' ? 200 : result.status === 'not_found' ? 404 : 409;
  return NextResponse.json(result, { status });
}

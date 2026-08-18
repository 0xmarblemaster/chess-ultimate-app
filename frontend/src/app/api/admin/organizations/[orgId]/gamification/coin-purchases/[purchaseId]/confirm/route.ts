/**
 * POST /api/admin/organizations/[orgId]/gamification/coin-purchases/[purchaseId]/confirm
 *
 * Admin marks a claimed payment paid → idempotent coin_ledger credit
 * (source='purchase', key `purchase:<id>`) + read-model refresh (§10). A double-
 * click can't double-credit. Admin/owner gated. Never touches xp_ledger (§14.1).
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { confirmPurchase } from '@/lib/empire-payments/purchases';

export const dynamic = 'force-dynamic';

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ orgId: string; purchaseId: string }> },
) {
  const { orgId, purchaseId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const result = await confirmPurchase(orgId, purchaseId);
  const status =
    result.status === 'ok' ? 200 : result.status === 'not_found' ? 404 : 409;
  return NextResponse.json(result, { status });
}

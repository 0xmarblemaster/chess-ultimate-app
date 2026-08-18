/**
 * POST /api/admin/organizations/[orgId]/gamification/coin-purchases/[purchaseId]/reject
 *
 * Admin rejects an unmatched claim: pending → failed. No ledger write, no coins
 * credited. Admin/owner gated.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { rejectPurchase } from '@/lib/empire-payments/purchases';

export const dynamic = 'force-dynamic';

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ orgId: string; purchaseId: string }> },
) {
  const { orgId, purchaseId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const result = await rejectPurchase(orgId, purchaseId);
  const status =
    result.status === 'ok' ? 200 : result.status === 'not_found' ? 404 : 409;
  return NextResponse.json(result, { status });
}

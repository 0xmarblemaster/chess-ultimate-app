/**
 * GET /api/admin/organizations/[orgId]/gamification/coin-purchases?status=pending
 *
 * The admin manual-confirm queue (§10). Lists coin_purchases for the org,
 * optionally filtered by status. Admin/owner gated. Next-side (not Flask)
 * because confirm/refund write the coin_ledger — same pattern as Ops.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { listPurchases } from '@/lib/empire-payments/purchases';
import type { PurchaseStatus } from '@/lib/empire-payments/purchases-core';

export const dynamic = 'force-dynamic';

const STATUSES: PurchaseStatus[] = ['pending', 'paid', 'failed', 'refunded'];

export async function GET(req: NextRequest, { params }: { params: Promise<{ orgId: string }> }) {
  const { orgId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const statusParam = req.nextUrl.searchParams.get('status');
  const status = STATUSES.includes(statusParam as PurchaseStatus)
    ? (statusParam as PurchaseStatus)
    : undefined;
  const studentId = req.nextUrl.searchParams.get('student_id') || undefined;

  const purchases = await listPurchases(orgId, { status, studentId });
  return NextResponse.json({ purchases });
}

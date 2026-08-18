/**
 * GET /api/admin/organizations/[orgId]/gamification/ops/ledger
 *
 * Ledger browser for the admin Ops tab (§9.4): recent XP + coin entries, filter
 * by student and ledger kind. Admin/owner gated.
 *
 * Query params: `student_id`, `ledger` (xp|coin|all), `limit`.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { type LedgerKind, browseLedger } from '@/lib/gamification/ops';

export const dynamic = 'force-dynamic';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ orgId: string }> },
) {
  const { orgId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const sp = req.nextUrl.searchParams;
  const studentId = sp.get('student_id') || undefined;
  const ledgerParam = sp.get('ledger');
  const ledger: LedgerKind | 'all' =
    ledgerParam === 'xp' || ledgerParam === 'coin' ? ledgerParam : 'all';
  const limitRaw = parseInt(sp.get('limit') || '', 10);
  const limit = Number.isFinite(limitRaw) ? limitRaw : undefined;

  const entries = await browseLedger(orgId, { studentId, ledger, limit });
  return NextResponse.json({ entries });
}

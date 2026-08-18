/**
 * POST /api/admin/organizations/[orgId]/gamification/ops/sync
 *
 * Admin "Sync now" (§5.3): runs the same `syncOrg` pass the CRON route runs, but
 * for this org only and admin/owner-gated. The CRON_SECRET stays server-side —
 * this route never exposes it; it invokes the runner directly.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { syncOrg } from '@/lib/gamification/sync-run';

export const dynamic = 'force-dynamic';

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ orgId: string }> },
) {
  const { orgId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const summary = await syncOrg(orgId);
  return NextResponse.json(
    { summary },
    { status: summary.status === 'error' ? 500 : 200 },
  );
}

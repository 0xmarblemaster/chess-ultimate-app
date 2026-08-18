/**
 * GET /api/admin/organizations/[orgId]/gamification/ops/sync-status
 *
 * Sync cursor + last-run health for the admin Ops tab (§9.4 item 7). Admin/owner
 * gated; reads gamification_sync_state service-role.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { getSyncStatus } from '@/lib/gamification/ops';

export const dynamic = 'force-dynamic';

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ orgId: string }> },
) {
  const { orgId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const status = await getSyncStatus(orgId);
  return NextResponse.json({ status });
}

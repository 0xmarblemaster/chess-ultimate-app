/**
 * POST /api/admin/organizations/[orgId]/gamification/seasons/[seasonId]/close
 *
 * Season close job (§8.4): freeze standings into season_results, mark the
 * winner, and grant the trophy item to eligible members of the winning legion.
 * Runs Next-side (not proxied to Flask) because it needs the CE branch mapping +
 * XP ledger to score. Admin/owner-gated. Requires the season to be active and
 * past its end date (auto-freeze + confirm, D-10); `{ force: true }` overrides
 * the end-date guard for a deliberate early close.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { closeSeason } from '@/lib/gamification/standings-store';

export const dynamic = 'force-dynamic';

const STATUS_CODE: Record<string, number> = {
  ok: 200,
  not_found: 404,
  not_active: 409,
  not_frozen: 409,
};

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ orgId: string; seasonId: string }> },
) {
  const { orgId, seasonId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const body = (await req.json().catch(() => ({}))) as { force?: boolean };
  try {
    const result = await closeSeason(orgId, seasonId, { force: body.force === true });
    return NextResponse.json(result, { status: STATUS_CODE[result.status] ?? 400 });
  } catch (err) {
    return NextResponse.json(
      { status: 'error', error: (err as Error)?.message ?? 'close_failed' },
      { status: 500 },
    );
  }
}

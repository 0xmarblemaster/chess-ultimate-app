/**
 * POST /api/admin/organizations/[orgId]/gamification/ops/trophy-grant
 *
 * Manually grant a trophy item to a student (§8.4 grace path). Idempotent via
 * UNIQUE(org, student, item). Admin/owner gated.
 *
 * Body: `{ student_id: string, item_id: string, season_id?: string }`.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { grantTrophy } from '@/lib/gamification/ops';

export const dynamic = 'force-dynamic';

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ orgId: string }> },
) {
  const { orgId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const body = (await req.json().catch(() => ({}))) as {
    student_id?: string;
    item_id?: string;
    season_id?: string;
  };
  if (!body.student_id || !body.item_id) {
    return NextResponse.json({ error: 'student_id and item_id required' }, { status: 400 });
  }

  const result = await grantTrophy(orgId, {
    studentId: body.student_id,
    itemId: body.item_id,
    seasonId: body.season_id ?? null,
  });
  return NextResponse.json(result, { status: result.status === 'ok' ? 200 : 404 });
}

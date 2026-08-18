/**
 * POST /api/admin/organizations/[orgId]/gamification/ops/ledger/reverse
 *
 * Reverse a ledger entry (§5.2): inserts a compensating negative `admin_adjust`
 * row — never a delete — and refreshes the student's read model. Idempotent, so
 * a double-press can't double-reverse. Admin/owner gated.
 *
 * Body: `{ ledger: 'xp'|'coin', entry_id: string }`.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { reverseLedgerEntry } from '@/lib/gamification/ops';

export const dynamic = 'force-dynamic';

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ orgId: string }> },
) {
  const { orgId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const body = (await req.json().catch(() => ({}))) as { ledger?: string; entry_id?: string };
  if ((body.ledger !== 'xp' && body.ledger !== 'coin') || !body.entry_id) {
    return NextResponse.json({ error: 'ledger and entry_id required' }, { status: 400 });
  }

  const result = await reverseLedgerEntry(orgId, body.ledger, body.entry_id);
  return NextResponse.json(result, { status: result.status === 'ok' ? 200 : 404 });
}

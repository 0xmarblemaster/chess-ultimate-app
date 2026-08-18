/**
 * POST /api/gamification/shop/buy   body: { item_id }
 *
 * Spend earned coins on a cosmetic. Delegates to the atomic `spend_coins` RPC
 * (balance check + coin debit + inventory grant in one transaction), which is
 * idempotent — re-submitting a purchase never double-charges (§7.1). Maps the
 * RPC status to HTTP.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { buyItem } from '@/lib/gamification/store';

export const dynamic = 'force-dynamic';

const STATUS_HTTP: Record<string, number> = {
  ok: 200,
  already_owned: 200, // idempotent
  insufficient_balance: 402,
  not_purchasable: 400,
  unavailable: 409,
  not_found: 404,
};

export async function POST(req: NextRequest) {
  const r = await resolveStudent();
  if (!r.ok) return NextResponse.json({ error: r.error }, { status: r.status });

  const body = await req.json().catch(() => ({}));
  const itemId = typeof body?.item_id === 'string' ? body.item_id : null;
  if (!itemId) return NextResponse.json({ error: 'item_id required' }, { status: 400 });

  const result = await buyItem(r.orgId, r.studentId, itemId);
  const http = STATUS_HTTP[result.status] ?? 400;
  return NextResponse.json(result, { status: http });
}

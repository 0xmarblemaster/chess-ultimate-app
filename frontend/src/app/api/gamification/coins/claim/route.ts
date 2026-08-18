/**
 * POST /api/gamification/coins/claim   body: { package_id, provider, provider_ref? }
 *
 * The «Я оплатил(а)» action: after paying out-of-band the parent claims payment,
 * which writes a pending (== awaiting-verification) coin_purchases row (§10).
 * Coins are NOT credited here — an admin confirms the transfer in the Coins tab,
 * which is the sole path that credits coin_ledger (source='purchase'). Verified-
 * link required (§7.1); unlinked callers are hidden (D-8).
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { createPendingPurchase } from '@/lib/empire-payments/purchases';
import { type PaymentProviderId, PROVIDER_IDS } from '@/lib/empire-payments/providers';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const r = await resolveStudent();
  if (!r.ok) return NextResponse.json({ error: r.error }, { status: r.status });

  const body = (await req.json().catch(() => ({}))) as {
    package_id?: string;
    provider?: string;
    provider_ref?: string;
  };
  const packageId = typeof body.package_id === 'string' ? body.package_id : null;
  const provider = body.provider as PaymentProviderId | undefined;
  if (!packageId) return NextResponse.json({ error: 'package_id required' }, { status: 400 });
  if (!provider || !PROVIDER_IDS.includes(provider)) {
    return NextResponse.json({ error: 'unknown_provider' }, { status: 400 });
  }

  const result = await createPendingPurchase(r.orgId, {
    studentId: r.studentId,
    packageId,
    provider,
    providerRef: typeof body.provider_ref === 'string' ? body.provider_ref : null,
  });
  if (result.status === 'package_unavailable') {
    return NextResponse.json({ error: 'package_unavailable' }, { status: 404 });
  }
  return NextResponse.json({ purchase: result.purchase }, { status: 201 });
}

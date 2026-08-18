/**
 * POST /api/gamification/coins/instructions   body: { package_id, provider }
 *
 * Build payment instructions (Kaspi link/QR or bank-transfer requisites) for a
 * selected package via the Empire Payments provider abstraction. No purchase row
 * is created here — the parent pays out-of-band, then claims (§10). The reference
 * embeds the student name + package so the manager can match the transfer.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { getCoinPackage } from '@/lib/empire-payments/purchases';
import {
  type PaymentProviderId,
  PROVIDER_IDS,
  buildPayment,
  loadProviderConfig,
} from '@/lib/empire-payments/providers';
import { getStudentDisplayName } from '@/lib/chess-empire-client';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const r = await resolveStudent();
  if (!r.ok) return NextResponse.json({ error: r.error }, { status: r.status });

  const body = (await req.json().catch(() => ({}))) as { package_id?: string; provider?: string };
  const packageId = typeof body.package_id === 'string' ? body.package_id : null;
  const provider = body.provider as PaymentProviderId | undefined;
  if (!packageId) return NextResponse.json({ error: 'package_id required' }, { status: 400 });
  if (!provider || !PROVIDER_IDS.includes(provider)) {
    return NextResponse.json({ error: 'unknown_provider' }, { status: 400 });
  }

  const pkg = await getCoinPackage(r.orgId, packageId);
  if (!pkg || !pkg.active) return NextResponse.json({ error: 'package_unavailable' }, { status: 404 });

  const studentName = (await getStudentDisplayName(r.studentId)) ?? r.studentId;
  const instructions = buildPayment(
    provider,
    { studentName, packageLabel: `${pkg.coins}🪙`, amountKzt: pkg.price_kzt },
    loadProviderConfig(),
  );
  if (!instructions.available) {
    return NextResponse.json({ error: 'provider_unavailable' }, { status: 409 });
  }

  return NextResponse.json({ instructions, package: pkg });
}

/**
 * GET /api/gamification/coins
 *
 * Parent-facing coin-purchase surface data for the calling student: active
 * packages (admin-priced, D-6), the student's display name (for the payment
 * reference), their recent purchases with status, and which providers are
 * configured. Verified-link required (§7.1, §10 — purchases are parent action);
 * unlinked callers are hidden (D-8).
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { getActiveCoinPackages, listPurchases } from '@/lib/empire-payments/purchases';
import { availableProviders, loadProviderConfig } from '@/lib/empire-payments/providers';
import { getStudentDisplayName } from '@/lib/chess-empire-client';

export const dynamic = 'force-dynamic';

export async function GET() {
  const r = await resolveStudent();
  if (!r.ok) return NextResponse.json({ error: r.error }, { status: r.status });

  const [packages, purchases, studentName] = await Promise.all([
    getActiveCoinPackages(r.orgId),
    listPurchases(r.orgId, { studentId: r.studentId, limit: 20 }),
    getStudentDisplayName(r.studentId),
  ]);

  const providers = availableProviders(loadProviderConfig());

  return NextResponse.json({
    student_name: studentName,
    packages,
    purchases,
    providers,
  });
}

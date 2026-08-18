/**
 * GET /api/gamification/achievements
 *
 * The caller's earned CE achievements, for the profile achievements strip
 * (§9.1). Verified-link required (D-8); unlinked callers get an empty list so
 * the strip degrades gracefully.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { getStudentAchievements } from '@/lib/chess-empire-client';

export const dynamic = 'force-dynamic';

export async function GET() {
  const r = await resolveStudent();
  if (!r.ok) {
    // Unlinked/unauthenticated → empty strip rather than an error surface.
    return NextResponse.json({ achievements: [] });
  }
  const achievements = await getStudentAchievements(r.studentId).catch(() => []);
  return NextResponse.json({ achievements });
}

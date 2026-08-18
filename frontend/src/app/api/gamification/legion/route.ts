/**
 * GET /api/gamification/legion
 *
 * The caller's own legion: crest, place, points, Top-N + full linked member
 * roster with season scores, and the caller's own position within it (§9.3).
 * Verified-link required (D-8); unlinked callers are hidden.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { buildCurrentStandings } from '@/lib/gamification/standings-store';
import { studentProximity } from '@/lib/gamification/standings';

export const dynamic = 'force-dynamic';

export async function GET() {
  const r = await resolveStudent();
  if (!r.ok) return NextResponse.json({ error: r.error }, { status: r.status });

  const bundle = await buildCurrentStandings(r.orgId);
  if (!bundle) return NextResponse.json({ season: null, legion: null, my: null });

  const my = studentProximity(bundle.standings, r.studentId);
  const legion = my.legion_id
    ? bundle.standings.legions.find((l) => l.legion.id === my.legion_id) ?? null
    : null;

  return NextResponse.json({
    season: {
      id: bundle.season.id,
      name: bundle.season.name,
      status: bundle.season.status,
      frozen: bundle.frozen,
    },
    top_n: bundle.standings.top_n,
    legion,
    my,
  });
}

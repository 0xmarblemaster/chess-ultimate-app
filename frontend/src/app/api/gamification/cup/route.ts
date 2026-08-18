/**
 * GET /api/gamification/cup
 *
 * Legion Cup table for the caller's org: every legion's place, points and gaps
 * for the current season, plus the caller's own Top-N proximity line (§8.3).
 * Verified-link required (D-8). Member rosters are omitted here (the /legion
 * surface carries those); the cup table is legion-level only.
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
  if (!bundle) {
    return NextResponse.json({ season: null, legions: [], my: null });
  }

  const my = studentProximity(bundle.standings, r.studentId);
  // Drop per-legion member lists — the cup table is legion-level.
  const legions = bundle.standings.legions.map(({ members, ...rest }) => {
    void members;
    return rest;
  });

  return NextResponse.json({
    season: {
      id: bundle.season.id,
      name: bundle.season.name,
      starts_at: bundle.season.starts_at,
      ends_at: bundle.season.ends_at,
      status: bundle.season.status,
      frozen: bundle.frozen,
    },
    top_n: bundle.standings.top_n,
    legions,
    my,
  });
}

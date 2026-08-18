/**
 * GET /api/gamification/seasons
 *
 * Season archive for the caller's org (§8.4 history): every season with its
 * winner legion resolved, plus the frozen standings snapshot for closed seasons.
 * Powers the «Скоро новый сезон» / past-archive view on the cup page.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { resolveStudent } from '@/lib/gamification/resolve-student';
import { supabaseAdmin } from '@/lib/supabase-admin';
import { getLegions, getSeasons } from '@/lib/gamification/store';

export const dynamic = 'force-dynamic';

export async function GET() {
  const r = await resolveStudent();
  if (!r.ok) return NextResponse.json({ error: r.error }, { status: r.status });

  const [seasons, legions] = await Promise.all([getSeasons(r.orgId), getLegions(r.orgId)]);
  const legionById = new Map(legions.map((l) => [l.id, l]));

  const closedIds = seasons.filter((s) => s.status === 'closed').map((s) => s.id);
  const resultsBySeason = new Map<string, unknown>();
  if (closedIds.length) {
    const { data } = await supabaseAdmin
      .from('season_results')
      .select('season_id,standings,winner_legion_id,finalized_at')
      .eq('organization_id', r.orgId)
      .in('season_id', closedIds);
    for (const row of data ?? []) resultsBySeason.set(row.season_id as string, row);
  }

  const out = seasons.map((s) => {
    const winner = s.winner_legion_id ? legionById.get(s.winner_legion_id) ?? null : null;
    return {
      id: s.id,
      name: s.name,
      starts_at: s.starts_at,
      ends_at: s.ends_at,
      status: s.status,
      top_n: s.top_n,
      winner: winner
        ? { id: winner.id, name: winner.name, crest_url: winner.crest_url }
        : null,
      results: resultsBySeason.get(s.id) ?? null,
    };
  });

  return NextResponse.json({ seasons: out });
}

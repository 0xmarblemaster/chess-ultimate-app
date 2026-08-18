/**
 * GET /api/admin/organizations/[orgId]/gamification/seasons/[seasonId]/standings
 *
 * Live standings preview for the Seasons tab (§9.4). Runs Next-side (needs CE
 * branch mapping + XP ledger); admin/owner-gated. Returns the full legion table
 * with member rosters so the admin can eyeball a season before closing it.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { requireOrgAdmin } from '@/app/api/admin/organizations/[orgId]/chess-empire/_lib/guard';
import { supabaseAdmin } from '@/lib/supabase-admin';
import { buildStandings } from '@/lib/gamification/standings-store';
import type { SeasonRow } from '@/lib/gamification/store';

export const dynamic = 'force-dynamic';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ orgId: string; seasonId: string }> },
) {
  const { orgId, seasonId } = await params;
  const guard = await requireOrgAdmin(orgId);
  if (!guard.ok) return guard.response;

  const { data } = await supabaseAdmin
    .from('seasons')
    .select('id,name,starts_at,ends_at,status,top_n,trophy_item_id,winner_legion_id,closed_at')
    .eq('organization_id', orgId)
    .eq('id', seasonId)
    .maybeSingle();
  if (!data) return NextResponse.json({ error: 'Season not found' }, { status: 404 });

  const bundle = await buildStandings(orgId, data as unknown as SeasonRow);
  return NextResponse.json({
    season: { ...data, frozen: bundle.frozen },
    top_n: bundle.standings.top_n,
    legions: bundle.standings.legions,
  });
}

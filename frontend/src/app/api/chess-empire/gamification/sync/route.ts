/**
 * POST /api/chess-empire/gamification/sync
 *
 * CRON_SECRET-guarded gamification ingestion (PRD §5.3). Runs `syncOrg` (see
 * `@/lib/gamification/sync-run`) for every org with a gamification_settings row:
 * pulls new CE tournament_results from the sync cursor forward, awards XP+coins
 * idempotently, replays streak bonuses, reverses deleted results, and recomputes
 * the player_gamification read model.
 *
 * Zero-start (D-5): on first run the cursor is pinned to "now" so historical
 * results are never awarded. Read-only against the CE DB.
 */
import 'server-only';
import { NextRequest, NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase-admin';
import { type OrgSyncSummary, syncOrg } from '@/lib/gamification/sync-run';

export const dynamic = 'force-dynamic';

function authorized(req: NextRequest): boolean {
  const secret = process.env.CRON_SECRET;
  if (!secret) return false; // fail closed if unconfigured
  const bearer = req.headers.get('authorization')?.replace(/^Bearer\s+/i, '');
  const header = req.headers.get('x-cron-secret');
  return bearer === secret || header === secret;
}

export async function POST(req: NextRequest) {
  if (!authorized(req)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { data: orgs } = await supabaseAdmin
    .from('gamification_settings')
    .select('organization_id');

  const results: OrgSyncSummary[] = [];
  for (const o of orgs ?? []) {
    results.push(await syncOrg(o.organization_id as string));
  }

  return NextResponse.json({ ok: true, ran_at: new Date().toISOString(), orgs: results });
}

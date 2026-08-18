/**
 * Legion-standings assembly + season close (service-role IO).
 *
 * Bridges the append-only ledgers, the CE branch mapping, and the pure
 * `standings.ts` math. Everything IO lives here so the scoring logic stays
 * unit-testable; this module just gathers inputs and persists the season-close
 * snapshot + trophy grants.
 *
 * Scoring is always computed live from the CURRENT branch→legion mapping (D-11)
 * so mid-season transfers and link/unlink changes are reflected immediately —
 * standings are a query, never a stored number (§8.3).
 */
import 'server-only';
import { supabaseAdmin } from '@/lib/supabase-admin';
import { getStudentBranches } from '@/lib/chess-empire-client';
import { roundHalf } from './economy';
import {
  type LegionRow,
  type SeasonRow,
  getCurrentSeason,
  getLegions,
  getLinkedStudentIds,
  getSeasons,
} from './store';
import {
  type Standings,
  type StandingsLegion,
  type StandingsStudent,
  computeStandings,
  planSeasonClose,
} from './standings';

function num(v: unknown): number {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return Number.isFinite(n) ? n : 0;
}

/** Per-student season aggregate from the XP ledger inside a window. */
interface SeasonAggregate {
  season_points: number;
  season_wins: number;
  tournaments: number;
  first_reached_at: string | null;
}

/**
 * Aggregate each student's XP-ledger rows whose occurred_at falls inside the
 * season window. Season points = SUM(amount) over all reasons (streaks
 * included, §8.3). Reversals cancel their tournament (negative amount + a
 * tournaments-- so counters stay honest).
 */
async function aggregateSeason(
  orgId: string,
  season: Pick<SeasonRow, 'starts_at' | 'ends_at'>,
): Promise<Map<string, SeasonAggregate>> {
  const { data } = await supabaseAdmin
    .from('xp_ledger')
    .select('student_id,amount,wins,reason,occurred_at')
    .eq('organization_id', orgId)
    .gte('occurred_at', season.starts_at)
    .lte('occurred_at', season.ends_at);

  const map = new Map<string, SeasonAggregate>();
  for (const r of data ?? []) {
    const sid = r.student_id as string;
    const agg = map.get(sid) ?? {
      season_points: 0,
      season_wins: 0,
      tournaments: 0,
      first_reached_at: null,
    };
    const amount = num(r.amount);
    agg.season_points += amount;
    agg.season_wins += num(r.wins);
    if (r.reason === 'tournament') agg.tournaments += 1;
    else if (r.reason === 'ce_result_reversed') agg.tournaments -= 1;
    if (amount > 0) {
      const occ = r.occurred_at as string;
      if (!agg.first_reached_at || occ < agg.first_reached_at) agg.first_reached_at = occ;
    }
    map.set(sid, agg);
  }
  return map;
}

function toStandingsLegion(l: LegionRow): StandingsLegion {
  return {
    id: l.id,
    name: l.name,
    totem: l.totem,
    crest_url: l.crest_url,
    color_primary: l.color_primary,
    color_secondary: l.color_secondary,
  };
}

export interface StandingsBundle {
  season: SeasonRow;
  standings: Standings;
  /** True once the season window has elapsed — auto-freeze (§8.2/D-10). */
  frozen: boolean;
  legions: LegionRow[];
}

/**
 * Build live standings for a season: aggregate ledger points, resolve each
 * scoring student's current branch→legion from CE, mark the linked set, and run
 * the pure Top-N math. `nowMs` is injectable so the auto-freeze boundary is
 * testable.
 */
export async function buildStandings(
  orgId: string,
  season: SeasonRow,
  nowMs: number = Date.now(),
): Promise<StandingsBundle> {
  const [legions, agg, linked] = await Promise.all([
    getLegions(orgId),
    aggregateSeason(orgId, season),
    getLinkedStudentIds(orgId),
  ]);

  const studentIds = [...agg.keys()];
  const branches = await getStudentBranches(studentIds);
  // branch_id → legion_id (only mapped legions participate in scoring).
  const branchToLegion = new Map<string, string>();
  for (const l of legions) {
    if (l.ce_branch_id) branchToLegion.set(l.ce_branch_id, l.id);
  }

  const students: StandingsStudent[] = studentIds.map((sid) => {
    const a = agg.get(sid)!;
    const branch = branches.get(sid) ?? null;
    return {
      student_id: sid,
      legion_id: branch ? branchToLegion.get(branch) ?? null : null,
      season_points: roundHalf(a.season_points),
      season_wins: roundHalf(a.season_wins),
      tournaments: Math.max(0, a.tournaments),
      first_reached_at: a.first_reached_at,
      linked: linked.has(sid),
    };
  });

  const config = await getOrgTopN(orgId, season.top_n);
  const standings = computeStandings(legions.map(toStandingsLegion), students, {
    top_n: season.top_n || config.top_n,
    count_unlinked: config.count_unlinked,
  });

  return {
    season,
    standings,
    frozen: nowMs >= new Date(season.ends_at).getTime(),
    legions,
  };
}

/** Read just the two standings knobs the season needs from org settings. */
async function getOrgTopN(
  orgId: string,
  fallbackTopN: number,
): Promise<{ top_n: number; count_unlinked: boolean; min_tournaments: number }> {
  const { data } = await supabaseAdmin
    .from('gamification_settings')
    .select('config')
    .eq('organization_id', orgId)
    .maybeSingle();
  const config = (data?.config ?? {}) as {
    top_n?: number;
    count_unlinked_in_standings?: boolean;
    min_tournaments_for_trophy?: number;
  };
  return {
    top_n: fallbackTopN || config.top_n || 5,
    count_unlinked: config.count_unlinked_in_standings === true,
    min_tournaments: config.min_tournaments_for_trophy ?? 3,
  };
}

/** Convenience: standings for the org's current (active/last-closed) season. */
export async function buildCurrentStandings(
  orgId: string,
  nowMs: number = Date.now(),
): Promise<StandingsBundle | null> {
  const season = await getCurrentSeason(orgId);
  if (!season) return null;
  return buildStandings(orgId, season, nowMs);
}

// ---------------------------------------------------------------------------
// Season close + trophy job (§8.4)
// ---------------------------------------------------------------------------

export type CloseStatus =
  | { status: 'ok'; winner_legion_id: string | null; trophies_granted: number }
  | { status: 'not_found' }
  | { status: 'not_active' }
  | { status: 'not_frozen' };

/**
 * Close a season: freeze the standings into season_results, mark the winner,
 * grant the trophy item to eligible members of the winning legion, and flip the
 * season to `closed`. Requires the season to be `active` and past its end date
 * (auto-freeze + admin confirm, D-10). `force` skips the end-date guard for the
 * rare admin override. Idempotent on the trophy inserts (UNIQUE student+item).
 */
export async function closeSeason(
  orgId: string,
  seasonId: string,
  opts: { force?: boolean; nowMs?: number } = {},
): Promise<CloseStatus> {
  const nowMs = opts.nowMs ?? Date.now();
  const { data: seasonRow } = await supabaseAdmin
    .from('seasons')
    .select('id,name,starts_at,ends_at,status,top_n,trophy_item_id,winner_legion_id,closed_at')
    .eq('organization_id', orgId)
    .eq('id', seasonId)
    .maybeSingle();
  if (!seasonRow) return { status: 'not_found' };
  const season = seasonRow as unknown as SeasonRow;
  if (season.status !== 'active') return { status: 'not_active' };
  if (!opts.force && nowMs < new Date(season.ends_at).getTime()) return { status: 'not_frozen' };

  const bundle = await buildStandings(orgId, season, nowMs);
  const { min_tournaments } = await getOrgTopN(orgId, season.top_n);
  const plan = planSeasonClose(bundle.standings, {
    min_tournaments_for_trophy: min_tournaments,
  });

  // Freeze the snapshot.
  await supabaseAdmin.from('season_results').upsert(
    {
      season_id: season.id,
      organization_id: orgId,
      standings: bundle.standings.legions,
      per_student: plan.per_student,
      winner_legion_id: plan.winner_legion_id,
      finalized_at: new Date(nowMs).toISOString(),
    },
    { onConflict: 'season_id' },
  );

  // Grant trophies (only if the season carries a trophy item).
  let granted = 0;
  if (season.trophy_item_id && plan.grants.length) {
    const rows = plan.grants.map((g) => ({
      organization_id: orgId,
      student_id: g.student_id,
      item_id: season.trophy_item_id,
      acquired_via: 'trophy',
      season_id: season.id,
    }));
    const { data } = await supabaseAdmin
      .from('player_items')
      .upsert(rows, { onConflict: 'organization_id,student_id,item_id', ignoreDuplicates: true })
      .select('id');
    granted = data?.length ?? 0;
  }

  // Flip the season to closed + record the winner.
  await supabaseAdmin
    .from('seasons')
    .update({
      status: 'closed',
      winner_legion_id: plan.winner_legion_id,
      closed_at: new Date(nowMs).toISOString(),
    })
    .eq('organization_id', orgId)
    .eq('id', season.id);

  return {
    status: 'ok',
    winner_legion_id: plan.winner_legion_id,
    trophies_granted: granted,
  };
}

// Re-export so routes import assembly + math from one place.
export { getSeasons, getCurrentSeason } from './store';

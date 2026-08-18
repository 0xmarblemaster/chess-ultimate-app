/**
 * Legion standings — pure, framework-free logic (PRD-gamification.md §8.3, §8.4).
 *
 * Everything here is deterministic and side-effect-free so the scoring math can
 * be unit tested without a database or CE calls. The standings store assembles
 * the inputs (season XP sums per student, each student's CURRENT branch→legion
 * mapping, the linked set) and feeds them here; the /legion, /cup and season-close
 * surfaces consume the result.
 *
 * Contract highlights:
 *  - Scoring uses each student's CURRENT legion (D-11): a transfer moves the
 *    student's whole season score simply by changing their `legion_id` input —
 *    there is no per-row attribution here.
 *  - Unlinked students are hidden (D-8): excluded from member lists and legion
 *    totals unless `count_unlinked` is set.
 *  - A legion's score is the sum of its Top-N linked members' season scores.
 *  - Ties: shared placement; tiebreak by season wins, then earlier attainment.
 */
import { roundHalf } from './economy';

// ---------------------------------------------------------------------------
// Inputs
// ---------------------------------------------------------------------------

/** One student's season aggregate + their current legion attribution. */
export interface StandingsStudent {
  student_id: string;
  /** Current branch→legion mapping (D-11). null ⇒ unmapped branch, not scored. */
  legion_id: string | null;
  /** SUM(xp_ledger.amount) inside the season window (all reasons). */
  season_points: number;
  /** SUM(xp_ledger.wins) inside the window — first tiebreak. */
  season_wins: number;
  /** Tournament participations inside the window — trophy eligibility (§8.4). */
  tournaments: number;
  /** Earliest occurred_at contributing points — "earlier attainment" tiebreak. */
  first_reached_at?: string | null;
  linked: boolean;
  /** Optional display name for member lists (never used for scoring). */
  name?: string | null;
}

export interface StandingsLegion {
  id: string;
  name: string;
  totem?: string | null;
  crest_url?: string | null;
  color_primary?: string | null;
  color_secondary?: string | null;
}

export interface StandingsOptions {
  top_n: number;
  count_unlinked: boolean;
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

/** One student inside a legion's ranked roster. */
export interface RankedMember {
  student_id: string;
  name?: string | null;
  season_points: number;
  season_wins: number;
  tournaments: number;
  /** 1-based rank within the legion (shared on ties). */
  place: number;
  /** True while the member counts toward the legion's Top-N score. */
  in_top_n: boolean;
}

export interface LegionStanding {
  legion: StandingsLegion;
  /** Sum of the Top-N members' season points (§8.3). */
  points: number;
  /** Sum of the Top-N members' season wins (legion tiebreak). */
  top_n_wins: number;
  /** 1-based place in the cup table (shared on ties). */
  place: number;
  /** Points behind the first-place legion (0 for the leader). */
  gap_to_first: number;
  /** Points behind the legion directly above (0 for the leader). */
  gap_to_above: number;
  member_count: number;
  members: RankedMember[];
}

export interface Standings {
  legions: LegionStanding[];
  top_n: number;
}

// ---------------------------------------------------------------------------
// Ranking
// ---------------------------------------------------------------------------

/**
 * Order students within a legion: most points first, then more season wins,
 * then earlier attainment (a smaller first_reached_at ISO string), then a
 * stable student_id fallback so the order is fully deterministic.
 */
function compareStudents(a: StandingsStudent, b: StandingsStudent): number {
  if (b.season_points !== a.season_points) return b.season_points - a.season_points;
  if (b.season_wins !== a.season_wins) return b.season_wins - a.season_wins;
  const af = a.first_reached_at ?? '￿';
  const bf = b.first_reached_at ?? '￿';
  if (af !== bf) return af < bf ? -1 : 1;
  return a.student_id < b.student_id ? -1 : a.student_id > b.student_id ? 1 : 0;
}

/** Assign 1-based places with shared placement on ties (1,2,2,4). */
function placeMembers(sorted: StandingsStudent[], topN: number): RankedMember[] {
  const out: RankedMember[] = [];
  let place = 0;
  let prev: StandingsStudent | null = null;
  sorted.forEach((s, i) => {
    // Same points AND same wins ⇒ genuinely tied placement.
    const tied =
      prev !== null && prev.season_points === s.season_points && prev.season_wins === s.season_wins;
    place = tied ? place : i + 1;
    out.push({
      student_id: s.student_id,
      name: s.name ?? null,
      season_points: roundHalf(s.season_points),
      season_wins: roundHalf(s.season_wins),
      tournaments: s.tournaments,
      place,
      in_top_n: i < topN,
    });
    prev = s;
  });
  return out;
}

/**
 * Compute the full cup standings from per-student season aggregates.
 *
 * Students with a null `legion_id` (unmapped branch) are never scored. Unlinked
 * students are excluded unless `count_unlinked` is true (D-8). Every legion in
 * `legions` appears in the result, even with zero members / zero points, so the
 * cup table is complete.
 */
export function computeStandings(
  legions: StandingsLegion[],
  students: StandingsStudent[],
  opts: StandingsOptions,
): Standings {
  const topN = Math.max(1, Math.floor(opts.top_n) || 1);

  // Group eligible students by their current legion.
  const byLegion = new Map<string, StandingsStudent[]>();
  for (const l of legions) byLegion.set(l.id, []);
  for (const s of students) {
    if (!s.legion_id) continue; // unmapped branch → unattributable
    if (!opts.count_unlinked && !s.linked) continue; // D-8
    const bucket = byLegion.get(s.legion_id);
    if (bucket) bucket.push(s); // ignore points for legions we don't know
  }

  // Build each legion standing (unplaced yet).
  const rows = legions.map((legion) => {
    const sorted = [...(byLegion.get(legion.id) ?? [])].sort(compareStudents);
    const members = placeMembers(sorted, topN);
    const top = sorted.slice(0, topN);
    const points = roundHalf(top.reduce((sum, s) => sum + s.season_points, 0));
    const topNWins = roundHalf(top.reduce((sum, s) => sum + s.season_wins, 0));
    return {
      legion,
      points,
      top_n_wins: topNWins,
      member_count: sorted.length,
      members,
    };
  });

  // Order the cup table: points desc, then Top-N wins desc, then name for stability.
  rows.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.top_n_wins !== a.top_n_wins) return b.top_n_wins - a.top_n_wins;
    return a.legion.name < b.legion.name ? -1 : a.legion.name > b.legion.name ? 1 : 0;
  });

  const leaderPoints = rows.length ? rows[0].points : 0;
  const standings: LegionStanding[] = rows.map((r, i) => ({
    ...r,
    place: standingsPlaceOf(rows, i), // shared placement on ties (1,2,2,4)
    gap_to_first: roundHalf(leaderPoints - r.points),
    gap_to_above: roundHalf((i === 0 ? r.points : rows[i - 1].points) - r.points),
  }));

  return { legions: standings, top_n: topN };
}

/**
 * Resolve the shared place for a row by walking back to the first row of its
 * tie group (equal points AND equal Top-N wins). Kept explicit rather than
 * threading mutable place state through the map above.
 */
function standingsPlaceOf(
  rows: Array<{ points: number; top_n_wins: number }>,
  i: number,
): number {
  let start = i;
  while (
    start > 0 &&
    rows[start - 1].points === rows[i].points &&
    rows[start - 1].top_n_wins === rows[i].top_n_wins
  ) {
    start -= 1;
  }
  return start + 1;
}

// ---------------------------------------------------------------------------
// Per-student proximity — the second-ladder motivation (§8.3)
// ---------------------------------------------------------------------------

export interface StudentProximity {
  legion_id: string | null;
  /** The student's 1-based place inside their legion, or null if not scored. */
  place: number | null;
  in_top_n: boolean;
  /** Points needed to break into the legion's Top-N (0 if already in). */
  points_to_top_n: number;
  /** The student's own season points. */
  season_points: number;
}

/**
 * A single student's position inside their legion + how far from the Top-N cut.
 * "До попадания в ТОП-5: 7 очков" = the Nth member's points minus theirs.
 */
export function studentProximity(
  standings: Standings,
  studentId: string,
): StudentProximity {
  for (const ls of standings.legions) {
    const idx = ls.members.findIndex((m) => m.student_id === studentId);
    if (idx === -1) continue;
    const me = ls.members[idx];
    if (me.in_top_n) {
      return {
        legion_id: ls.legion.id,
        place: me.place,
        in_top_n: true,
        points_to_top_n: 0,
        season_points: me.season_points,
      };
    }
    // The last member currently inside the Top-N is the cut line.
    const cut = ls.members.filter((m) => m.in_top_n).at(-1);
    const need = cut ? roundHalf(Math.max(0, cut.season_points - me.season_points)) : 0;
    return {
      legion_id: ls.legion.id,
      place: me.place,
      in_top_n: false,
      points_to_top_n: need,
      season_points: me.season_points,
    };
  }
  return {
    legion_id: null,
    place: null,
    in_top_n: false,
    points_to_top_n: 0,
    season_points: 0,
  };
}

// ---------------------------------------------------------------------------
// Season close — winner + trophy grants + snapshot (§8.4)
// ---------------------------------------------------------------------------

export interface SeasonCloseOptions {
  min_tournaments_for_trophy: number;
}

export interface TrophyGrant {
  student_id: string;
  legion_id: string;
}

export interface SeasonClosePlan {
  winner_legion_id: string | null;
  /** Members of the winning legion eligible for the trophy (§8.4, D-4). */
  grants: TrophyGrant[];
  /** Frozen legion table snapshot for season_results.standings. */
  standings: LegionStanding[];
  /** Per-student season scores for season_results.per_student. */
  per_student: Array<{
    student_id: string;
    legion_id: string;
    season_points: number;
    season_wins: number;
    tournaments: number;
    place: number;
  }>;
}

/**
 * Plan a season close from computed standings: pick the winner (place 1), grant
 * the trophy to eligible linked members of the winning legion (≥
 * min_tournaments_for_trophy participations, §8.4/D-4), and snapshot the table.
 *
 * A tie for first place is resolved by the standings ordering (points → Top-N
 * wins → name); the top row wins. If there are no legions or nobody scored, the
 * winner is null and no trophies are granted.
 */
export function planSeasonClose(
  standings: Standings,
  opts: SeasonCloseOptions,
): SeasonClosePlan {
  const winner = standings.legions.find((l) => l.place === 1 && l.points > 0) ?? null;
  const minT = Math.max(0, Math.floor(opts.min_tournaments_for_trophy) || 0);

  const grants: TrophyGrant[] = [];
  if (winner) {
    for (const m of winner.members) {
      if (m.tournaments >= minT) {
        grants.push({ student_id: m.student_id, legion_id: winner.legion.id });
      }
    }
  }

  const perStudent: SeasonClosePlan['per_student'] = [];
  for (const ls of standings.legions) {
    for (const m of ls.members) {
      perStudent.push({
        student_id: m.student_id,
        legion_id: ls.legion.id,
        season_points: m.season_points,
        season_wins: m.season_wins,
        tournaments: m.tournaments,
        place: m.place,
      });
    }
  }

  return {
    winner_legion_id: winner?.legion.id ?? null,
    grants,
    standings: standings.legions,
    per_student: perStudent,
  };
}

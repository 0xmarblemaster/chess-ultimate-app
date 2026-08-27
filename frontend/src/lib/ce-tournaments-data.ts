/**
 * Chess Empire tournaments — shared server-side snapshot.
 *
 * Single source of truth for the CE tournament schedule + rosters + the viewer's
 * own registration status. Consumed by both the SSR view
 * (`ChessEmpireTournaments`) and the polling API route
 * (`/api/chess-empire/tournaments`) so the initial paint and every 15s refresh
 * produce byte-identical card shapes. All CE calls (and the service key) stay
 * server-side.
 *
 * The design is a faithful port of the vanilla public schedule
 * (chess-empire-database/tournaments.js): branches (excluding НИШ / Zhandosova)
 * with upcoming counts, per-tournament full-name rosters, capacity meters.
 */
import 'server-only';
import { auth } from '@clerk/nextjs/server';
import { getMembershipStateForUser } from '@/lib/chess-empire-member';
import {
  listTournaments,
  listBranches,
  getStudentTournamentRegistrations,
  getStudentDisplayName,
  getTournamentRoster,
} from '@/lib/chess-empire-client';

/** Branches hidden from the public schedule (mirrors the vanilla page). */
export const EXCLUDED_BRANCHES = ['НИШ', 'Zhandosova'];

export interface CETournamentCard {
  id: string;
  name: string;
  info: string | null;
  tournament_date: string;
  start_time: string | null;
  time_format: string | null;
  registration_fee: number;
  rounds: number;
  capacity: number;
  /** 'open' | 'closed' | 'cancelled'. */
  status: string;
  registered_count: number;
  branch_id: string | null;
  branch_name: string | null;
  /** ISO deadline for the flip-clock countdown, when the schedule exposes one. */
  registration_deadline: string | null;
  /** Registered players' full names, in registration order. */
  roster: string[];
  /** Non-null when the viewing member is already registered. */
  registration_id: string | null;
  is_registered: boolean;
}

export interface CEBranchRef {
  id: string;
  name: string;
}

export type CEMembership = 'logged_out' | 'unverified' | 'verified';

export interface CETournamentSnapshot {
  membership: CEMembership;
  studentName: string | null;
  branches: CEBranchRef[];
  tournaments: CETournamentCard[];
}

export async function loadCETournamentSnapshot(): Promise<CETournamentSnapshot> {
  let rawTournaments: Awaited<ReturnType<typeof listTournaments>> = [];
  try {
    rawTournaments = await listTournaments(true);
  } catch (err) {
    console.error('[ce-tournaments] schedule fetch failed', err);
  }

  // Rosters for every upcoming tournament, in parallel. Each is best-effort —
  // a failed roster degrades to [] without sinking the whole snapshot.
  const rosterLists = await Promise.all(
    rawTournaments.map((t) => getTournamentRoster(t.id).catch(() => [])),
  );
  const rosterById = new Map<string, string[]>();
  rawTournaments.forEach((t, i) => rosterById.set(t.id, rosterLists[i] ?? []));

  // Viewer membership + their own registrations + display name (best-effort).
  let membership: CEMembership = 'logged_out';
  let studentName: string | null = null;
  const registrationByTournament = new Map<string, string>();
  try {
    const { userId } = await auth();
    if (userId) {
      const member = await getMembershipStateForUser(userId);
      if (member.state === 'verified' && member.studentId) {
        membership = 'verified';
        const [regs, name] = await Promise.all([
          getStudentTournamentRegistrations(member.studentId),
          getStudentDisplayName(member.studentId),
        ]);
        for (const r of regs) registrationByTournament.set(r.tournament_id, r.id);
        studentName = name;
      } else {
        membership = 'unverified';
      }
    }
  } catch (err) {
    console.error('[ce-tournaments] viewer resolution failed', err);
  }

  // Branch accordion. Prefer the full CE branch directory so empty branches
  // still render (with a "No tournaments" badge) like the vanilla page; fall
  // back to branches derived from the tournament rows if the directory is
  // unavailable. Excludes НИШ / Zhandosova either way.
  let branchRows: Awaited<ReturnType<typeof listBranches>> = [];
  try {
    branchRows = await listBranches();
  } catch {
    branchRows = [];
  }
  const branchMap = new Map<string, string>();
  for (const b of branchRows) {
    if (!EXCLUDED_BRANCHES.includes(b.name)) branchMap.set(b.id, b.name);
  }
  for (const t of rawTournaments) {
    if (
      t.branch &&
      !EXCLUDED_BRANCHES.includes(t.branch.name) &&
      !branchMap.has(t.branch.id)
    ) {
      branchMap.set(t.branch.id, t.branch.name);
    }
  }
  const branches: CEBranchRef[] = [...branchMap.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name));

  const tournaments: CETournamentCard[] = rawTournaments
    .filter((t) => !(t.branch && EXCLUDED_BRANCHES.includes(t.branch.name)))
    .map((t) => {
      const roster = rosterById.get(t.id) ?? [];
      return {
        id: t.id,
        name: t.name,
        info: t.info,
        tournament_date: t.tournament_date,
        start_time: t.start_time,
        time_format: t.time_format,
        registration_fee: t.registration_fee,
        rounds: t.rounds,
        capacity: t.capacity,
        status: t.status,
        // Roster is the source of truth for who's registered; fall back to the
        // list endpoint's count only when the roster fetch came back empty.
        registered_count: roster.length || t.registered_count,
        branch_id: t.branch_id,
        branch_name: t.branch?.name ?? null,
        registration_deadline:
          (t as { registration_deadline?: string | null }).registration_deadline ??
          null,
        roster,
        registration_id: registrationByTournament.get(t.id) ?? null,
        is_registered: registrationByTournament.has(t.id),
      };
    });

  return { membership, studentName, branches, tournaments };
}

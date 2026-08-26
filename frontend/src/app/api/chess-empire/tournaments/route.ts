/**
 * GET /api/chess-empire/tournaments
 *
 * Public proxy of the CE tournament schedule (`upcoming=true`). When the caller
 * is a signed-in verified Chess Empire member, their per-tournament registration
 * status is merged in (`registration_id` / `is_registered`) so a client can
 * hydrate the "You're registered ✓" states without exposing the service key.
 *
 * The service key never leaves the server — every CE call is server-side here.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';
import { getMembershipStateForUser } from '@/lib/chess-empire-member';
import {
  listTournaments,
  getStudentTournamentRegistrations,
} from '@/lib/chess-empire-client';

export async function GET() {
  let tournaments;
  try {
    tournaments = await listTournaments(true);
  } catch (err) {
    console.error('[chess-empire/tournaments] list failed', err);
    return NextResponse.json({ error: 'server_error' }, { status: 502 });
  }

  let membership: 'logged_out' | 'unverified' | 'verified' = 'logged_out';
  const registrationByTournament = new Map<string, string>();

  try {
    const { userId } = await auth();
    if (userId) {
      const member = await getMembershipStateForUser(userId);
      if (member.state === 'verified' && member.studentId) {
        membership = 'verified';
        const regs = await getStudentTournamentRegistrations(member.studentId);
        for (const r of regs) registrationByTournament.set(r.tournament_id, r.id);
      } else {
        membership = 'unverified';
      }
    }
  } catch (err) {
    // Membership merge is best-effort — the schedule still renders list-only.
    console.error('[chess-empire/tournaments] membership merge failed', err);
  }

  const withStatus = tournaments.map((t) => ({
    ...t,
    registration_id: registrationByTournament.get(t.id) ?? null,
    is_registered: registrationByTournament.has(t.id),
  }));

  return NextResponse.json({ membership, tournaments: withStatus });
}

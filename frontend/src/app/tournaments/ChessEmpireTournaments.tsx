/**
 * Chess Empire tournaments — server view.
 *
 * Server-fetches the public schedule plus (for a signed-in verified member)
 * their registration status + display name, then hands a plain-data snapshot to
 * the client view that renders the cards and drives register/cancel. All CE
 * calls (and the service key) stay server-side.
 */
import 'server-only';
import { auth } from '@clerk/nextjs/server';
import { getMembershipStateForUser } from '@/lib/chess-empire-member';
import {
  listTournaments,
  getStudentTournamentRegistrations,
  getStudentDisplayName,
} from '@/lib/chess-empire-client';
import CETournamentsView, {
  type CETournamentCard,
  type CEViewer,
} from './CETournamentsView';

export default async function ChessEmpireTournaments() {
  let tournaments: Awaited<ReturnType<typeof listTournaments>> = [];
  try {
    tournaments = await listTournaments(true);
  } catch (err) {
    console.error('[ce-tournaments] schedule fetch failed', err);
  }

  let viewer: CEViewer = { state: 'logged_out' };
  const registrationByTournament = new Map<string, string>();

  try {
    const { userId } = await auth();
    if (userId) {
      const member = await getMembershipStateForUser(userId);
      if (member.state === 'verified' && member.studentId) {
        const [regs, name] = await Promise.all([
          getStudentTournamentRegistrations(member.studentId),
          getStudentDisplayName(member.studentId),
        ]);
        for (const r of regs) registrationByTournament.set(r.tournament_id, r.id);
        viewer = { state: 'verified', studentName: name };
      } else {
        viewer = { state: 'unverified' };
      }
    }
  } catch (err) {
    console.error('[ce-tournaments] viewer resolution failed', err);
  }

  const cards: CETournamentCard[] = tournaments.map((t) => ({
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
    registered_count: t.registered_count,
    branch_name: t.branch?.name ?? null,
    registration_id: registrationByTournament.get(t.id) ?? null,
  }));

  return <CETournamentsView tournaments={cards} viewer={viewer} />;
}

/**
 * `/tournaments` router.
 *
 * On the chess-empire tenant host (`chess-empire.chesster.io`) this renders the
 * Chess Empire league schedule with a member-only registration gate. Everywhere
 * else (apex `chesster.io`, other tenants) it renders the existing Flask-backed
 * tournament calendar, unchanged.
 *
 * Tenant detection mirrors `/dashboard`: `x-org-id` present AND
 * `x-org-slug === 'chess-empire'` (set on the request headers by middleware).
 */
import { headers } from 'next/headers';
import TournamentsCalendar from './TournamentsCalendar';
import ChessEmpireTournaments from './ChessEmpireTournaments';

export const dynamic = 'force-dynamic';

export default async function TournamentsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
} = {}) {
  const headersList = await headers();
  const orgId = headersList.get('x-org-id');
  const orgSlug = headersList.get('x-org-slug');

  if (orgId && orgSlug === 'chess-empire') {
    // app.chessempire.kz deep-links registrants here with `?tournament=<id>`.
    const sp = (await searchParams) ?? {};
    const raw = sp.tournament;
    const deepLinkTournamentId = Array.isArray(raw) ? raw[0] ?? null : raw ?? null;
    return (
      <ChessEmpireTournaments deepLinkTournamentId={deepLinkTournamentId} />
    );
  }

  return <TournamentsCalendar />;
}

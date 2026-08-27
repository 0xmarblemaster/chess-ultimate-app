/**
 * GET /api/chess-empire/tournaments
 *
 * Public proxy of the CE tournament schedule snapshot: branches, per-tournament
 * rosters (full names), and — for a signed-in verified member — their own
 * registration status merged per tournament. Backs the chess-empire tenant
 * `/tournaments` page's 15s polling refresh.
 *
 * The service key never leaves the server — every CE call is server-side here.
 */
import 'server-only';
import { NextResponse } from 'next/server';
import { loadCETournamentSnapshot } from '@/lib/ce-tournaments-data';

export async function GET() {
  const snapshot = await loadCETournamentSnapshot();
  return NextResponse.json(snapshot);
}

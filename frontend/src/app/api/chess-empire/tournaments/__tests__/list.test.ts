/**
 * Tests for GET /api/chess-empire/tournaments.
 *
 * Covers: logged-out → list with membership:'logged_out' and no registration
 * status; verified member → registration status merged per tournament; list
 * fetch failure → 502.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const authStore: { userId: string | null } = { userId: null };
vi.mock('@clerk/nextjs/server', () => ({
  auth: async () => ({ userId: authStore.userId }),
}));

const memberStore: { result: { state: string; studentId: string | null } } = {
  result: { state: 'verified', studentId: 'stu-1' },
};
vi.mock('@/lib/chess-empire-member', () => ({
  getMembershipStateForUser: vi.fn(async () => memberStore.result),
}));

const listMock = vi.fn();
const regsMock = vi.fn();
vi.mock('@/lib/chess-empire-client', () => ({
  listTournaments: (...args: unknown[]) => listMock(...args),
  getStudentTournamentRegistrations: (...args: unknown[]) => regsMock(...args),
}));

import { GET } from '../route';

beforeEach(() => {
  authStore.userId = null;
  memberStore.result = { state: 'verified', studentId: 'stu-1' };
  listMock.mockReset();
  regsMock.mockReset();
});

describe('GET /api/chess-empire/tournaments', () => {
  it('logged out → list with membership logged_out, is_registered false', async () => {
    listMock.mockResolvedValue([{ id: 't1', name: 'Blitz' }]);
    const res = await GET();
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      membership: string;
      tournaments: Array<{ is_registered: boolean; registration_id: string | null }>;
    };
    expect(body.membership).toBe('logged_out');
    expect(body.tournaments[0].is_registered).toBe(false);
    expect(body.tournaments[0].registration_id).toBeNull();
    expect(regsMock).not.toHaveBeenCalled();
  });

  it('verified member → merges registration status per tournament', async () => {
    authStore.userId = 'user-1';
    listMock.mockResolvedValue([
      { id: 't1', name: 'Blitz' },
      { id: 't2', name: 'Rapid' },
    ]);
    regsMock.mockResolvedValue([
      { id: 'reg-1', tournament_id: 't1', registered_at: 'x' },
    ]);
    const res = await GET();
    const body = (await res.json()) as {
      membership: string;
      tournaments: Array<{
        id: string;
        is_registered: boolean;
        registration_id: string | null;
      }>;
    };
    expect(body.membership).toBe('verified');
    expect(body.tournaments[0]).toMatchObject({
      id: 't1',
      is_registered: true,
      registration_id: 'reg-1',
    });
    expect(body.tournaments[1]).toMatchObject({
      id: 't2',
      is_registered: false,
      registration_id: null,
    });
  });

  it('502 when the schedule fetch fails', async () => {
    listMock.mockRejectedValue(new Error('down'));
    const res = await GET();
    expect(res.status).toBe(502);
  });
});

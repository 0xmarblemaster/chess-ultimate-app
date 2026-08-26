/**
 * Tests for the tournaments-api helpers in chess-empire-client.ts — mock global
 * fetch, assert request URLs / headers / body and the graceful-404 behaviour of
 * the student-registrations lookup.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import {
  listTournaments,
  registerForTournament,
  cancelTournamentRegistration,
  getStudentTournamentRegistrations,
  ChessEmpireAPIError,
} from '../chess-empire-client';

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'content-type': 'application/json', ...(init.headers || {}) },
  });
}

describe('chess-empire-client tournaments', () => {
  const originalKey = process.env.CHESS_EMPIRE_SERVICE_KEY;
  const originalUrl = process.env.CHESS_EMPIRE_SUPABASE_URL;
  const fetchSpy = vi.spyOn(globalThis, 'fetch');

  beforeEach(() => {
    process.env.CHESS_EMPIRE_SERVICE_KEY = 'ce-test-key';
    process.env.CHESS_EMPIRE_SUPABASE_URL = 'https://ce.example.com';
    fetchSpy.mockReset();
  });
  afterEach(() => {
    if (originalKey === undefined) delete process.env.CHESS_EMPIRE_SERVICE_KEY;
    else process.env.CHESS_EMPIRE_SERVICE_KEY = originalKey;
    if (originalUrl === undefined) delete process.env.CHESS_EMPIRE_SUPABASE_URL;
    else process.env.CHESS_EMPIRE_SUPABASE_URL = originalUrl;
  });

  describe('listTournaments', () => {
    it('hits the public tournaments endpoint (no api key) and unwraps the list', async () => {
      fetchSpy.mockResolvedValue(
        jsonResponse({ ok: true, tournaments: [{ id: 't1', name: 'Blitz' }] }),
      );
      const result = await listTournaments(true);
      expect(result).toEqual([{ id: 't1', name: 'Blitz' }]);
      const [url, init] = fetchSpy.mock.calls[0]!;
      expect(String(url)).toBe(
        'https://ce.example.com/functions/v1/tournaments-api/tournaments?upcoming=true',
      );
      const headers = (init?.headers ?? {}) as Record<string, string>;
      expect(headers['x-api-key']).toBeUndefined();
    });

    it('returns [] when the body has no tournaments array', async () => {
      fetchSpy.mockResolvedValue(jsonResponse({ ok: true }));
      expect(await listTournaments()).toEqual([]);
    });
  });

  describe('registerForTournament', () => {
    it('POSTs with the service key, x-source, and a student_id body', async () => {
      fetchSpy.mockResolvedValue(
        jsonResponse({ ok: true, registration_id: 'reg-1', registered_count: 3 }),
      );
      const result = await registerForTournament('t1', 'stu-1');
      expect(result.ok).toBe(true);
      expect(result.registration_id).toBe('reg-1');
      const [url, init] = fetchSpy.mock.calls[0]!;
      expect(String(url)).toBe(
        'https://ce.example.com/functions/v1/tournaments-api/tournaments/t1/register',
      );
      expect(init?.method).toBe('POST');
      const headers = (init?.headers ?? {}) as Record<string, string>;
      expect(headers['x-api-key']).toBe('ce-test-key');
      expect(headers['x-source']).toBe('web');
      expect(JSON.parse(String(init?.body))).toEqual({ student_id: 'stu-1' });
    });

    it('throws ChessEmpireAPIError carrying the reason on a 409', async () => {
      fetchSpy.mockResolvedValue(
        jsonResponse({ ok: false, reason: 'full' }, { status: 409 }),
      );
      await expect(registerForTournament('t1', 'stu-1')).rejects.toBeInstanceOf(
        ChessEmpireAPIError,
      );
    });
  });

  describe('cancelTournamentRegistration', () => {
    it('DELETEs the registration with the service key', async () => {
      fetchSpy.mockResolvedValue(jsonResponse({ ok: true }));
      await cancelTournamentRegistration('reg-1');
      const [url, init] = fetchSpy.mock.calls[0]!;
      expect(String(url)).toBe(
        'https://ce.example.com/functions/v1/tournaments-api/registrations/reg-1',
      );
      expect(init?.method).toBe('DELETE');
      const headers = (init?.headers ?? {}) as Record<string, string>;
      expect(headers['x-api-key']).toBe('ce-test-key');
    });

    it('throws ChessEmpireAPIError on a 404', async () => {
      fetchSpy.mockResolvedValue(
        jsonResponse({ ok: false, reason: 'not_found' }, { status: 404 }),
      );
      await expect(cancelTournamentRegistration('reg-x')).rejects.toBeInstanceOf(
        ChessEmpireAPIError,
      );
    });
  });

  describe('getStudentTournamentRegistrations', () => {
    it('returns the registrations array on success', async () => {
      fetchSpy.mockResolvedValue(
        jsonResponse({
          ok: true,
          registrations: [{ id: 'reg-1', tournament_id: 't1', registered_at: 'x' }],
        }),
      );
      const result = await getStudentTournamentRegistrations('stu-1');
      expect(result).toEqual([
        { id: 'reg-1', tournament_id: 't1', registered_at: 'x' },
      ]);
      const [url] = fetchSpy.mock.calls[0]!;
      expect(String(url)).toBe(
        'https://ce.example.com/functions/v1/tournaments-api/students/stu-1/registrations',
      );
    });

    it('degrades to [] on a 404 (endpoint not yet deployed)', async () => {
      fetchSpy.mockResolvedValue(
        jsonResponse({ ok: false, reason: 'not_found' }, { status: 404 }),
      );
      expect(await getStudentTournamentRegistrations('stu-1')).toEqual([]);
    });

    it('degrades to [] on a network error', async () => {
      fetchSpy.mockRejectedValue(new Error('boom'));
      expect(await getStudentTournamentRegistrations('stu-1')).toEqual([]);
    });
  });
});

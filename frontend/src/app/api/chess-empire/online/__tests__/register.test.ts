/**
 * Tests for /api/chess-empire/online/register.
 *
 * The online-students flow skips the CE roster search entirely: it resolves an
 * `kind='online'` invite token and mints a synthetic-student invite JWT that
 * carries `external_source='online'` + the token's `access_ttl_hours`. Covers:
 * missing fields (400), non-online / invalid tokens (401), and the happy path
 * (200 → JWT verifies with the online marker + TTL + a synthetic student id).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

interface ScriptedResponse {
  data?: unknown;
  error?: unknown;
}

const scripts: Record<string, ScriptedResponse[]> = {};

function nextScript(table: string, op: string): ScriptedResponse {
  const queue = scripts[`${table}.${op}`];
  if (!queue || queue.length === 0) return { data: null, error: null };
  return queue.shift() as ScriptedResponse;
}

function makeBuilder(table: string) {
  const chain: Record<string, unknown> = {
    select() {
      return chain;
    },
    eq() {
      return chain;
    },
    maybeSingle() {
      return Promise.resolve(nextScript(table, 'maybeSingle'));
    },
  };
  return chain;
}

vi.mock('@/lib/supabase-admin', () => ({
  supabaseAdmin: {
    from: (table: string) => makeBuilder(table),
  },
}));

import { POST } from '../register/route';
import { verifyInviteJwt } from '@/lib/invite-jwt';
import { _resetRateLimitForTests } from '@/lib/in-memory-rate-limit';
import { NextRequest } from 'next/server';

const ONLINE_TOKEN = {
  id: 'token-online-1',
  organization_id: 'org-1',
  external_branch_id: 'br-online',
  kind: 'online',
  access_ttl_hours: 72,
  expires_at: null,
  revoked_at: null,
};

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://x/api/chess-empire/online/register', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

beforeEach(() => {
  for (const k of Object.keys(scripts)) delete scripts[k];
  _resetRateLimitForTests();
  process.env.INVITE_JWT_SECRET = 'unit-test-secret';
});

describe('POST /api/chess-empire/online/register', () => {
  it('400 on missing fields', async () => {
    expect((await POST(makeReq({}))).status).toBe(400);
    expect((await POST(makeReq({ branchToken: 't' }))).status).toBe(400);
    expect((await POST(makeReq({ name: 'Sam' }))).status).toBe(400);
  });

  it('401 when the token does not exist', async () => {
    scripts['branch_invite_tokens.maybeSingle'] = [{ data: null, error: null }];
    const res = await POST(makeReq({ branchToken: 'bad', name: 'Sam' }));
    expect(res.status).toBe(401);
  });

  it('401 for a branch token (online endpoint rejects kind=branch)', async () => {
    scripts['branch_invite_tokens.maybeSingle'] = [
      { data: { ...ONLINE_TOKEN, kind: 'branch' }, error: null },
    ];
    const res = await POST(makeReq({ branchToken: 't', name: 'Sam' }));
    expect(res.status).toBe(401);
  });

  it('401 for a revoked online token', async () => {
    scripts['branch_invite_tokens.maybeSingle'] = [
      { data: { ...ONLINE_TOKEN, revoked_at: '2020-01-01T00:00:00Z' }, error: null },
    ];
    const res = await POST(makeReq({ branchToken: 't', name: 'Sam' }));
    expect(res.status).toBe(401);
  });

  it('mints a JWT carrying the online marker, TTL, and a synthetic student id', async () => {
    scripts['branch_invite_tokens.maybeSingle'] = [
      { data: ONLINE_TOKEN, error: null },
    ];
    const res = await POST(makeReq({ branchToken: 't', name: 'Sam' }));
    expect(res.status).toBe(200);
    const body = (await res.json()) as { inviteJwt?: string };
    expect(typeof body.inviteJwt).toBe('string');

    const claims = verifyInviteJwt(body.inviteJwt!);
    expect(claims.external_source).toBe('online');
    expect(claims.member_type).toBe('student');
    expect(claims.access_ttl_hours).toBe(72);
    expect(claims.branch_id).toBe('br-online');
    expect(claims.org_id).toBe('org-1');
    expect(claims.branch_token_id).toBe('token-online-1');
    // Synthetic student id — a non-empty UUID, not a real CE record.
    expect(claims.student_id).toMatch(/^[0-9a-f-]{36}$/);
  });

  it('gives each online sign-up a distinct synthetic student id', async () => {
    scripts['branch_invite_tokens.maybeSingle'] = [
      { data: ONLINE_TOKEN, error: null },
      { data: ONLINE_TOKEN, error: null },
    ];
    const a = (await (await POST(makeReq({ branchToken: 't', name: 'A' }))).json()) as {
      inviteJwt: string;
    };
    const b = (await (await POST(makeReq({ branchToken: 't', name: 'B' }))).json()) as {
      inviteJwt: string;
    };
    expect(verifyInviteJwt(a.inviteJwt).student_id).not.toBe(
      verifyInviteJwt(b.inviteJwt).student_id,
    );
  });
});

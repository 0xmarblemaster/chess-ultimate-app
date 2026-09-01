import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';

// Clerk auth mock.
vi.mock('@clerk/nextjs/server', () => ({ auth: vi.fn() }));

// Supabase admin mock — scriptable select + recorded upsert.
const db = vi.hoisted(() => ({
  selectResult: { data: null as unknown, error: null as unknown },
  upsertResult: { error: null as unknown },
  lastUpsert: null as { payload: unknown; opts: unknown } | null,
}));

vi.mock('@/lib/supabase-admin', () => ({
  supabaseAdmin: {
    from() {
      return {
        select() {
          return this;
        },
        eq() {
          return this;
        },
        maybeSingle() {
          return Promise.resolve(db.selectResult);
        },
        upsert(payload: unknown, opts: unknown) {
          db.lastUpsert = { payload, opts };
          return Promise.resolve(db.upsertResult);
        },
      };
    },
  },
}));

import { auth } from '@clerk/nextjs/server';
import { GET, POST } from '../route';

function mockAuth(userId: string | null) {
  (auth as unknown as { mockResolvedValue: (v: unknown) => void }).mockResolvedValue({ userId });
}

function getReq(key?: string): NextRequest {
  const url = key
    ? `http://localhost/api/coach/review-cache?key=${encodeURIComponent(key)}`
    : 'http://localhost/api/coach/review-cache';
  return new NextRequest(url);
}

function postReq(body: unknown, raw?: string): NextRequest {
  return new NextRequest('http://localhost/api/coach/review-cache', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: raw ?? JSON.stringify(body),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  db.selectResult = { data: null, error: null };
  db.upsertResult = { error: null };
  db.lastUpsert = null;
});

describe('GET /api/coach/review-cache', () => {
  it('401s when unauthenticated', async () => {
    mockAuth(null);
    const res = await GET(getReq('v1:explain:x'));
    expect(res.status).toBe(401);
  });

  it('400s when key is missing', async () => {
    mockAuth('user_1');
    const res = await GET(getReq());
    expect(res.status).toBe(400);
  });

  it('returns { content: null } on a cache miss', async () => {
    mockAuth('user_1');
    db.selectResult = { data: null, error: null };
    const res = await GET(getReq('v1:explain:miss'));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ content: null, model: null });
  });

  it('returns the stored content + model on a hit', async () => {
    mockAuth('user_1');
    db.selectResult = { data: { content: 'hi there', model: 'claude-opus' }, error: null };
    const res = await GET(getReq('v1:explain:hit'));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ content: 'hi there', model: 'claude-opus' });
  });

  it('502s when the DB errors', async () => {
    mockAuth('user_1');
    db.selectResult = { data: null, error: { message: 'db down' } };
    const res = await GET(getReq('v1:explain:err'));
    expect(res.status).toBe(502);
  });
});

describe('POST /api/coach/review-cache', () => {
  it('401s when unauthenticated', async () => {
    mockAuth(null);
    const res = await POST(postReq({ cache_key: 'k', kind: 'explain', locale: 'en', content: 'c' }));
    expect(res.status).toBe(401);
  });

  it('400s on invalid JSON', async () => {
    mockAuth('user_1');
    const res = await POST(postReq(null, '}{not json'));
    expect(res.status).toBe(400);
  });

  it('400s on missing fields', async () => {
    mockAuth('user_1');
    const res = await POST(postReq({ cache_key: 'k', locale: 'en' }));
    expect(res.status).toBe(400);
  });

  it('400s on an invalid kind', async () => {
    mockAuth('user_1');
    const res = await POST(
      postReq({ cache_key: 'k', kind: 'bogus', locale: 'en', content: 'c' }),
    );
    expect(res.status).toBe(400);
  });

  it('upserts a valid explain payload (ignore-duplicates on cache_key)', async () => {
    mockAuth('user_1');
    const res = await POST(
      postReq({ cache_key: 'v1:explain:k', kind: 'explain', locale: 'en', content: 'hi', model: 'm' }),
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });
    expect(db.lastUpsert?.payload).toMatchObject({
      cache_key: 'v1:explain:k',
      kind: 'explain',
      locale: 'en',
      content: 'hi',
      model: 'm',
    });
    expect(db.lastUpsert?.opts).toMatchObject({ onConflict: 'cache_key', ignoreDuplicates: true });
  });

  it('defaults model to null when omitted', async () => {
    mockAuth('user_1');
    await POST(postReq({ cache_key: 'k', kind: 'summary', locale: 'ru', content: 'c' }));
    expect((db.lastUpsert?.payload as { model: unknown }).model).toBeNull();
  });

  it('502s when the upsert errors', async () => {
    mockAuth('user_1');
    db.upsertResult = { error: { message: 'write failed' } };
    const res = await POST(
      postReq({ cache_key: 'k', kind: 'explain', locale: 'en', content: 'c' }),
    );
    expect(res.status).toBe(502);
  });
});

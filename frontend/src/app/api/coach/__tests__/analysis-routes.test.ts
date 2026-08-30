import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Clerk auth
vi.mock('@clerk/nextjs/server', () => ({
  auth: vi.fn(),
}));

import { auth } from '@clerk/nextjs/server';

const FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

// Build a fetch Response whose body streams the given SSE lines, mirroring
// Hermes' text/event-stream output.
function sseResponse(frames: Record<string, unknown>[], ok = true) {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(frame)}\n\n`));
      }
      controller.close();
    },
  });
  return { ok, status: ok ? 200 : 500, body } as any;
}

describe('Coach Analysis API Routes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('POST /api/coach/analysis', () => {
    it('returns 401 when not authenticated', async () => {
      (auth as any).mockResolvedValue({ userId: null });

      const { POST } = await import('../../coach/analysis/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest('http://localhost:3000/api/coach/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fen: FEN, query: 'analyze' }),
      });

      const response = await POST(request as any);
      expect(response.status).toBe(401);
      expect((await response.json()).error).toBe('Unauthorized');
    });

    it('returns 400 when fen is missing', async () => {
      (auth as any).mockResolvedValue({ userId: 'user_123' });

      const { POST } = await import('../../coach/analysis/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest('http://localhost:3000/api/coach/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: 'analyze' }),
      });

      const response = await POST(request as any);
      expect(response.status).toBe(400);
      expect((await response.json()).error).toBe('Missing fen');
    });

    it('returns 400 when query is missing', async () => {
      (auth as any).mockResolvedValue({ userId: 'user_123' });

      const { POST } = await import('../../coach/analysis/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest('http://localhost:3000/api/coach/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fen: FEN }),
      });

      const response = await POST(request as any);
      expect(response.status).toBe(400);
      expect((await response.json()).error).toBe('Missing query');
    });

    it('forwards to Hermes with the Clerk user id and returns the response shape', async () => {
      (auth as any).mockResolvedValue({ userId: 'user_123' });

      const hermesBody = {
        success: true,
        response: 'This is a solid opening position.',
        conversation_id: 'conv_1',
        tokens_used: 42,
        usage: { hourly_remaining: 10, daily_remaining: 100, tier: 'free' },
      };
      const fetchMock = vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => hermesBody,
      }));
      global.fetch = fetchMock as any;

      const { POST } = await import('../../coach/analysis/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest('http://localhost:3000/api/coach/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fen: FEN,
          query: 'analyze this',
          conversation_id: 'conv_1',
          context_type: 'position',
        }),
      });

      const response = await POST(request as any);
      expect(response.status).toBe(200);
      expect(await response.json()).toEqual(hermesBody);

      const [url, opts] = fetchMock.mock.calls[0] as any[];
      expect(url).toContain('/api/coach/analysis');
      expect(opts.headers['X-User-Id']).toBe('user_123');
      expect(JSON.parse(opts.body)).toEqual({
        fen: FEN,
        query: 'analyze this',
        conversation_id: 'conv_1',
        context_type: 'position',
      });
    });

    it('passes a 429 rate-limit response through', async () => {
      (auth as any).mockResolvedValue({ userId: 'user_123' });

      const hermesBody = {
        success: false,
        error: 'Rate limit exceeded for free tier. Limit: 10 requests per minute.',
        rate_limited: true,
      };
      global.fetch = vi.fn(async () => ({
        ok: false,
        status: 429,
        json: async () => hermesBody,
      })) as any;

      const { POST } = await import('../../coach/analysis/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest('http://localhost:3000/api/coach/analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fen: FEN, query: 'analyze' }),
      });

      const response = await POST(request as any);
      expect(response.status).toBe(429);
      expect(await response.json()).toEqual(hermesBody);
    });
  });

  describe('POST /api/coach/analysis/stream', () => {
    it('returns 401 when not authenticated', async () => {
      (auth as any).mockResolvedValue({ userId: null });

      const { POST } = await import('../../coach/analysis/stream/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest(
        'http://localhost:3000/api/coach/analysis/stream',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fen: FEN, query: 'analyze' }),
        },
      );

      const response = await POST(request as any);
      expect(response.status).toBe(401);
      expect((await response.json()).error).toBe('Unauthorized');
    });

    it('returns 400 when query is missing', async () => {
      (auth as any).mockResolvedValue({ userId: 'user_123' });

      const { POST } = await import('../../coach/analysis/stream/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest(
        'http://localhost:3000/api/coach/analysis/stream',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fen: FEN }),
        },
      );

      const response = await POST(request as any);
      expect(response.status).toBe(400);
      expect((await response.json()).error).toBe('Missing query');
    });

    it('passes SSE frames through ({delta} then {done})', async () => {
      (auth as any).mockResolvedValue({ userId: 'user_123' });

      global.fetch = vi.fn(async () =>
        sseResponse([
          { delta: 'Hello ' },
          { delta: 'world' },
          { done: true, conversation_id: 'conv_9', tokens_used: 5 },
        ]),
      ) as any;

      const { POST } = await import('../../coach/analysis/stream/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest(
        'http://localhost:3000/api/coach/analysis/stream',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fen: FEN, query: 'analyze' }),
        },
      );

      const response = await POST(request as any);
      expect(response.headers.get('Content-Type')).toBe('text/event-stream');

      const text = await response.text();
      const frames = text
        .split('\n\n')
        .filter((l) => l.startsWith('data: '))
        .map((l) => JSON.parse(l.slice(6)));

      expect(frames).toEqual([
        { delta: 'Hello ' },
        { delta: 'world' },
        { done: true, conversation_id: 'conv_9', tokens_used: 5 },
      ]);
    });
  });

  describe('GET /api/coach/history/[id]', () => {
    it('returns 401 when not authenticated', async () => {
      (auth as any).mockResolvedValue({ userId: null });

      const { GET } = await import('../../coach/history/[id]/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest(
        'http://localhost:3000/api/coach/history/conv_1',
      );

      const response = await GET(request as any, {
        params: Promise.resolve({ id: 'conv_1' }),
      });
      expect(response.status).toBe(401);
      expect((await response.json()).error).toBe('Unauthorized');
    });

    it('forwards to Hermes and returns {messages}', async () => {
      (auth as any).mockResolvedValue({ userId: 'user_123' });

      const hermesBody = {
        success: true,
        conversation: { id: 'conv_1', type: 'analysis' },
        messages: [
          { role: 'user', content: 'hi', timestamp: 1 },
          { role: 'assistant', content: 'hello', timestamp: 2 },
        ],
      };
      const fetchMock = vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => hermesBody,
      }));
      global.fetch = fetchMock as any;

      const { GET } = await import('../../coach/history/[id]/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest(
        'http://localhost:3000/api/coach/history/conv_1',
      );

      const response = await GET(request as any, {
        params: Promise.resolve({ id: 'conv_1' }),
      });
      expect(response.status).toBe(200);
      expect(await response.json()).toEqual(hermesBody);

      const [url, opts] = fetchMock.mock.calls[0] as any[];
      expect(url).toContain('/api/coach/history/conv_1');
      expect(opts.headers['X-User-Id']).toBe('user_123');
    });

    it('passes a 404 not-found response through', async () => {
      (auth as any).mockResolvedValue({ userId: 'user_123' });

      const hermesBody = {
        success: false,
        error: 'Conversation not found or access denied',
      };
      global.fetch = vi.fn(async () => ({
        ok: false,
        status: 404,
        json: async () => hermesBody,
      })) as any;

      const { GET } = await import('../../coach/history/[id]/route');
      const { NextRequest } = await import('next/server');
      const request = new NextRequest(
        'http://localhost:3000/api/coach/history/missing',
      );

      const response = await GET(request as any, {
        params: Promise.resolve({ id: 'missing' }),
      });
      expect(response.status).toBe(404);
      expect(await response.json()).toEqual(hermesBody);
    });
  });
});

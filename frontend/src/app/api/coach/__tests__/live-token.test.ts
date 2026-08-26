import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Clerk auth
vi.mock('@clerk/nextjs/server', () => ({
  auth: vi.fn(),
}));

// Mock @google/genai so no real network call happens.
const createMock = vi.fn();
vi.mock('@google/genai', () => ({
  GoogleGenAI: class {
    authTokens = { create: createMock };
  },
  Modality: { AUDIO: 'AUDIO' },
}));

import { auth } from '@clerk/nextjs/server';

const makeRequest = (body?: unknown) =>
  new Request('http://localhost:3000/api/coach/live-token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

describe('POST /api/coach/live-token', () => {
  const originalKey = process.env.GEMINI_API_KEY;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (originalKey === undefined) {
      delete process.env.GEMINI_API_KEY;
    } else {
      process.env.GEMINI_API_KEY = originalKey;
    }
    vi.restoreAllMocks();
  });

  it('returns 401 when not authenticated', async () => {
    (auth as any).mockResolvedValue({ userId: null });

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({}));

    expect(response.status).toBe(401);
    const data = await response.json();
    expect(data.error).toBe('Unauthorized');
  });

  it('returns 500 when GEMINI_API_KEY is unset', async () => {
    (auth as any).mockResolvedValue({ userId: 'user_123' });
    delete process.env.GEMINI_API_KEY;

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({}));

    expect(response.status).toBe(500);
    const data = await response.json();
    expect(data.error).toBe('Live coach not configured');
  });

  it('returns 200 with token, model and expiresAt when mint succeeds', async () => {
    (auth as any).mockResolvedValue({ userId: 'user_123' });
    process.env.GEMINI_API_KEY = 'AQ.test-key';
    createMock.mockResolvedValue({ name: 'ephemeral-token-xyz' });
    global.fetch = vi.fn(async () => ({ ok: true, json: async () => ({ tools: [] }) })) as any;

    const { POST } = await import('../live-token/route');
    const response = await POST(
      makeRequest({ fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1' }),
    );

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.token).toBe('ephemeral-token-xyz');
    expect(data.model).toBe('gemini-3.1-flash-live-preview');
    expect(typeof data.expiresAt).toBe('string');
    expect(createMock).toHaveBeenCalledTimes(1);
  });

  it('returns 502 when the mint call rejects', async () => {
    (auth as any).mockResolvedValue({ userId: 'user_123' });
    process.env.GEMINI_API_KEY = 'AQ.test-key';
    createMock.mockRejectedValue(new Error('google boom'));
    global.fetch = vi.fn(async () => ({ ok: true, json: async () => ({ tools: [] }) })) as any;
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({}));

    expect(response.status).toBe(502);
    const data = await response.json();
    expect(data.error).toBe('Failed to start live session');
    errorSpy.mockRestore();
  });

  // ── Shared conversation memory injection ────────────────────────────────────

  const systemInstructionFromMint = () => {
    const call = createMock.mock.calls[0][0];
    return call.config.liveConnectConstraints.config.systemInstruction as string;
  };

  it('injects a conversation recap from Hermes when session_id is present', async () => {
    (auth as any).mockResolvedValue({ userId: 'user_123' });
    process.env.GEMINI_API_KEY = 'AQ.test-key';
    createMock.mockResolvedValue({ name: 'ephemeral-token-xyz' });

    const fetchSpy = vi.fn(async (url: string) => {
      if (String(url).includes('/api/coach/tools')) {
        return { ok: true, json: async () => ({ tools: [] }) };
      }
      return {
        ok: true,
        json: async () => ({
          messages: [
            { role: 'user', content: 'How do I attack the king?', source: 'text' },
            { role: 'assistant', content: 'Open lines first.', source: 'text' },
            { role: 'user', content: 'Like this?', source: 'voice' },
          ],
        }),
      };
    });
    global.fetch = fetchSpy as any;

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({ session_id: 'sess_1' }));

    expect(response.status).toBe(200);
    // Fetched the last 20 messages for this session, scoped by user.
    const recapCall = fetchSpy.mock.calls.find((c: any[]) =>
      String(c[0]).includes('/messages'),
    );
    expect(recapCall).toBeTruthy();
    const [url, opts] = recapCall as any[];
    expect(url).toContain('/api/coach/sessions/sess_1/messages');
    expect(url).toContain('limit=20');
    expect(opts.headers['X-User-Id']).toBe('user_123');

    const instruction = systemInstructionFromMint();
    expect(instruction).toContain('continuing an ongoing coaching conversation');
    expect(instruction).toContain('How do I attack the king?');
    expect(instruction).toContain('Open lines first.');
    // Voice-sourced lines may be tagged.
    expect(instruction).toContain('[user (spoken)] Like this?');
  });

  it('does not fetch the recap when no session_id is provided', async () => {
    (auth as any).mockResolvedValue({ userId: 'user_123' });
    process.env.GEMINI_API_KEY = 'AQ.test-key';
    createMock.mockResolvedValue({ name: 'ephemeral-token-xyz' });

    const fetchSpy = vi.fn(async () => ({ ok: true, json: async () => ({ tools: [] }) }));
    global.fetch = fetchSpy as any;

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({ fen: 'somefen' }));

    expect(response.status).toBe(200);
    // Tools are still fetched, but no session message recap.
    const recapCall = fetchSpy.mock.calls.find((c: any[]) =>
      String(c[0]).includes('/messages'),
    );
    expect(recapCall).toBeUndefined();
    expect(systemInstructionFromMint()).not.toContain(
      'continuing an ongoing coaching conversation',
    );
  });

  // ── Tool declaration embedding ──────────────────────────────────────────────

  const configFromMint = () =>
    createMock.mock.calls[0][0].config.liveConnectConstraints.config;

  it('embeds tool functionDeclarations from Hermes into the token constraints', async () => {
    (auth as any).mockResolvedValue({ userId: 'user_123' });
    process.env.GEMINI_API_KEY = 'AQ.test-key';
    createMock.mockResolvedValue({ name: 'ephemeral-token-xyz' });

    const decls = [
      { name: 'board_control', description: 'control board', parameters: { type: 'object' } },
    ];
    global.fetch = vi.fn(async (url: string) => {
      if (String(url).includes('/api/coach/tools')) {
        return { ok: true, json: async () => ({ tools: decls }) };
      }
      return { ok: true, json: async () => ({ messages: [] }) };
    }) as any;

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({ fen: 'somefen' }));

    expect(response.status).toBe(200);
    const config = configFromMint();
    expect(config.tools).toEqual([{ functionDeclarations: decls }]);
    expect(config.systemInstruction).toContain('You have tools.');
  });

  it('enables sessionResumption in the token constraints so the server issues handles', async () => {
    (auth as any).mockResolvedValue({ userId: 'user_123' });
    process.env.GEMINI_API_KEY = 'AQ.test-key';
    createMock.mockResolvedValue({ name: 'ephemeral-token-xyz' });
    global.fetch = vi.fn(async () => ({ ok: true, json: async () => ({ tools: [] }) })) as any;

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({ fen: 'somefen' }));

    expect(response.status).toBe(200);
    expect(configFromMint().sessionResumption).toEqual({});
  });

  it('mints the token without tools (still 200) when the tools fetch fails', async () => {
    (auth as any).mockResolvedValue({ userId: 'user_123' });
    process.env.GEMINI_API_KEY = 'AQ.test-key';
    createMock.mockResolvedValue({ name: 'ephemeral-token-xyz' });
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    global.fetch = vi.fn(async () => ({ ok: false, status: 503, json: async () => ({}) })) as any;

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({ fen: 'somefen' }));

    expect(response.status).toBe(200);
    expect(configFromMint().tools).toBeUndefined();
    warnSpy.mockRestore();
  });

  it('falls back to no recap (still 200) when the Hermes fetch fails', async () => {
    (auth as any).mockResolvedValue({ userId: 'user_123' });
    process.env.GEMINI_API_KEY = 'AQ.test-key';
    createMock.mockResolvedValue({ name: 'ephemeral-token-xyz' });
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    global.fetch = vi.fn().mockRejectedValue(new Error('hermes down')) as any;

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({ session_id: 'sess_1' }));

    // Voice must still start even if Hermes is unreachable.
    expect(response.status).toBe(200);
    expect(systemInstructionFromMint()).not.toContain(
      'continuing an ongoing coaching conversation',
    );
    errorSpy.mockRestore();
  });
});

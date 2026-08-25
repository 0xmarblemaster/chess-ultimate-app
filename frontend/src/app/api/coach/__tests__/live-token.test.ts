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
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { POST } = await import('../live-token/route');
    const response = await POST(makeRequest({}));

    expect(response.status).toBe(502);
    const data = await response.json();
    expect(data.error).toBe('Failed to start live session');
    errorSpy.mockRestore();
  });
});

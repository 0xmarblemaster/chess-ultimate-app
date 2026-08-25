/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

// ---- @google/genai mock ----------------------------------------------------
const g = vi.hoisted(() => ({
  session: { sendRealtimeInput: vi.fn(), close: vi.fn() },
  connectArgs: { value: null as any },
  ctorArgs: { value: null as any },
}));

vi.mock('@google/genai', () => {
  class GoogleGenAI {
    live: { connect: (params: any) => Promise<any> };
    constructor(opts: any) {
      g.ctorArgs.value = opts;
      this.live = {
        connect: vi.fn(async (params: any) => {
          g.connectArgs.value = params;
          return g.session;
        }),
      };
    }
  }
  return { GoogleGenAI, Modality: { AUDIO: 'AUDIO' } };
});

import useGeminiLive from '../useGeminiLive';

// ---- Browser API fakes -----------------------------------------------------
const createdSources: any[] = [];
let lastWorkletNode: any = null;
const trackStop = vi.fn();

class FakeAudioContext {
  destination = {};
  currentTime = 0;
  sampleRate: number;
  audioWorklet = { addModule: vi.fn(async () => {}) };
  constructor(opts?: { sampleRate?: number }) {
    this.sampleRate = opts?.sampleRate ?? 48000;
  }
  createMediaStreamSource = vi.fn(() => ({ connect: vi.fn() }));
  createBuffer = vi.fn((_ch: number, len: number, rate: number) => ({
    duration: len / rate,
    getChannelData: () => new Float32Array(len),
  }));
  createBufferSource = vi.fn(() => {
    const src = {
      buffer: null as any,
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
      onended: null as null | (() => void),
    };
    createdSources.push(src);
    return src;
  });
  close = vi.fn(async () => {});
}

class FakeAudioWorkletNode {
  port = { onmessage: null as null | ((ev: MessageEvent) => void), postMessage: vi.fn() };
  connect = vi.fn();
  disconnect = vi.fn();
  constructor() {
    lastWorkletNode = this;
  }
}

function fakeStream(): MediaStream {
  return { getTracks: () => [{ stop: trackStop }] } as unknown as MediaStream;
}

function installBrowserMocks() {
  vi.stubGlobal('AudioContext', FakeAudioContext);
  vi.stubGlobal('AudioWorkletNode', FakeAudioWorkletNode);
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: vi.fn(async () => fakeStream()) },
  });
}

const AUDIO_B64 = btoa(String.fromCharCode(0, 1, 2, 3));

function tokenOk() {
  return vi.fn(async () => ({
    ok: true,
    json: async () => ({
      token: 'auth_tokens/abc',
      model: 'gemini-3.1-flash-live-preview',
      expiresAt: '2026-01-01T00:00:00.000Z',
    }),
  }));
}

beforeEach(() => {
  g.session.sendRealtimeInput.mockReset();
  g.session.close.mockReset();
  g.connectArgs.value = null;
  g.ctorArgs.value = null;
  createdSources.length = 0;
  lastWorkletNode = null;
  trackStop.mockReset();
  installBrowserMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useGeminiLive', () => {
  it('reports isSupported=false when AudioWorkletNode is missing', async () => {
    vi.stubGlobal('AudioWorkletNode', undefined);
    const { result } = renderHook(() => useGeminiLive());
    await waitFor(() => expect(result.current.isSupported).toBe(false));
  });

  it('reports isSupported=false when getUserMedia is missing', async () => {
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: undefined,
    });
    const { result } = renderHook(() => useGeminiLive());
    await waitFor(() => expect(result.current.isSupported).toBe(false));
  });

  it('reports isSupported=true when all APIs are present', async () => {
    const { result } = renderHook(() => useGeminiLive());
    await waitFor(() => expect(result.current.isSupported).toBe(true));
  });

  it('connect() posts to the token endpoint, passes the token as apiKey, and connects with the model', async () => {
    const fetchMock = tokenOk();
    vi.stubGlobal('fetch', fetchMock);

    const { result } = renderHook(() => useGeminiLive({ getFen: () => 'FEN' }));
    await act(async () => {
      await result.current.connect();
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/coach/live-token',
      expect.objectContaining({ method: 'POST' }),
    );
    const body = JSON.parse((fetchMock.mock.calls[0] as any[])[1].body);
    expect(body.fen).toBe('FEN');

    expect(g.ctorArgs.value.apiKey).toBe('auth_tokens/abc');
    expect(g.connectArgs.value.model).toBe('gemini-3.1-flash-live-preview');
    expect(g.connectArgs.value.config.responseModalities).toEqual(['AUDIO']);
    expect(result.current.isActive).toBe(true);
    expect(result.current.status).toBe('listening');
  });

  it('sets status=error and calls onError when the token endpoint fails', async () => {
    const fetchMock = vi.fn(async () => ({ ok: false, status: 401, json: async () => ({}) }));
    vi.stubGlobal('fetch', fetchMock);
    const onError = vi.fn();

    const { result } = renderHook(() => useGeminiLive({ onError }));
    await act(async () => {
      await result.current.connect();
    });

    expect(result.current.status).toBe('error');
    expect(result.current.isActive).toBe(false);
    expect(onError).toHaveBeenCalledOnce();
    expect(g.connectArgs.value).toBeNull(); // no session opened
  });

  it('disconnect() closes the session, stops mic tracks, and is idempotent', async () => {
    vi.stubGlobal('fetch', tokenOk());
    const { result } = renderHook(() => useGeminiLive());
    await act(async () => {
      await result.current.connect();
    });

    act(() => {
      result.current.disconnect();
    });
    expect(g.session.close).toHaveBeenCalledOnce();
    expect(trackStop).toHaveBeenCalled();
    expect(result.current.status).toBe('idle');
    expect(result.current.isActive).toBe(false);

    // Safe to call again.
    expect(() => act(() => result.current.disconnect())).not.toThrow();
  });

  it('barge-in: high-RMS worklet message while speaking flushes playback and returns to listening', async () => {
    vi.stubGlobal('fetch', tokenOk());
    const { result } = renderHook(() => useGeminiLive());
    await act(async () => {
      await result.current.connect();
    });

    // Model sends audio -> status becomes speaking.
    act(() => {
      g.connectArgs.value.callbacks.onmessage({
        serverContent: {
          modelTurn: {
            parts: [{ inlineData: { data: AUDIO_B64, mimeType: 'audio/pcm;rate=24000' } }],
          },
        },
      });
    });
    expect(result.current.status).toBe('speaking');
    expect(createdSources.length).toBe(1);

    // User speaks over the coach -> flush.
    act(() => {
      lastWorkletNode.port.onmessage({ data: { pcm: new ArrayBuffer(4), rms: 0.9 } });
    });

    expect(createdSources[0].stop).toHaveBeenCalled();
    expect(result.current.status).toBe('listening');
  });
});

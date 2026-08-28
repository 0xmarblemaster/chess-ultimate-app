/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

// ---- @google/genai mock ----------------------------------------------------
const g = vi.hoisted(() => ({
  session: {
    sendRealtimeInput: vi.fn(),
    sendClientContent: vi.fn(),
    sendToolResponse: vi.fn(),
    close: vi.fn(),
  },
  connectArgs: { value: null as any },
  connectCalls: [] as any[],
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
          g.connectCalls.push(params);
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
  g.session.sendClientContent.mockReset();
  g.session.sendToolResponse.mockReset();
  g.session.close.mockReset();
  g.connectArgs.value = null;
  g.connectCalls.length = 0;
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

  it('sends the initial FEN as a board-update turn immediately after the session opens', async () => {
    vi.stubGlobal('fetch', tokenOk());
    const { result } = renderHook(() => useGeminiLive({ getFen: () => 'INIT_FEN' }));
    await act(async () => {
      await result.current.connect();
    });

    expect(g.session.sendClientContent).toHaveBeenCalledWith({
      turns: [
        {
          role: 'user',
          parts: [{ text: 'Current position (FEN): INIT_FEN' }],
        },
      ],
      turnComplete: false,
    });
  });

  it('sendBoardUpdate() sends the FEN as a non-interrupting client turn when connected', async () => {
    vi.stubGlobal('fetch', tokenOk());
    const { result } = renderHook(() => useGeminiLive({ getFen: () => 'INIT_FEN' }));
    await act(async () => {
      await result.current.connect();
    });
    g.session.sendClientContent.mockClear();

    act(() => {
      result.current.sendBoardUpdate('NEW_FEN');
    });

    expect(g.session.sendClientContent).toHaveBeenCalledTimes(1);
    expect(g.session.sendClientContent).toHaveBeenCalledWith({
      turns: [
        {
          role: 'user',
          parts: [{ text: 'Current position (FEN): NEW_FEN' }],
        },
      ],
      turnComplete: false,
    });
  });

  it('sendBoardUpdate() no-ops safely when no session is connected', () => {
    const { result } = renderHook(() => useGeminiLive({ getFen: () => 'FEN' }));
    expect(() => act(() => result.current.sendBoardUpdate('NEW_FEN'))).not.toThrow();
    expect(g.session.sendClientContent).not.toHaveBeenCalled();
  });

  // ---- Tool bridge (Phase 2) ----------------------------------------------

  // Route fetch: token endpoint -> token; tool endpoint -> supplied handler.
  function routedFetch(toolHandler: (url: string, opts: any) => any) {
    return vi.fn(async (url: string, opts: any) => {
      if (url === '/api/coach/live-token') {
        return {
          ok: true,
          json: async () => ({
            token: 'auth_tokens/abc',
            model: 'gemini-3.1-flash-live-preview',
            expiresAt: '2026-01-01T00:00:00.000Z',
          }),
        };
      }
      return toolHandler(url, opts);
    });
  }

  it('toolCall: proxies each functionCall and replies with sendToolResponse', async () => {
    const toolPayload = {
      result: { ok: true },
      board_actions: [{ type: 'set_fen', fen: 'FEN2' }],
    };
    const fetchMock = routedFetch(() => ({ ok: true, json: async () => toolPayload }));
    vi.stubGlobal('fetch', fetchMock);
    const onToolResult = vi.fn();

    const { result } = renderHook(() =>
      useGeminiLive({ getSessionId: () => 'sess-9', onToolResult }),
    );
    await act(async () => {
      await result.current.connect();
    });

    await act(async () => {
      g.connectArgs.value.callbacks.onmessage({
        toolCall: {
          functionCalls: [{ id: 'c1', name: 'board_control', args: { action_type: 'set_fen' } }],
        },
      });
      await new Promise((r) => setTimeout(r, 0));
    });

    // Proxy was called with the tool name, args and shared session id.
    const toolCall = fetchMock.mock.calls.find((c: any[]) => c[0] === '/api/coach/tool');
    expect(toolCall).toBeTruthy();
    const body = JSON.parse((toolCall as any[])[1].body);
    expect(body).toEqual({
      name: 'board_control',
      args: { action_type: 'set_fen' },
      session_id: 'sess-9',
    });

    expect(g.session.sendToolResponse).toHaveBeenCalledWith({
      functionResponses: [
        { id: 'c1', name: 'board_control', response: { result: { ok: true } } },
      ],
    });
    expect(onToolResult).toHaveBeenCalledWith('board_control', toolPayload);
  });

  it('toolCall: answers every functionCall in one message', async () => {
    const fetchMock = routedFetch(() => ({ ok: true, json: async () => ({ result: 1 }) }));
    vi.stubGlobal('fetch', fetchMock);

    const { result } = renderHook(() => useGeminiLive());
    await act(async () => {
      await result.current.connect();
    });

    await act(async () => {
      g.connectArgs.value.callbacks.onmessage({
        toolCall: {
          functionCalls: [
            { id: 'a', name: 'tool_a', args: {} },
            { id: 'b', name: 'tool_b', args: {} },
          ],
        },
      });
      await new Promise((r) => setTimeout(r, 0));
    });

    const arg = g.session.sendToolResponse.mock.calls[0][0];
    expect(arg.functionResponses.map((r: any) => r.id).sort()).toEqual(['a', 'b']);
  });

  it('toolCall: sends an error functionResponse when the proxy fetch fails', async () => {
    const fetchMock = routedFetch(() => {
      throw new Error('network down');
    });
    vi.stubGlobal('fetch', fetchMock);

    const { result } = renderHook(() => useGeminiLive());
    await act(async () => {
      await result.current.connect();
    });

    await act(async () => {
      g.connectArgs.value.callbacks.onmessage({
        toolCall: { functionCalls: [{ id: 'c1', name: 'board_control', args: {} }] },
      });
      await new Promise((r) => setTimeout(r, 0));
    });

    const arg = g.session.sendToolResponse.mock.calls[0][0];
    expect(arg.functionResponses[0].id).toBe('c1');
    expect(arg.functionResponses[0].response.error).toBeTruthy();
  });

  // ---- Session resumption (Phase 3) ---------------------------------------

  const flush = () => new Promise((r) => setTimeout(r, 0));

  it('auto-reconnects once with the captured resumption handle on an unexpected close', async () => {
    vi.stubGlobal('fetch', tokenOk());
    const { result } = renderHook(() => useGeminiLive());
    await act(async () => {
      await result.current.connect();
    });
    const first = g.connectArgs.value;
    expect(g.connectCalls.length).toBe(1);

    // Server issues a resumable handle mid-session.
    act(() => {
      first.callbacks.onmessage({
        sessionResumptionUpdate: { resumable: true, newHandle: 'H1' },
      });
    });

    // Unexpected drop -> reconnect once, passing the handle.
    await act(async () => {
      first.callbacks.onclose();
      await flush();
    });

    expect(g.connectCalls.length).toBe(2);
    expect(g.connectCalls[1].config.sessionResumption).toEqual({ handle: 'H1' });
    expect(result.current.isActive).toBe(true);
    expect(result.current.status).toBe('listening');

    // A second drop must NOT trigger another automatic reconnect; instead the
    // unrecoverable disconnect surfaces as an error state.
    const second = g.connectCalls[1];
    await act(async () => {
      second.callbacks.onclose();
      await flush();
    });
    expect(g.connectCalls.length).toBe(2);
    expect(result.current.status).toBe('error');
  });

  it('surfaces an error (not silent idle) on close when no resumable handle was captured', async () => {
    vi.stubGlobal('fetch', tokenOk());
    const onError = vi.fn();
    const { result } = renderHook(() => useGeminiLive({ onError }));
    await act(async () => {
      await result.current.connect();
    });
    const first = g.connectArgs.value;

    // Non-resumable update carries no usable handle.
    act(() => {
      first.callbacks.onmessage({
        sessionResumptionUpdate: { resumable: false, newHandle: '' },
      });
    });

    await act(async () => {
      first.callbacks.onclose();
      await flush();
    });

    expect(g.connectCalls.length).toBe(1); // no reconnect
    expect(result.current.status).toBe('error');
    expect(result.current.error).toBeTruthy();
    expect(onError).toHaveBeenCalledOnce();
  });

  it('does not auto-reconnect after a deliberate user disconnect', async () => {
    vi.stubGlobal('fetch', tokenOk());
    const { result } = renderHook(() => useGeminiLive());
    await act(async () => {
      await result.current.connect();
    });
    const first = g.connectArgs.value;
    act(() => {
      first.callbacks.onmessage({
        sessionResumptionUpdate: { resumable: true, newHandle: 'H1' },
      });
    });

    // User stops on purpose, then a late close event arrives.
    act(() => {
      result.current.disconnect();
    });
    await act(async () => {
      first.callbacks.onclose();
      await flush();
    });

    expect(g.connectCalls.length).toBe(1); // stayed at the original connect
    expect(result.current.status).toBe('idle');
  });

  it('toolCall: a fetch that never resolves times out at 10s and replies with an error functionResponse', async () => {
    vi.useFakeTimers();
    try {
      // Tool fetch hangs forever, only settling (rejecting) when its signal aborts —
      // exactly how the real fetch behaves under an AbortController timeout.
      const fetchMock = routedFetch((_url, opts) =>
        new Promise((_resolve, reject) => {
          opts.signal.addEventListener('abort', () =>
            reject(new DOMException('aborted', 'AbortError')),
          );
        }),
      );
      vi.stubGlobal('fetch', fetchMock);

      const { result } = renderHook(() => useGeminiLive());
      await act(async () => {
        await result.current.connect();
      });

      act(() => {
        g.connectArgs.value.callbacks.onmessage({
          toolCall: {
            functionCalls: [{ id: 'c1', name: 'analyze_position', args: {} }],
          },
        });
      });

      // The tool never responds; advancing past 10s fires the timeout, which
      // aborts the fetch and forces an error functionResponse.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });

      expect(g.session.sendToolResponse).toHaveBeenCalledTimes(1);
      const arg = g.session.sendToolResponse.mock.calls[0][0];
      expect(arg.functionResponses[0].id).toBe('c1');
      expect(arg.functionResponses[0].response.error).toContain('timed out');
    } finally {
      vi.useRealTimers();
    }
  });

  it('toolCallCancellation: aborts the pending fetch and sends no response', async () => {
    let capturedSignal: AbortSignal | null = null;
    const fetchMock = routedFetch((_url, opts) => {
      capturedSignal = opts.signal;
      return new Promise((_resolve, reject) => {
        opts.signal.addEventListener('abort', () =>
          reject(new DOMException('aborted', 'AbortError')),
        );
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    const { result } = renderHook(() => useGeminiLive());
    await act(async () => {
      await result.current.connect();
    });

    await act(async () => {
      g.connectArgs.value.callbacks.onmessage({
        toolCall: { functionCalls: [{ id: 'c1', name: 'board_control', args: {} }] },
      });
      await new Promise((r) => setTimeout(r, 0));
      g.connectArgs.value.callbacks.onmessage({
        toolCallCancellation: { ids: ['c1'] },
      });
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(capturedSignal).not.toBeNull();
    expect((capturedSignal as unknown as AbortSignal).aborted).toBe(true);
    expect(g.session.sendToolResponse).not.toHaveBeenCalled();
  });
});

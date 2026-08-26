import { useState, useRef, useCallback, useEffect } from 'react';
import { GoogleGenAI, Modality } from '@google/genai';
import type {
  LiveServerMessage,
  LiveServerToolCall,
  LiveServerToolCallCancellation,
  Session,
} from '@google/genai';

/**
 * useGeminiLive — browser-side Gemini Live voice client for the AI Chess Coach (Phase 2).
 *
 * Audio engine only: mints an ephemeral token via POST /api/coach/live-token, opens a Live
 * session through the SDK (ephemeral token passed as apiKey), streams 16 kHz PCM mic audio up
 * via an AudioWorklet, and plays back 24 kHz model audio gaplessly with barge-in support.
 * No UI — callers wire the returned state/handlers into their own components (Phase 3).
 */

export type LiveStatus = 'idle' | 'connecting' | 'listening' | 'speaking' | 'error';

export interface UseGeminiLiveOptions {
  getFen?: () => string;
  /** Current coach session id, so the minted token carries the shared conversation memory. */
  getSessionId?: () => string | null | undefined;
  onTranscript?: (t: { role: 'user' | 'model'; text: string; final: boolean }) => void;
  onError?: (msg: string) => void;
  onStatusChange?: (s: LiveStatus) => void;
  /** Fired after a voice tool call resolves, so the UI can apply board actions / game lists. */
  onToolResult?: (name: string, result: unknown) => void;
}

export interface UseGeminiLiveReturn {
  status: LiveStatus;
  isSupported: boolean;
  isActive: boolean;
  error: string | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  sendBoardUpdate: (fen: string) => void;
}

// Gemini Live audio formats (non-negotiable, per spec).
const OUTPUT_SAMPLE_RATE = 24000;
// RMS above which local mic activity counts as barge-in while the model is speaking.
const BARGE_IN_RMS = 0.05;

function getAudioContextCtor(): typeof AudioContext | null {
  if (typeof window === 'undefined') return null;
  return (window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext ||
    null) as typeof AudioContext | null;
}

function arrayBufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(
      null,
      Array.from(bytes.subarray(i, i + chunk)),
    );
  }
  return btoa(binary);
}

// Wrap a FEN in a board-update turn the live model reads as the new source of truth.
function boardUpdateText(fen: string): string {
  return `Board update — the CURRENT position is now (this supersedes any previous position): ${fen}`;
}

function base64ToInt16(b64: string): Int16Array {
  const binary = atob(b64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Int16Array(bytes.buffer, 0, Math.floor(len / 2));
}

export default function useGeminiLive(
  options: UseGeminiLiveOptions = {},
): UseGeminiLiveReturn {
  const [status, setStatusState] = useState<LiveStatus>('idle');
  const [isSupported, setIsSupported] = useState(false);
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep the latest options accessible from stable callbacks without re-binding them.
  const optionsRef = useRef<UseGeminiLiveOptions>(options);
  optionsRef.current = options;

  const statusRef = useRef<LiveStatus>('idle');
  const sessionRef = useRef<Session | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const captureCtxRef = useRef<AudioContext | null>(null);
  const playbackCtxRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const playSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const nextPlayTimeRef = useRef(0);
  // In-flight tool-call fetches, keyed by functionCall id, so a
  // toolCallCancellation can abort them.
  const toolAbortRef = useRef<Map<string, AbortController>>(new Map());

  const setStatus = useCallback((s: LiveStatus) => {
    statusRef.current = s;
    setStatusState(s);
    optionsRef.current.onStatusChange?.(s);
  }, []);

  // Detect capability once mounted (SSR-safe).
  useEffect(() => {
    const supported =
      typeof window !== 'undefined' &&
      getAudioContextCtor() !== null &&
      typeof AudioWorkletNode !== 'undefined' &&
      !!navigator?.mediaDevices?.getUserMedia;
    setIsSupported(supported);
  }, []);

  // Stop and clear all scheduled playback buffers.
  const stopSources = useCallback(() => {
    playSourcesRef.current.forEach((src) => {
      try {
        src.onended = null;
        src.stop();
      } catch {
        /* already stopped */
      }
    });
    playSourcesRef.current.clear();
    nextPlayTimeRef.current = 0;
  }, []);

  // Barge-in: flush playback and hand the floor back to the user.
  const flushPlayback = useCallback(() => {
    stopSources();
    if (statusRef.current === 'speaking') {
      setStatus('listening');
    }
  }, [stopSources, setStatus]);

  const cleanup = useCallback(() => {
    toolAbortRef.current.forEach((controller) => {
      try {
        controller.abort();
      } catch {
        /* noop */
      }
    });
    toolAbortRef.current.clear();
    const node = workletNodeRef.current;
    if (node) {
      try {
        node.port.onmessage = null;
      } catch {
        /* noop */
      }
      try {
        node.disconnect();
      } catch {
        /* noop */
      }
      workletNodeRef.current = null;
    }
    if (sourceNodeRef.current) {
      try {
        sourceNodeRef.current.disconnect();
      } catch {
        /* noop */
      }
      sourceNodeRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => {
        try {
          t.stop();
        } catch {
          /* noop */
        }
      });
      streamRef.current = null;
    }
    if (sessionRef.current) {
      try {
        sessionRef.current.close();
      } catch {
        /* noop */
      }
      sessionRef.current = null;
    }
    stopSources();
    if (captureCtxRef.current) {
      try {
        captureCtxRef.current.close();
      } catch {
        /* noop */
      }
      captureCtxRef.current = null;
    }
    if (playbackCtxRef.current) {
      try {
        playbackCtxRef.current.close();
      } catch {
        /* noop */
      }
      playbackCtxRef.current = null;
    }
  }, [stopSources]);

  // Decode a base64 24 kHz PCM chunk and schedule it gaplessly.
  const enqueuePlayback = useCallback(
    (b64: string) => {
      const AudioCtor = getAudioContextCtor();
      if (!AudioCtor) return;
      if (!playbackCtxRef.current) {
        playbackCtxRef.current = new AudioCtor({ sampleRate: OUTPUT_SAMPLE_RATE });
      }
      const ctx = playbackCtxRef.current;

      const int16 = base64ToInt16(b64);
      if (int16.length === 0) return;
      const float = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) {
        float[i] = int16[i] / 0x8000;
      }

      const buffer = ctx.createBuffer(1, float.length, OUTPUT_SAMPLE_RATE);
      buffer.getChannelData(0).set(float);

      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.connect(ctx.destination);

      const startAt = Math.max(ctx.currentTime, nextPlayTimeRef.current);
      src.start(startAt);
      nextPlayTimeRef.current = startAt + buffer.duration;

      playSourcesRef.current.add(src);
      setStatus('speaking');

      src.onended = () => {
        playSourcesRef.current.delete(src);
        if (playSourcesRef.current.size === 0 && statusRef.current === 'speaking') {
          setStatus('listening');
        }
      };
    },
    [setStatus],
  );

  // Cancel in-flight tool fetches the model no longer wants a response for.
  const handleToolCancellation = useCallback(
    (cancellation: LiveServerToolCallCancellation) => {
      for (const id of cancellation.ids ?? []) {
        const controller = toolAbortRef.current.get(id);
        if (controller) {
          try {
            controller.abort();
          } catch {
            /* noop */
          }
          toolAbortRef.current.delete(id);
        }
      }
    },
    [],
  );

  // Run each functionCall through the /api/coach/tool proxy and reply with a
  // functionResponse for every call — even on failure — so the session never
  // stalls waiting on a tool.
  const handleToolCall = useCallback(async (toolCall: LiveServerToolCall) => {
    const calls = toolCall.functionCalls ?? [];
    const session = sessionRef.current;
    if (calls.length === 0 || !session) return;

    const sessionId = optionsRef.current.getSessionId?.() ?? undefined;

    const responses = await Promise.all(
      calls.map(async (fc) => {
        const controller = new AbortController();
        if (fc.id) toolAbortRef.current.set(fc.id, controller);
        try {
          const res = await fetch('/api/coach/tool', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
              name: fc.name,
              args: fc.args ?? {},
              session_id: sessionId,
            }),
            signal: controller.signal,
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) {
            return {
              id: fc.id,
              name: fc.name,
              response: {
                error:
                  (data && (data as { error?: string }).error) ||
                  `Tool proxy error ${res.status}`,
              },
            };
          }
          try {
            optionsRef.current.onToolResult?.(fc.name ?? '', data);
          } catch {
            /* UI callback errors must not break the session */
          }
          return {
            id: fc.id,
            name: fc.name,
            response: { result: (data as { result?: unknown }).result ?? data },
          };
        } catch (err) {
          // Aborted (cancelled by the model) — drop it, no response expected.
          if (err instanceof DOMException && err.name === 'AbortError') {
            return null;
          }
          const message = err instanceof Error ? err.message : 'tool call failed';
          return { id: fc.id, name: fc.name, response: { error: message } };
        } finally {
          if (fc.id) toolAbortRef.current.delete(fc.id);
        }
      }),
    );

    const functionResponses = responses.filter(
      (r): r is NonNullable<typeof r> => r !== null,
    );
    if (functionResponses.length === 0) return;
    try {
      session.sendToolResponse({ functionResponses });
    } catch {
      /* session may be closing */
    }
  }, []);

  const handleMessage = useCallback(
    (msg: LiveServerMessage) => {
      if (msg.toolCall) {
        void handleToolCall(msg.toolCall);
      }
      if (msg.toolCallCancellation) {
        handleToolCancellation(msg.toolCallCancellation);
      }

      const sc = msg.serverContent;
      if (!sc) return;

      if (sc.inputTranscription?.text) {
        optionsRef.current.onTranscript?.({
          role: 'user',
          text: sc.inputTranscription.text,
          final: !!sc.inputTranscription.finished,
        });
      }
      if (sc.outputTranscription?.text) {
        optionsRef.current.onTranscript?.({
          role: 'model',
          text: sc.outputTranscription.text,
          final: !!sc.outputTranscription.finished,
        });
      }

      if (sc.interrupted) {
        flushPlayback();
      }

      const parts = sc.modelTurn?.parts;
      if (parts) {
        for (const part of parts) {
          const inline = part.inlineData;
          if (inline?.data && inline.mimeType?.includes('audio/pcm')) {
            enqueuePlayback(inline.data);
          }
        }
      }
    },
    [flushPlayback, enqueuePlayback, handleToolCall, handleToolCancellation],
  );

  const fail = useCallback(
    (msg: string) => {
      cleanup();
      setIsActive(false);
      setError(msg);
      optionsRef.current.onError?.(msg);
      setStatus('error');
    },
    [cleanup, setStatus],
  );

  const startCapture = useCallback(
    async (session: Session) => {
      const AudioCtor = getAudioContextCtor();
      if (!AudioCtor) throw new Error('AudioContext is not available');

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const ctx = new AudioCtor();
      captureCtxRef.current = ctx;
      await ctx.audioWorklet.addModule('/worklets/pcm-capture-processor.js');

      const source = ctx.createMediaStreamSource(stream);
      const node = new AudioWorkletNode(ctx, 'pcm-capture-processor');
      sourceNodeRef.current = source;
      workletNodeRef.current = node;

      node.port.onmessage = (ev: MessageEvent) => {
        const data = ev.data as { pcm: ArrayBuffer; rms: number };
        if (!data?.pcm) return;

        // Local barge-in: user speaks over the coach.
        if (data.rms > BARGE_IN_RMS && statusRef.current === 'speaking') {
          flushPlayback();
        }

        try {
          session.sendRealtimeInput({
            audio: {
              data: arrayBufferToBase64(data.pcm),
              mimeType: 'audio/pcm;rate=16000',
            },
          });
        } catch {
          /* session may be closing */
        }
      };

      source.connect(node);
      node.connect(ctx.destination);
    },
    [flushPlayback],
  );

  const connect = useCallback(async () => {
    if (sessionRef.current) return;
    setError(null);
    setStatus('connecting');

    try {
      const fen = optionsRef.current.getFen?.();
      const sessionId = optionsRef.current.getSessionId?.();
      const res = await fetch('/api/coach/live-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ fen, session_id: sessionId ?? undefined }),
      });
      if (!res.ok) {
        throw new Error(`Live coach unavailable (${res.status})`);
      }
      const { token, model } = (await res.json()) as {
        token?: string;
        model?: string;
      };
      if (!token || !model) {
        throw new Error('Invalid live-token response');
      }

      const ai = new GoogleGenAI({
        apiKey: token,
        httpOptions: { apiVersion: 'v1alpha' },
      });

      const session = await ai.live.connect({
        model,
        callbacks: {
          onmessage: handleMessage,
          onerror: (e: ErrorEvent) => {
            fail(e?.message || 'Live connection error');
          },
          onclose: () => {
            if (statusRef.current !== 'error') {
              cleanup();
              setIsActive(false);
              setStatus('idle');
            }
          },
        },
        config: {
          responseModalities: [Modality.AUDIO],
          inputAudioTranscription: {},
          outputAudioTranscription: {},
        },
      });
      sessionRef.current = session;

      // Anchor the initial position client-side so the coach is never blind to it,
      // regardless of whether the token's system instruction carried the FEN.
      if (fen) {
        try {
          session.sendClientContent({
            turns: [{ role: 'user', parts: [{ text: boardUpdateText(fen) }] }],
            turnComplete: false,
          });
        } catch {
          /* session may be closing */
        }
      }

      await startCapture(session);

      setIsActive(true);
      setStatus('listening');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start live coach';
      fail(msg);
    }
  }, [setStatus, handleMessage, startCapture, cleanup, fail]);

  const disconnect = useCallback(() => {
    cleanup();
    setIsActive(false);
    setStatus('idle');
  }, [cleanup, setStatus]);

  // Push the current board position into the open session mid-conversation.
  // turnComplete:false injects context without interrupting the audio turn.
  const sendBoardUpdate = useCallback((fen: string) => {
    const session = sessionRef.current;
    if (!session || !fen) return;
    try {
      session.sendClientContent({
        turns: [{ role: 'user', parts: [{ text: boardUpdateText(fen) }] }],
        turnComplete: false,
      });
    } catch {
      /* session may be closing */
    }
  }, []);

  // Ensure resources are released on unmount.
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return {
    status,
    isSupported,
    isActive,
    error,
    connect,
    disconnect,
    sendBoardUpdate,
  };
}

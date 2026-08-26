/**
 * @vitest-environment jsdom
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, act, fireEvent } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';

import en from '../../../../messages/en.json';
import type { UseGeminiLiveReturn, LiveStatus } from '@/hooks/useGeminiLive';

// ── Mock the Gemini Live hook: capture the options it was called with, and
//    return a state object each test can configure. ───────────────────────────
const live = vi.hoisted(() => ({
  options: null as null | {
    getFen?: () => string;
    onTranscript?: (t: { role: 'user' | 'model'; text: string; final: boolean }) => void;
  },
  ret: null as unknown as UseGeminiLiveReturn,
}));

vi.mock('@/hooks/useGeminiLive', () => ({
  __esModule: true,
  default: (options: typeof live.options) => {
    live.options = options;
    return live.ret;
  },
}));

import CoachChat from '../CoachChat';

function makeReturn(overrides: Partial<UseGeminiLiveReturn> = {}): UseGeminiLiveReturn {
  return {
    status: 'idle' as LiveStatus,
    isSupported: true,
    isActive: false,
    error: null,
    connect: vi.fn(async () => {}),
    disconnect: vi.fn(),
    sendBoardUpdate: vi.fn(),
    ...overrides,
  };
}

function renderChat(currentFen = 'startpos-fen') {
  return render(
    <NextIntlClientProvider locale="en" messages={en as Record<string, unknown>}>
      <CoachChat
        currentFen={currentFen}
        sessionId={null}
        onBoardActions={() => {}}
      />
    </NextIntlClientProvider>
  );
}

const coach = en.coach;

beforeEach(() => {
  live.options = null;
  live.ret = makeReturn();
  // jsdom does not implement scrollIntoView (called on message updates).
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(cleanup);

describe('CoachChat voice mode', () => {
  it('renders the mic button when voice is supported', () => {
    live.ret = makeReturn({ isSupported: true });
    renderChat();
    expect(screen.getByTestId('voice-toggle')).toBeTruthy();
  });

  it('hides the mic button when voice is not supported', () => {
    live.ret = makeReturn({ isSupported: false });
    renderChat();
    expect(screen.queryByTestId('voice-toggle')).toBeNull();
  });

  it('calls connect() when clicking the mic while idle', () => {
    const connect = vi.fn(async () => {});
    live.ret = makeReturn({ status: 'idle', isActive: false, connect });
    renderChat();
    fireEvent.click(screen.getByTestId('voice-toggle'));
    expect(connect).toHaveBeenCalledTimes(1);
  });

  it('calls disconnect() when clicking the mic while active', () => {
    const disconnect = vi.fn();
    live.ret = makeReturn({ status: 'listening', isActive: true, disconnect });
    renderChat();
    fireEvent.click(screen.getByTestId('voice-toggle'));
    expect(disconnect).toHaveBeenCalledTimes(1);
  });

  it('shows the listening pill when status is listening', () => {
    live.ret = makeReturn({ status: 'listening', isActive: true });
    renderChat();
    expect(screen.getByTestId('voice-pill').textContent).toBe(coach.voiceListening);
  });

  it('shows the speaking pill when status is speaking', () => {
    live.ret = makeReturn({ status: 'speaking', isActive: true });
    renderChat();
    expect(screen.getByTestId('voice-pill').textContent).toBe(coach.voiceSpeaking);
  });

  it('renders a user bubble from a final transcript', () => {
    renderChat();
    act(() => {
      live.options?.onTranscript?.({ role: 'user', text: 'hello coach', final: true });
    });
    expect(screen.getByText('hello coach')).toBeTruthy();
  });

  it('updates the same bubble across streaming chunks instead of creating two', () => {
    renderChat();
    act(() => {
      live.options?.onTranscript?.({ role: 'model', text: 'Let me ', final: false });
    });
    act(() => {
      live.options?.onTranscript?.({ role: 'model', text: 'think.', final: true });
    });
    // Both chunks land in one bubble: no separate 'Let me ' node survives.
    expect(screen.queryByText('Let me ')).toBeNull();
    expect(screen.getByText('Let me think.')).toBeTruthy();
  });

  it('surfaces the error message as the mic tooltip in the error state', () => {
    live.ret = makeReturn({ status: 'error', error: 'Mic blocked' });
    renderChat();
    const btn = screen.getByTestId('voice-toggle');
    expect(btn.getAttribute('title')).toBe('Mic blocked');
    expect(btn.getAttribute('data-status')).toBe('error');
  });

  it('passes the live FEN through getFen', () => {
    renderChat();
    expect(live.options?.getFen?.()).toBe('startpos-fen');
  });
});

describe('CoachChat board sync', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('pushes a debounced board update when the FEN changes while voice is active', () => {
    const sendBoardUpdate = vi.fn();
    live.ret = makeReturn({ status: 'listening', isActive: true, sendBoardUpdate });

    const { rerender } = renderChat('fen-1');
    // Initial FEN must not be re-sent — the session anchors it on open.
    act(() => vi.advanceTimersByTime(300));
    expect(sendBoardUpdate).not.toHaveBeenCalled();

    rerender(
      <NextIntlClientProvider locale="en" messages={en as Record<string, unknown>}>
        <CoachChat currentFen="fen-2" sessionId={null} onBoardActions={() => {}} />
      </NextIntlClientProvider>
    );

    // Debounced: nothing yet before the timer fires.
    expect(sendBoardUpdate).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(300));
    expect(sendBoardUpdate).toHaveBeenCalledTimes(1);
    expect(sendBoardUpdate).toHaveBeenCalledWith('fen-2');
  });

  it('does not push board updates when voice is inactive', () => {
    const sendBoardUpdate = vi.fn();
    live.ret = makeReturn({ status: 'idle', isActive: false, sendBoardUpdate });

    const { rerender } = renderChat('fen-1');
    rerender(
      <NextIntlClientProvider locale="en" messages={en as Record<string, unknown>}>
        <CoachChat currentFen="fen-2" sessionId={null} onBoardActions={() => {}} />
      </NextIntlClientProvider>
    );
    act(() => vi.advanceTimersByTime(300));
    expect(sendBoardUpdate).not.toHaveBeenCalled();
  });
});

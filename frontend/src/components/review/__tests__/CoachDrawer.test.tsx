/**
 * @vitest-environment jsdom
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, cleanup, fireEvent } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';

import CoachDrawer from '../CoachDrawer';
import type { ReviewMove } from '../types';
import { renderIntl } from './intl';
import en from '../../../../messages/en.json';

/** Wrap in the intl provider so RTL's `rerender` keeps the context. */
function intl(ui: React.ReactElement) {
  return (
    <NextIntlClientProvider locale="en" messages={en as Record<string, unknown>}>
      {ui}
    </NextIntlClientProvider>
  );
}

/** Collapse any whitespace (ICU may emit NBSP) for stable text assertions. */
const norm = (s: string | null | undefined) => (s ?? '').replace(/\s+/g, ' ');

// Mock the reused chat surface: expose the imperative `send` so we can assert
// starter chips fire, and echo the grounding props back as data attributes.
const h = vi.hoisted(() => ({ sends: [] as string[] }));
vi.mock('@/components/coach/CoachChat', async () => {
  const React = await import('react');
  return {
    __esModule: true,
    default: React.forwardRef(function MockCoachChat(
      props: { currentFen: string; contextNote?: string },
      ref: React.Ref<{ send: (t: string) => void }>,
    ) {
      React.useImperativeHandle(ref, () => ({ send: (t: string) => h.sends.push(t) }), []);
      return React.createElement('div', {
        'data-testid': 'mock-coach-chat',
        'data-fen': props.currentFen,
        'data-note': props.contextNote ?? '',
      });
    }),
  };
});

function move(partial: Partial<ReviewMove> & { ply: number }): ReviewMove {
  return {
    san: 'Nxe5',
    uci: 'c6e5',
    fen: 'fen-under-review',
    eval: { type: 'cp', value: -250 },
    best: { uci: 'd7d5', eval: { type: 'cp', value: 20 } },
    winPercent: 30,
    accuracy: null,
    classification: 'blunder',
    phase: 'middlegame',
    ...partial,
  };
}

function setWidth(px: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: px });
}

beforeEach(() => {
  h.sends.length = 0;
  setWidth(1200);
});

afterEach(cleanup);

describe('CoachDrawer open/close', () => {
  it('is closed and does not mount the chat until first opened', () => {
    renderIntl(<CoachDrawer open={false} onClose={() => {}} gameId="g1" move={move({ ply: 28 })} />);
    expect(screen.getByTestId('coach-drawer').getAttribute('data-open')).toBe('false');
    expect(screen.queryByTestId('mock-coach-chat')).toBeNull();
  });

  it('mounts the chat and marks itself open when open', () => {
    renderIntl(<CoachDrawer open onClose={() => {}} gameId="g1" move={move({ ply: 28 })} />);
    expect(screen.getByTestId('coach-drawer').getAttribute('data-open')).toBe('true');
    expect(screen.getByTestId('mock-coach-chat')).toBeTruthy();
  });

  it('fires onClose from the close button', () => {
    const onClose = vi.fn();
    renderIntl(<CoachDrawer open onClose={onClose} gameId="g1" move={move({ ply: 28 })} />);
    fireEvent.click(screen.getByTestId('coach-drawer-close'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe('CoachDrawer move-context chip', () => {
  it('renders the current ply as "Re: {move} — {classification}"', () => {
    // ply 28 → Black's 14th move → "14…".
    renderIntl(<CoachDrawer open onClose={() => {}} gameId="g1" move={move({ ply: 28 })} />);
    const chip = screen.getByTestId('coach-drawer-context-chip');
    expect(norm(chip.textContent)).toBe('Re: 14… Nxe5 — Blunder');
  });

  it('updates the chip when the ply changes', () => {
    const { rerender } = renderIntl(
      <CoachDrawer open onClose={() => {}} gameId="g1" move={move({ ply: 28 })} />,
    );
    rerender(
      intl(
        <CoachDrawer
          open
          onClose={() => {}}
          gameId="g1"
          move={move({ ply: 7, san: 'Bb5', classification: 'best' })}
        />,
      ),
    );
    // ply 7 → White's 4th move → "4.".
    expect(norm(screen.getByTestId('coach-drawer-context-chip').textContent)).toBe('Re: 4. Bb5 — Best');
  });

  it('omits the chip when there is no move (start position)', () => {
    renderIntl(<CoachDrawer open onClose={() => {}} gameId="g1" move={null} />);
    expect(screen.queryByTestId('coach-drawer-context-chip')).toBeNull();
  });
});

describe('CoachDrawer starter chips', () => {
  it('sends the tapped prompt through the chat handle', () => {
    renderIntl(<CoachDrawer open onClose={() => {}} gameId="g1" move={move({ ply: 28 })} />);
    const chips = screen.getAllByTestId('coach-drawer-starter');
    expect(chips.map((c) => c.textContent)).toEqual([
      'Why is this a blunder?',
      'What should I have played?',
      'Explain the plan.',
    ]);
    fireEvent.click(chips[0]);
    expect(h.sends).toEqual(['Why is this a blunder?']);
  });

  it('passes a grounding note scoped to the move under review', () => {
    renderIntl(<CoachDrawer open onClose={() => {}} gameId="g1" move={move({ ply: 28 })} />);
    const note = screen.getByTestId('mock-coach-chat').getAttribute('data-note') || '';
    expect(note).toContain('Nxe5');
    expect(note).toContain('blunder');
    expect(note).toContain('English');
    // Grounds on the position FEN Review already computed.
    expect(screen.getByTestId('mock-coach-chat').getAttribute('data-fen')).toBe('fen-under-review');
  });
});

describe('CoachDrawer responsive mode', () => {
  it('is a desktop slide-over on wide viewports', () => {
    setWidth(1200);
    renderIntl(<CoachDrawer open onClose={() => {}} gameId="g1" move={move({ ply: 28 })} />);
    expect(screen.getByTestId('coach-drawer').getAttribute('data-mode')).toBe('desktop');
    // No backdrop on desktop — the board/evals stay interactive.
    expect(screen.queryByTestId('coach-drawer-backdrop')).toBeNull();
  });

  it('is a bottom sheet with a drag handle on narrow viewports', () => {
    setWidth(375);
    renderIntl(<CoachDrawer open onClose={() => {}} gameId="g1" move={move({ ply: 28 })} />);
    expect(screen.getByTestId('coach-drawer').getAttribute('data-mode')).toBe('mobile');
    expect(screen.getByTestId('coach-drawer-handle')).toBeTruthy();
    expect(screen.getByTestId('coach-drawer-backdrop')).toBeTruthy();
  });
});

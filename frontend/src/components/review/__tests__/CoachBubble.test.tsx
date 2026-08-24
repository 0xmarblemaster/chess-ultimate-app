/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, afterEach } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import CoachBubble, { coachText, evalDeltaPawns, formatDelta } from '../CoachBubble';
import type { ReviewMove } from '../types';

afterEach(cleanup);

function move(partial: Partial<ReviewMove> & { ply: number }): ReviewMove {
  return {
    san: 'Nf3',
    uci: 'g1f3',
    fen: 'x',
    eval: { type: 'cp', value: 0 },
    best: null,
    winPercent: 50,
    accuracy: null,
    classification: 'best',
    phase: 'middlegame',
    ...partial,
  };
}

describe('evalDeltaPawns (mover POV)', () => {
  it('is negative when a white move loses eval', () => {
    const prev = move({ ply: 2, eval: { type: 'cp', value: 30 } });
    const m = move({ ply: 3, classification: 'blunder', eval: { type: 'cp', value: -250 } });
    expect(evalDeltaPawns(m, prev)).toBeCloseTo(-2.8);
  });

  it('is negative for a black blunder even though white-POV eval rose', () => {
    const prev = move({ ply: 3, eval: { type: 'cp', value: 30 } });
    const m = move({ ply: 4, classification: 'blunder', eval: { type: 'cp', value: 350 } });
    expect(evalDeltaPawns(m, prev)).toBeCloseTo(-3.2);
  });

  it('is positive for a strong white move', () => {
    const m = move({ ply: 1, classification: 'best', eval: { type: 'cp', value: 40 } });
    expect(evalDeltaPawns(m, null)).toBeCloseTo(0.4);
  });
});

describe('formatDelta', () => {
  it('always signs the value and collapses tiny deltas to 0.0', () => {
    expect(formatDelta(2.8)).toBe('+2.8');
    expect(formatDelta(-3.2)).toBe('−3.2');
    expect(formatDelta(0.02)).toBe('0.0');
  });
});

describe('coachText templates', () => {
  it('names the last book move with the opening', () => {
    const m = move({ ply: 2, san: 'e6', classification: 'book' });
    expect(coachText(m, null, { name: 'French Defense', lastBookPly: 2 })).toContain(
      'last book move',
    );
    expect(coachText(m, null, { name: 'French Defense', lastBookPly: 2 })).toContain(
      'French Defense',
    );
  });

  it('calls out a brilliant sacrifice', () => {
    const m = move({ ply: 6, san: 'Bxh7+', classification: 'brilliant' });
    expect(coachText(m, null)).toMatch(/[Bb]rilliant/);
  });

  it('flags a blunder', () => {
    const prev = move({ ply: 2, eval: { type: 'cp', value: 30 } });
    const m = move({ ply: 3, san: 'Qd2', classification: 'blunder', eval: { type: 'cp', value: -250 } });
    expect(coachText(m, prev)).toContain('blunder');
  });
});

describe('CoachBubble render', () => {
  it('shows the SAN, classification and a signed delta chip', () => {
    const prev = move({ ply: 2, eval: { type: 'cp', value: 30 } });
    const m = move({ ply: 3, san: 'Qd2', classification: 'blunder', eval: { type: 'cp', value: -250 } });
    const { getByTestId } = render(<CoachBubble move={m} prev={prev} />);
    expect(getByTestId('coach-san').textContent).toBe('Qd2');
    expect(getByTestId('coach-delta').textContent).toBe('−2.8');
    expect(getByTestId('coach-bubble').getAttribute('data-classification')).toBe('blunder');
  });

  it('renders a placeholder at the start position', () => {
    const { getByTestId } = render(<CoachBubble move={null} prev={null} />);
    expect(getByTestId('coach-bubble').textContent).toMatch(/step through/i);
  });
});

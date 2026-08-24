/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, afterEach, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import ReviewSounds, { soundKeyForMove } from '../ReviewSounds';
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

describe('soundKeyForMove', () => {
  it('gives brilliant and blunder their signature cues', () => {
    expect(soundKeyForMove(move({ ply: 1, classification: 'brilliant' }))).toBe('brilliant');
    expect(soundKeyForMove(move({ ply: 1, classification: 'blunder' }))).toBe('blunder');
  });

  it('falls back to capture for capture SANs', () => {
    expect(soundKeyForMove(move({ ply: 1, san: 'Bxh7+', classification: 'best' }))).toBe('capture');
  });

  it('falls back to a plain move click otherwise', () => {
    expect(soundKeyForMove(move({ ply: 1, san: 'Nf3', classification: 'good' }))).toBe('move');
    expect(soundKeyForMove(null)).toBe('move');
  });
});

describe('ReviewSounds playback', () => {
  it('does not autoplay on mount and stays silent while muted', () => {
    const play = vi
      .spyOn(window.HTMLMediaElement.prototype, 'play')
      .mockImplementation(() => Promise.resolve());

    const { rerender } = render(
      <ReviewSounds currentPly={0} move={null} muted={false} />,
    );
    expect(play).not.toHaveBeenCalled(); // no autoplay on mount

    // Step onto a real ply → one sound.
    rerender(
      <ReviewSounds currentPly={1} move={move({ ply: 1, san: 'Bxh7', classification: 'best' })} muted={false} />,
    );
    expect(play).toHaveBeenCalledTimes(1);

    // Stepping while muted → no further sound.
    play.mockClear();
    rerender(
      <ReviewSounds currentPly={2} move={move({ ply: 2, classification: 'brilliant' })} muted={true} />,
    );
    expect(play).not.toHaveBeenCalled();

    play.mockRestore();
  });
});

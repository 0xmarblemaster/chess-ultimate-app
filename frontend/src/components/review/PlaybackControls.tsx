'use client';

import { useEffect, useRef, useState } from 'react';

/**
 * The next key-moment ply strictly after `currentPly`, or null if none remain.
 * Key moments arrive sorted from the backend; we defensively sort a copy.
 */
export function nextKeyMoment(keyMoments: number[], currentPly: number): number | null {
  const sorted = [...keyMoments].sort((a, b) => a - b);
  for (const ply of sorted) {
    if (ply > currentPly) return ply;
  }
  return null;
}

export interface PlaybackControlsProps {
  currentPly: number;
  maxPly: number;
  keyMoments: number[];
  /** Absolute jump (used by first/last and the key-moment Next). */
  onJump: (ply: number) => void;
  /** Relative step, clamped by the store (used by prev/next). */
  onStep: (delta: number) => void;
}

const btn: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 40,
  height: 40,
  borderRadius: 10,
  border: '1px solid var(--review-card-border)',
  background: 'var(--review-card)',
  color: 'var(--review-text)',
  cursor: 'pointer',
  fontSize: 15,
};

/**
 * first / prev / play-through / next / last + a "Next key moment" jump.
 * Play-through auto-advances ~1 move/sec and stops at the final ply. Keyboard
 * ←/→ is wired at the page level and keeps working alongside these.
 */
export default function PlaybackControls({
  currentPly,
  maxPly,
  keyMoments,
  onJump,
  onStep,
}: PlaybackControlsProps) {
  const [playing, setPlaying] = useState(false);
  const atStart = currentPly <= 0;
  const atEnd = currentPly >= maxPly;
  const upcomingKeyMoment = nextKeyMoment(keyMoments, currentPly);
  // At the end there is nothing to advance to, so playback naturally idles.
  const showPlaying = playing && !atEnd;

  // Auto-advance timer. The step callback is read through a ref so a fresh
  // identity each render doesn't reset the running timer.
  const stepRef = useRef(onStep);
  useEffect(() => {
    stepRef.current = onStep;
  });
  useEffect(() => {
    if (!playing || currentPly >= maxPly) return;
    const t = setTimeout(() => stepRef.current(1), 1000);
    return () => clearTimeout(t);
  }, [playing, currentPly, maxPly]);

  return (
    <div
      data-testid="playback-controls"
      style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'center' }}
    >
      <button type="button" aria-label="First move" data-testid="pb-first" style={btn}
        disabled={atStart} onClick={() => onJump(0)}>⏮</button>
      <button type="button" aria-label="Previous move" data-testid="pb-prev" style={btn}
        disabled={atStart} onClick={() => onStep(-1)}>‹</button>
      <button type="button" aria-label={showPlaying ? 'Pause' : 'Play through'} data-testid="pb-play" style={btn}
        onClick={() => setPlaying((p) => !p)} disabled={atEnd && !playing}>{showPlaying ? '⏸' : '▶'}</button>
      <button type="button" aria-label="Next move" data-testid="pb-next" style={btn}
        disabled={atEnd} onClick={() => onStep(1)}>›</button>
      <button type="button" aria-label="Last move" data-testid="pb-last" style={btn}
        disabled={atEnd} onClick={() => onJump(maxPly)}>⏭</button>
      <button
        type="button"
        aria-label="Next key moment"
        data-testid="pb-keymoment"
        style={{ ...btn, width: 'auto', padding: '0 12px', gap: 6, fontSize: 13, fontWeight: 700 }}
        disabled={upcomingKeyMoment == null}
        onClick={() => upcomingKeyMoment != null && onJump(upcomingKeyMoment)}
      >
        Next ⚡
      </button>
    </div>
  );
}

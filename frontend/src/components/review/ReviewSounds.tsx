'use client';

import { useEffect, useRef } from 'react';
import type { ReviewMove } from './types';

export type SoundKey = 'brilliant' | 'blunder' | 'capture' | 'move';

const SOUND_SRC: Record<SoundKey, string> = {
  brilliant: '/sounds/review/brilliant.wav',
  blunder: '/sounds/review/blunder.wav',
  capture: '/sounds/review/capture.wav',
  move: '/sounds/review/move.wav',
};

/**
 * Pick the sound for a move. Brilliant and blunder get their signature cues;
 * everything else falls back to capture (SAN contains ×) or the plain move click.
 */
export function soundKeyForMove(move: ReviewMove | null): SoundKey {
  if (!move) return 'move';
  if (move.classification === 'brilliant') return 'brilliant';
  if (move.classification === 'blunder') return 'blunder';
  if (move.san.includes('x')) return 'capture';
  return 'move';
}

export interface ReviewSoundsProps {
  /** 1-based ply currently landed on (0 = start). */
  currentPly: number;
  /** The move at currentPly (null at ply 0). */
  move: ReviewMove | null;
  muted: boolean;
}

/**
 * Plays a per-classification sound whenever the user steps onto a new ply.
 * Never autoplays on mount (the initial ply is remembered, not sounded) and
 * stays silent while muted. Renders nothing.
 */
export default function ReviewSounds({ currentPly, move, muted }: ReviewSoundsProps) {
  const audioRef = useRef<Partial<Record<SoundKey, HTMLAudioElement>>>({});
  const prevPlyRef = useRef<number>(currentPly);

  // Preload the four clips once, client-side only.
  useEffect(() => {
    if (typeof Audio === 'undefined') return;
    const map: Partial<Record<SoundKey, HTMLAudioElement>> = {};
    (Object.keys(SOUND_SRC) as SoundKey[]).forEach((key) => {
      const el = new Audio(SOUND_SRC[key]);
      el.preload = 'auto';
      el.volume = 0.6;
      map[key] = el;
    });
    audioRef.current = map;
  }, []);

  useEffect(() => {
    const prev = prevPlyRef.current;
    prevPlyRef.current = currentPly;
    // Only on a real, user-driven ply change — and only when a move landed.
    if (currentPly === prev || currentPly === 0 || muted) return;
    const el = audioRef.current[soundKeyForMove(move)];
    if (!el) return;
    try {
      el.currentTime = 0;
      void el.play();
    } catch {
      /* Autoplay/interaction guards — safe to ignore. */
    }
  }, [currentPly, move, muted]);

  return null;
}

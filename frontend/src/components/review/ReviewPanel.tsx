'use client';

import { useState } from 'react';
import type { ReviewResult } from './types';
import CoachBubble from './CoachBubble';
import MoveList from './MoveList';
import ReviewSounds from './ReviewSounds';

const MUTE_KEY = 'review-sound-muted';

export interface ReviewPanelProps {
  data: ReviewResult;
  /** 1-based current ply (0 = start position). */
  currentPly: number;
  onSetPly: (ply: number) => void;
  /** Return to the Highlights summary. */
  onExitReview: () => void;
}

/**
 * Review-mode sidebar: Highlights/Share/Mute row → coach bubble → annotated
 * move list, plus the sound player. The playback replay bar now lives under
 * the board (page.tsx), not here. One layout, both themes via the review CSS
 * vars.
 */
export default function ReviewPanel({
  data,
  currentPly,
  onSetPly,
  onExitReview,
}: ReviewPanelProps) {
  const currentMove = currentPly >= 1 ? data.moves[currentPly - 1] : null;
  const prevMove = currentPly >= 2 ? data.moves[currentPly - 2] : null;

  // Read the persisted mute preference lazily; the server has no localStorage
  // so it defaults to unmuted (the button below suppresses the hydration diff).
  const [muted, setMuted] = useState(
    () => typeof window !== 'undefined' && localStorage.getItem(MUTE_KEY) === '1',
  );
  const [shared, setShared] = useState(false);

  const toggleMute = () => {
    setMuted((m) => {
      const next = !m;
      try {
        localStorage.setItem(MUTE_KEY, next ? '1' : '0');
      } catch {
        /* private mode — ignore */
      }
      return next;
    });
  };

  const onShare = async () => {
    try {
      await navigator.clipboard?.writeText(window.location.href);
      setShared(true);
      setTimeout(() => setShared(false), 1500);
    } catch {
      /* clipboard blocked — Share image is Phase 5 anyway */
    }
  };

  return (
    <aside
      data-testid="review-sidebar"
      data-mode="review"
      style={{ width: 430, maxWidth: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button
          type="button"
          data-testid="exit-review"
          onClick={onExitReview}
          className="review-ghost-btn"
          style={{ padding: '6px 12px', fontSize: 13 }}
        >
          ‹ Highlights
        </button>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            type="button"
            data-testid="share-btn"
            onClick={onShare}
            className="review-ghost-btn"
            style={{ padding: '6px 12px', fontSize: 13 }}
          >
            {shared ? 'Copied!' : 'Share'}
          </button>
          <button
            type="button"
            data-testid="mute-toggle"
            aria-pressed={muted}
            aria-label={muted ? 'Unmute sounds' : 'Mute sounds'}
            onClick={toggleMute}
            className="review-ghost-btn"
            style={{ padding: '6px 12px', fontSize: 13 }}
            suppressHydrationWarning
          >
            {muted ? '🔇' : '🔊'}
          </button>
        </div>
      </div>

      <CoachBubble
        move={currentMove}
        prev={prevMove}
        opening={{ name: data.opening?.name, lastBookPly: data.opening?.lastBookPly }}
      />

      <MoveList moves={data.moves} currentPly={currentPly} onSelect={onSetPly} />

      <ReviewSounds currentPly={currentPly} move={currentMove} muted={muted} />
    </aside>
  );
}

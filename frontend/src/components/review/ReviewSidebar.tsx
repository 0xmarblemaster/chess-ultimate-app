'use client';

import type { ReviewResult } from './types';
import CoachIntro from './CoachIntro';
import AccuracyCard from './AccuracyCard';
import PlayersAccuracyRow from './PlayersAccuracyRow';
import TallyTable from './TallyTable';
import GameRating from './GameRating';
import PhaseStats from './PhaseStats';

export interface SidebarPlayer {
  name: string;
  rating?: number;
}

export interface ReviewSidebarProps {
  data: ReviewResult;
  mode: 'highlights' | 'review';
  white: SidebarPlayer;
  black: SidebarPlayer;
  onStartReview: () => void;
}

/** Build a short, deterministic coach greeting from the aggregates. */
function coachCopy(data: ReviewResult): { headline: string; message: string } {
  const brilliancies = data.tally.w.brilliant + data.tally.b.brilliant;
  const blunders = data.tally.w.blunder + data.tally.b.blunder;
  const best = Math.max(data.accuracy.w, data.accuracy.b).toFixed(1);
  if (brilliancies > 0) {
    return {
      headline: 'A brilliant game!',
      message: `You found ${brilliancies} brilliant move${brilliancies > 1 ? 's' : ''}. Step through the review to relive the key moments.`,
    };
  }
  if (blunders === 0) {
    return {
      headline: 'Clean and solid.',
      message: `No blunders this game — top accuracy ${best}%. Let's look at where you could push even harder.`,
    };
  }
  return {
    headline: "Let's review this one.",
    message: `A few turning points to learn from. Top accuracy was ${best}% — start the review to see every key moment.`,
  };
}

/**
 * Highlights-mode sidebar. The Start Review CTA flips the store to "review"
 * mode; the move-by-move stepper itself lands in Phase 4 (placeholder here).
 */
export default function ReviewSidebar({
  data,
  mode,
  white,
  black,
  onStartReview,
}: ReviewSidebarProps) {
  if (mode === 'review') {
    return (
      <aside
        data-testid="review-sidebar"
        data-mode="review"
        style={{ width: 430, maxWidth: '100%', display: 'flex', flexDirection: 'column', gap: 14 }}
      >
        <div className="review-card" style={{ padding: 20, textAlign: 'center' }}>
          <div className="review-heading" style={{ fontSize: 18, fontWeight: 800, marginBottom: 8 }}>
            Move-by-move review
          </div>
          <p style={{ fontSize: 13, opacity: 0.8, margin: 0 }}>
            The stepper, coach bubble and on-board badges arrive in the next phase.
          </p>
        </div>
      </aside>
    );
  }

  const copy = coachCopy(data);

  return (
    <aside
      data-testid="review-sidebar"
      data-mode="highlights"
      style={{ width: 430, maxWidth: '100%', display: 'flex', flexDirection: 'column', gap: 14 }}
    >
      <CoachIntro
        openingName={data.opening?.name || undefined}
        headline={copy.headline}
        message={copy.message}
      />

      <div style={{ display: 'flex', gap: 12 }}>
        <AccuracyCard label={white.name} value={data.accuracy.w} color="var(--review-accent)" />
        <AccuracyCard label={black.name} value={data.accuracy.b} color="var(--review-text-dim)" />
      </div>

      <PlayersAccuracyRow
        white={{ name: white.name, rating: white.rating, color: 'w', accuracy: data.accuracy.w }}
        black={{ name: black.name, rating: black.rating, color: 'b', accuracy: data.accuracy.b }}
      />

      <TallyTable tally={data.tally} />

      <GameRating
        whiteRating={data.estRating.w}
        blackRating={data.estRating.b}
        whiteName={white.name}
        blackName={black.name}
      />

      <PhaseStats phases={data.phases} />

      <button
        type="button"
        data-testid="start-review-cta"
        className="review-cta"
        onClick={onStartReview}
        style={{ padding: '14px', fontSize: 16 }}
      >
        Start Review →
      </button>
    </aside>
  );
}

'use client';

import type { EngineEval } from './types';

/**
 * White-fill vertical offset for the eval bar.
 *
 * The fill layer is a full-height white block anchored to the bottom; it slides
 * DOWN by `(100 − whiteWin%)` so the black band shows above. `translate3d` keeps
 * it on the GPU; a 0.5s ease transition glides between moves (Part B).
 */
export function whiteFillOffset(whiteWinPercent: number): number {
  const clamped = Math.max(0, Math.min(100, whiteWinPercent));
  return 100 - clamped;
}

/** Abbreviated score label from a White-POV eval (e.g. "+3.2", "M4", "-0.4"). */
export function evalLabel(e: EngineEval): string {
  if (e.type === 'mate') {
    return `M${Math.abs(e.value)}`;
  }
  const pawns = e.value / 100;
  const sign = pawns > 0 ? '+' : pawns < 0 ? '-' : '';
  return `${sign}${Math.abs(pawns).toFixed(1)}`;
}

export interface EvalBarProps {
  /** Win probability for White (0–100). */
  whiteWinPercent: number;
  /** White-POV engine eval for the score label. */
  evaluation: EngineEval;
  /**
   * Explicit pixel height. When omitted the bar tracks the board via the
   * `.review-eval-bar` class — a fixed 688 on desktop, and `height:auto` +
   * `align-self:stretch` on mobile so it matches the shrunken board's height
   * instead of leaving a tall empty gap.
   */
  height?: number;
}

export default function EvalBar({ whiteWinPercent, evaluation, height }: EvalBarProps) {
  const offset = whiteFillOffset(whiteWinPercent);
  const whiteLeads = whiteWinPercent >= 50;

  return (
    <div
      data-testid="eval-bar"
      className="review-eval-bar"
      style={{
        width: 26,
        ...(height !== undefined ? { height } : null),
        position: 'relative',
        overflow: 'hidden',
        borderRadius: 4,
        background: 'var(--review-evalbar-track)',
        flex: 'none',
      }}
    >
      <div
        data-testid="eval-bar-fill"
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: '100%',
          background: 'var(--review-evalbar-fill)',
          transform: `translate3d(0, ${offset}%, 0)`,
          transition: 'transform 0.5s ease',
        }}
      />
      <span
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          textAlign: 'center',
          fontSize: 10,
          fontWeight: 800,
          zIndex: 2,
          // Label sits on whichever side is winning, in a legible colour.
          ...(whiteLeads
            ? { bottom: 4, color: 'var(--review-evalbar-score)' }
            : { top: 4, color: 'var(--review-evalbar-fill)' }),
        }}
      >
        {evalLabel(evaluation)}
      </span>
    </div>
  );
}

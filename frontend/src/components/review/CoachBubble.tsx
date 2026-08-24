'use client';

import ClassificationIcon, { CLASSIFICATION_LABELS } from './ClassificationIcon';
import type { ReviewMove } from './types';

/**
 * Signed eval delta of a move in PAWNS, from the MOVER's point of view.
 * Positive = the move improved the mover's eval; negative = it cost them.
 * Book plies and ply 1 have no meaningful "before", so we compare against the
 * previous position's white-POV eval (0 before the first move).
 */
export function evalDeltaPawns(move: ReviewMove, prev: ReviewMove | null): number {
  const before = prev ? evalToCp(prev) : 0;
  const after = evalToCp(move);
  const whiteDelta = after - before;
  const moverIsWhite = move.ply % 2 === 1;
  const moverDelta = moverIsWhite ? whiteDelta : -whiteDelta;
  return moverDelta / 100;
}

/** White-POV centipawns, mate resolved to a large clamp so deltas stay finite. */
function evalToCp(move: ReviewMove): number {
  if (move.eval.type === 'mate') {
    return move.eval.value >= 0 ? 2000 : -2000;
  }
  return move.eval.value;
}

/** "+1.2" / "-0.4" / "0.0" — always signed. */
export function formatDelta(pawns: number): string {
  const rounded = Math.abs(pawns) < 0.05 ? 0 : pawns;
  const sign = rounded > 0 ? '+' : rounded < 0 ? '−' : '';
  return `${sign}${Math.abs(rounded).toFixed(1)}`;
}

/**
 * Deterministic v1 coach commentary — a template per classification, keyed on
 * SAN, book/opening flag and a trivially-derivable "hangs a piece" hint (a
 * capture SAN answering a blunder/mistake). The LLM "Explain" upgrade is Phase 5.
 */
export function coachText(
  move: ReviewMove,
  prev: ReviewMove | null,
  opening?: { name?: string; lastBookPly?: number },
): string {
  const san = move.san;
  const isLastBook = !!opening && opening.lastBookPly === move.ply;

  switch (move.classification) {
    case 'book':
      return isLastBook
        ? `${san} is the last book move${opening?.name ? ` of the ${opening.name}` : ''}.`
        : `${san} is still theory — a well-known book move.`;
    case 'brilliant':
      return `Brilliant! ${san} is a stunning sacrifice that the engine loves.`;
    case 'great':
      return `Great move — ${san} was the only move that keeps your position together.`;
    case 'best':
      return `${san} is the best move here. Nothing improves on it.`;
    case 'excellent':
      return `${san} is excellent — right in line with the engine.`;
    case 'good':
      return `${san} is a good, solid move.`;
    case 'forced':
      return `${san} is forced — there was nothing else.`;
    case 'inaccuracy':
      return `${san} is a slight inaccuracy. There was something a little sharper.`;
    case 'mistake':
      return `${san} is a mistake and lets some of your advantage slip away.`;
    case 'miss':
      return `${san} misses a stronger continuation that was on the board.`;
    case 'blunder':
      return `${san} is a blunder${dropsMaterial(move, prev) ? ' — it drops material' : ''}. The engine had much better.`;
    default:
      return san;
  }
}

/** A blunder/mistake whose eval collapsed alongside a capture-shaped reply. */
function dropsMaterial(move: ReviewMove, prev: ReviewMove | null): boolean {
  const delta = evalDeltaPawns(move, prev);
  return delta <= -2;
}

export interface CoachBubbleProps {
  move: ReviewMove | null;
  prev: ReviewMove | null;
  opening?: { name?: string; lastBookPly?: number };
}

/** Review-mode coach bubble: classification icon + SAN + delta chip + text. */
export default function CoachBubble({ move, prev, opening }: CoachBubbleProps) {
  if (!move) {
    return (
      <div className="review-card" data-testid="coach-bubble" style={{ padding: 14, minHeight: 92 }}>
        <p style={{ fontSize: 13, opacity: 0.75, margin: 0 }}>
          Step through the game to see move-by-move coaching.
        </p>
      </div>
    );
  }

  const delta = evalDeltaPawns(move, prev);
  const deltaStr = formatDelta(delta);
  const deltaNegative = delta < -0.05;

  return (
    <div
      className="review-card"
      data-testid="coach-bubble"
      data-classification={move.classification}
      style={{ padding: 14, minHeight: 92, display: 'flex', gap: 12, alignItems: 'flex-start' }}
    >
      <div style={{ width: 40, height: 40, flex: 'none' }}>
        <ClassificationIcon type={move.classification} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
          <span
            className="review-heading"
            data-testid="coach-san"
            style={{
              fontWeight: 800,
              fontSize: 15,
              color: `var(--color-classification-${move.classification})`,
            }}
          >
            {move.san}
          </span>
          <span style={{ fontSize: 12, fontWeight: 700, opacity: 0.7 }}>
            {CLASSIFICATION_LABELS[move.classification]}
          </span>
          <span
            data-testid="coach-delta"
            style={{
              fontSize: 12,
              fontWeight: 800,
              padding: '1px 7px',
              borderRadius: 999,
              background: 'var(--review-neutral)',
              color: deltaNegative ? 'var(--color-classification-blunder)' : 'var(--review-text-dim)',
            }}
          >
            {deltaStr}
          </span>
        </div>
        <p style={{ fontSize: 13, lineHeight: 1.4, margin: 0, opacity: 0.9 }}>
          {coachText(move, prev, opening)}
        </p>
        {opening?.name && move.classification === 'book' && (
          <div
            style={{ fontSize: 11.5, marginTop: 6, opacity: 0.6, textDecoration: 'underline' }}
          >
            {opening.name}
          </div>
        )}
      </div>
    </div>
  );
}

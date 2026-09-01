'use client';

import { useEffect, useRef } from 'react';
import ClassificationIcon from './ClassificationIcon';
import type { ReviewMove } from './types';

/** Classifications quiet enough to leave the SAN in the default text colour. */
const NEUTRAL_CLASSES = new Set(['book', 'forced']);

export interface MoveListProps {
  moves: ReviewMove[];
  /** 1-based ply currently selected (0 = start position). */
  currentPly: number;
  onSelect: (ply: number) => void;
}

interface MovePair {
  moveNo: number;
  white?: ReviewMove;
  black?: ReviewMove;
}

/** Group the flat ply list into white/black move-number rows. */
export function toMovePairs(moves: ReviewMove[]): MovePair[] {
  const pairs: MovePair[] = [];
  for (const m of moves) {
    const moveNo = Math.ceil(m.ply / 2);
    const isWhite = m.ply % 2 === 1;
    let pair = pairs[pairs.length - 1];
    if (!pair || pair.moveNo !== moveNo) {
      pair = { moveNo };
      pairs.push(pair);
    }
    if (isWhite) pair.white = m;
    else pair.black = m;
  }
  return pairs;
}

function MoveNode({
  move,
  selected,
  onSelect,
}: {
  move: ReviewMove;
  selected: boolean;
  onSelect: (ply: number) => void;
}) {
  const color = `var(--color-classification-${move.classification})`;
  return (
    <button
      type="button"
      data-testid="move-node"
      data-ply={move.ply}
      data-classification={move.classification}
      data-selected={selected ? 'true' : 'false'}
      onClick={() => onSelect(move.ply)}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '3px 7px',
        borderRadius: 6,
        border: 'none',
        cursor: 'pointer',
        background: selected ? 'var(--review-tint)' : 'transparent',
        fontFamily: 'var(--review-font)',
        fontSize: 13.5,
        fontWeight: 700,
        color: NEUTRAL_CLASSES.has(move.classification) ? 'var(--review-text)' : color,
      }}
    >
      <ClassificationIcon type={move.classification} size={18} />
      <span>{move.san}</span>
    </button>
  );
}

/**
 * Annotated move list: two-column white/black pairs, an 18px classification
 * badge per ply, SAN coloured by `--color-classification-*`, the selected ply
 * highlighted and auto-scrolled into view. Clicking a ply sets currentPly.
 */
export default function MoveList({ moves, currentPly, onSelect }: MoveListProps) {
  const pairs = toMovePairs(moves);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = listRef.current;
    const node = container?.querySelector<HTMLElement>('[data-selected="true"]');
    if (!container || !node) return;
    const c = container.getBoundingClientRect();
    const n = node.getBoundingClientRect();
    if (n.top < c.top) {
      container.scrollTop -= c.top - n.top;
    } else if (n.bottom > c.bottom) {
      container.scrollTop += n.bottom - c.bottom;
    }
  }, [currentPly]);

  return (
    <div
      ref={listRef}
      className="review-card"
      data-testid="move-list"
      style={{ padding: 8, maxHeight: 260, overflowY: 'auto' }}
    >
      {pairs.map((pair) => (
        <div
          key={pair.moveNo}
          style={{
            display: 'grid',
            gridTemplateColumns: '28px 1fr 1fr',
            alignItems: 'center',
            gap: 4,
            padding: '1px 2px',
          }}
        >
          <span style={{ fontSize: 12, opacity: 0.5, textAlign: 'right' }}>{pair.moveNo}.</span>
          <span>
            {pair.white && (
              <MoveNode
                move={pair.white}
                selected={currentPly === pair.white.ply}
                onSelect={onSelect}
              />
            )}
          </span>
          <span>
            {pair.black && (
              <MoveNode
                move={pair.black}
                selected={currentPly === pair.black.ply}
                onSelect={onSelect}
              />
            )}
          </span>
        </div>
      ))}
    </div>
  );
}

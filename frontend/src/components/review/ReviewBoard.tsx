'use client';

import ChessgroundBoard from '@/components/chess/ChessgroundBoard';

export interface ReviewBoardProps {
  fen: string;
  orientation?: 'white' | 'black';
  lastMove?: [string, string] | null;
}

/**
 * Read-only review board. Reuses the app's ChessgroundBoard; square colours are
 * driven by the --review-* board vars via globals.css. On-board badges, square
 * tints and the stepper are Phase 4 — this renders a static position only.
 */
export default function ReviewBoard({ fen, orientation = 'white', lastMove }: ReviewBoardProps) {
  return (
    <div
      data-testid="review-board"
      style={{
        borderRadius: 16,
        overflow: 'hidden',
        boxShadow: 'var(--review-board-shadow)',
        maxWidth: 520,
        width: '100%',
      }}
    >
      <ChessgroundBoard
        fen={fen}
        orientation={orientation}
        movable={false}
        viewOnly
        lastMove={lastMove as never}
      />
    </div>
  );
}

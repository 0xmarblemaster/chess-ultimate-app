'use client';

export interface GameRatingProps {
  whiteRating: number;
  blackRating: number;
  whiteName?: string;
  blackName?: string;
}

/** Estimated performance rating per player (Part A Step 6 "Game Rating"). */
export default function GameRating({
  whiteRating,
  blackRating,
  whiteName = 'White',
  blackName = 'Black',
}: GameRatingProps) {
  return (
    <div
      className="review-card"
      data-testid="game-rating"
      style={{ padding: '12px 14px' }}
    >
      <div
        className="review-heading"
        style={{ fontSize: 12, fontWeight: 700, color: 'var(--review-text-dim)', marginBottom: 8 }}
      >
        Game Rating
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        {[
          { name: whiteName, rating: whiteRating },
          { name: blackName, rating: blackRating },
        ].map((p) => (
          <div key={p.name} style={{ flex: 1, textAlign: 'center' }}>
            <div
              className="review-heading"
              style={{ fontSize: 26, fontWeight: 800, color: 'var(--review-accent)' }}
            >
              {p.rating}
            </div>
            <div style={{ fontSize: 12, color: 'var(--review-text-dim)', fontWeight: 600 }}>
              {p.name}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

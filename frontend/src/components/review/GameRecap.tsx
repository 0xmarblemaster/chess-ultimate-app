'use client';

import { useTranslations } from 'next-intl';
import type { CoachEntry } from '@/hooks/useReviewCoach';

export interface GameRecapProps {
  recap: CoachEntry;
  onRecap: () => void;
}

/**
 * F3 — whole-game coach recap card, pinned to the top of the review sidebar.
 * Manual trigger; streams the coach's narrative (turning points, recurring
 * weakness, one thing to work on) grounded in the pipeline aggregates.
 */
export default function GameRecap({ recap, onRecap }: GameRecapProps) {
  const t = useTranslations('gameReview');
  const { status, content } = recap;
  const streaming = status === 'streaming';

  return (
    <div
      className="review-card"
      data-testid="game-recap"
      data-status={status}
      style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span className="review-heading" style={{ fontWeight: 800, fontSize: 14 }}>
          ✨ {t('coach.recap.title')}
        </span>
        {status === 'idle' && (
          <button
            type="button"
            data-testid="game-recap-btn"
            onClick={onRecap}
            className="review-ghost-btn"
            style={{ padding: '6px 12px', fontSize: 12.5, fontWeight: 700 }}
          >
            {t('coach.recap.cta')}
          </button>
        )}
        {status === 'error' && (
          <button
            type="button"
            data-testid="game-recap-retry"
            onClick={onRecap}
            className="review-ghost-btn"
            style={{ padding: '6px 12px', fontSize: 12.5, fontWeight: 700 }}
          >
            {t('coach.recap.retry')}
          </button>
        )}
      </div>

      {status === 'idle' && (
        <p style={{ fontSize: 12.5, opacity: 0.7, margin: 0 }}>{t('coach.recap.subtitle')}</p>
      )}

      {status === 'error' && (
        <p
          data-testid="game-recap-error"
          style={{ fontSize: 12.5, margin: 0, color: 'var(--color-classification-blunder)' }}
        >
          {t('coach.recap.error')}
        </p>
      )}

      {(status === 'streaming' || status === 'done') && (
        <p
          data-testid="game-recap-content"
          style={{ fontSize: 13, lineHeight: 1.5, margin: 0, whiteSpace: 'pre-wrap' }}
        >
          {content}
          {streaming && (
            <span data-testid="game-recap-loading" style={{ opacity: 0.6 }}>
              {content ? ' ▍' : t('coach.recap.loading')}
            </span>
          )}
        </p>
      )}
    </div>
  );
}

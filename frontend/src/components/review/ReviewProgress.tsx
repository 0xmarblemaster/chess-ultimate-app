'use client';

import Image from 'next/image';
import { useTranslations } from 'next-intl';

export interface ReviewProgressProps {
  /** 0–1 analysis progress. */
  progress: number;
  status: 'queued' | 'running';
}

/** Themed progress panel shown while the engine is still analysing. */
export default function ReviewProgress({ progress, status }: ReviewProgressProps) {
  const t = useTranslations('gameReview');
  const pct = Math.round(Math.max(0, Math.min(1, progress)) * 100);
  return (
    <div
      data-testid="review-progress"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 18,
        minHeight: '60vh',
        padding: 24,
      }}
    >
      <Image
        src="/static/images/chesster-logo-v3.png"
        alt=""
        width={56}
        height={56}
        className="animate-mascotBounce"
        priority
      />
      <div className="review-heading" style={{ fontSize: 20, fontWeight: 800 }}>
        {status === 'queued' ? t('progress.queued') : t('progress.running')}
      </div>
      <div
        style={{
          width: 'min(420px, 80vw)',
          height: 12,
          borderRadius: 999,
          background: 'var(--review-neutral)',
          overflow: 'hidden',
        }}
      >
        <div
          data-testid="review-progress-fill"
          style={{
            width: `${pct}%`,
            height: '100%',
            background: 'var(--review-cta-gradient)',
            transition: 'width 0.4s ease',
          }}
        />
      </div>
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--review-text-dim)' }}>{pct}%</div>
    </div>
  );
}

'use client';

import { useTranslations } from 'next-intl';
import type { ReviewResult } from './types';

const PHASE_KEYS: Array<keyof ReviewResult['phases']> = ['opening', 'middlegame', 'endgame'];

function fmt(v: number | null): string {
  return v == null ? '—' : v.toFixed(1);
}

export interface PhaseStatsProps {
  phases: ReviewResult['phases'];
}

/** Per-phase accuracy split (Part A Step 6 "Phase stats"). */
export default function PhaseStats({ phases }: PhaseStatsProps) {
  const t = useTranslations('gameReview');
  return (
    <div className="review-card" data-testid="phase-stats" style={{ padding: '12px 14px' }}>
      <div
        className="review-heading"
        style={{ fontSize: 12, fontWeight: 700, color: 'var(--review-text-dim)', marginBottom: 8 }}
      >
        {t('phases.title')}
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 48px 48px',
          rowGap: 6,
          fontSize: 13,
        }}
      >
        <span style={{ color: 'var(--review-text-dim)', fontWeight: 600 }} />
        <span style={{ textAlign: 'center', fontWeight: 700, color: 'var(--review-text-dim)' }}>
          {t('players.whiteShort')}
        </span>
        <span style={{ textAlign: 'center', fontWeight: 700, color: 'var(--review-text-dim)' }}>
          {t('players.blackShort')}
        </span>
        {PHASE_KEYS.map((key) => (
          <PhaseRow
            key={key}
            label={t(`phases.${key}`)}
            w={fmt(phases[key].w)}
            b={fmt(phases[key].b)}
          />
        ))}
      </div>
    </div>
  );
}

function PhaseRow({ label, w, b }: { label: string; w: string; b: string }) {
  return (
    <>
      <span style={{ fontWeight: 600 }}>{label}</span>
      <span style={{ textAlign: 'center', fontWeight: 800 }}>{w}</span>
      <span style={{ textAlign: 'center', fontWeight: 800 }}>{b}</span>
    </>
  );
}

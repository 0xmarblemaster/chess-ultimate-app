'use client';

import { useTranslations } from 'next-intl';
import ClassificationIcon, {
  CLASSIFICATION_COLORS,
  type Classification,
} from './ClassificationIcon';
import type { Tally } from './types';

/** Rows in the frozen palette order (forced is shown only when it occurs). */
const ROW_ORDER: Classification[] = [
  'brilliant',
  'great',
  'best',
  'excellent',
  'good',
  'book',
  'inaccuracy',
  'mistake',
  'miss',
  'blunder',
];

export interface TallyTableProps {
  tally: Tally;
}

export default function TallyTable({ tally }: TallyTableProps) {
  const t = useTranslations('gameReview');
  const rows = [...ROW_ORDER];
  if ((tally.w.forced ?? 0) + (tally.b.forced ?? 0) > 0) {
    rows.push('forced');
  }

  return (
    <div
      className="review-card"
      data-testid="tally-table"
      style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 2 }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '40px 1fr 40px',
          alignItems: 'center',
          fontSize: 11,
          fontWeight: 700,
          color: 'var(--review-text-dim)',
          padding: '2px 0 6px',
        }}
      >
        <span style={{ textAlign: 'center' }}>{t('players.whiteShort')}</span>
        <span />
        <span style={{ textAlign: 'center' }}>{t('players.blackShort')}</span>
      </div>
      {rows.map((cls) => {
        const w = tally.w[cls] ?? 0;
        const b = tally.b[cls] ?? 0;
        const color = CLASSIFICATION_COLORS[cls];
        return (
          <div
            key={cls}
            data-testid={`tally-row-${cls}`}
            style={{
              display: 'grid',
              gridTemplateColumns: '40px 1fr 40px',
              alignItems: 'center',
              padding: '3px 0',
            }}
          >
            <span
              data-testid={`tally-w-${cls}`}
              style={{ textAlign: 'center', fontWeight: 800, fontSize: 14, color }}
            >
              {w}
            </span>
            <span
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              <ClassificationIcon type={cls} size={24} />
              {t(`classifications.${cls}`)}
            </span>
            <span
              data-testid={`tally-b-${cls}`}
              style={{ textAlign: 'center', fontWeight: 800, fontSize: 14, color }}
            >
              {b}
            </span>
          </div>
        );
      })}
    </div>
  );
}

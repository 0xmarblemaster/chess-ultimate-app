'use client';

import type { ReviewResult } from './types';

const PHASES: Array<{ key: keyof ReviewResult['phases']; label: string }> = [
  { key: 'opening', label: 'Opening' },
  { key: 'middlegame', label: 'Middlegame' },
  { key: 'endgame', label: 'Endgame' },
];

function fmt(v: number | null): string {
  return v == null ? '—' : v.toFixed(1);
}

export interface PhaseStatsProps {
  phases: ReviewResult['phases'];
}

/** Per-phase accuracy split (Part A Step 6 "Phase stats"). */
export default function PhaseStats({ phases }: PhaseStatsProps) {
  return (
    <div className="review-card" data-testid="phase-stats" style={{ padding: '12px 14px' }}>
      <div
        className="review-heading"
        style={{ fontSize: 12, fontWeight: 700, color: 'var(--review-text-dim)', marginBottom: 8 }}
      >
        Phases
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
          W
        </span>
        <span style={{ textAlign: 'center', fontWeight: 700, color: 'var(--review-text-dim)' }}>
          B
        </span>
        {PHASES.map(({ key, label }) => (
          <PhaseRow key={key} label={label} w={fmt(phases[key].w)} b={fmt(phases[key].b)} />
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

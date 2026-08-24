'use client';

import { useEffect, useState } from 'react';

const R = 34;
const CIRC = 2 * Math.PI * R;

export interface AccuracyCardProps {
  label: string;
  /** Accuracy 0–100. */
  value: number;
  /** Arc colour; defaults to the review accent. */
  color?: string;
}

/**
 * Circular accuracy gauge. The arc sweeps 0 → value on mount over ~1s
 * (Highcharts-style, Part B), driven by a CSS transition on stroke-dashoffset.
 */
export default function AccuracyCard({ label, value, color }: AccuracyCardProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const pct = Math.max(0, Math.min(100, value));
  const offset = mounted ? CIRC * (1 - pct / 100) : CIRC;

  return (
    <div
      className="review-card"
      data-testid="accuracy-card"
      style={{
        padding: '14px 10px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 6,
        flex: 1,
      }}
    >
      <div style={{ position: 'relative', width: 84, height: 84 }}>
        <svg viewBox="0 0 84 84" width="84" height="84" style={{ transform: 'rotate(-90deg)' }}>
          <circle
            cx="42"
            cy="42"
            r={R}
            fill="none"
            stroke="var(--review-neutral)"
            strokeWidth="7"
          />
          <circle
            cx="42"
            cy="42"
            r={R}
            fill="none"
            stroke={color ?? 'var(--review-accent)'}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={CIRC}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 1s ease' }}
          />
        </svg>
        <span
          data-testid="accuracy-value"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 18,
            fontWeight: 800,
            fontFamily: 'var(--review-font-heading)',
          }}
        >
          {pct.toFixed(1)}
        </span>
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--review-text-dim)' }}>
        {label}
      </span>
    </div>
  );
}

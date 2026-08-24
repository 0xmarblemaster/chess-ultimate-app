'use client';

import { useRef, useState } from 'react';
import type { EngineEval, ReviewMove } from './types';
import { CLASSIFICATION_COLORS } from './ClassificationIcon';

/** Eval clamped to ±CLAMP pawns (White POV). Mate resolves to the rail. */
export const EVAL_CLAMP = 6;

export function clampEvalToPawns(e: EngineEval): number {
  if (e.type === 'mate') {
    return e.value > 0 ? EVAL_CLAMP : -EVAL_CLAMP;
  }
  const pawns = e.value / 100;
  return Math.max(-EVAL_CLAMP, Math.min(EVAL_CLAMP, pawns));
}

/** Series of clamped White-POV evals, one per ply (P1..PN). */
export function evalSeries(moves: ReviewMove[]): number[] {
  return moves.map((m) => clampEvalToPawns(m.eval));
}

const W = 380;
const H = 90;
const PAD_X = 8;

/** Map a clamped pawn value to a y coordinate in the viewBox. */
function pawnsToY(pawns: number): number {
  // +CLAMP → 0 (top, white winning), −CLAMP → H (bottom, black winning).
  const t = (EVAL_CLAMP - pawns) / (2 * EVAL_CLAMP);
  return t * H;
}

function plyToX(index: number, n: number): number {
  if (n <= 1) return PAD_X;
  return PAD_X + ((W - 2 * PAD_X) * index) / (n - 1);
}

export interface EvalGraphProps {
  moves: ReviewMove[];
  keyMoments: number[];
  currentPly?: number;
  onSelectPly?: (ply: number) => void;
}

export default function EvalGraph({
  moves,
  keyMoments,
  currentPly,
  onSelectPly,
}: EvalGraphProps) {
  const ref = useRef<SVGSVGElement | null>(null);
  const [hoverX, setHoverX] = useState<number | null>(null);

  const series = evalSeries(moves);
  const n = series.length;
  const mid = H / 2;

  const linePoints = series
    .map((p, i) => `${plyToX(i, n).toFixed(1)},${pawnsToY(p).toFixed(1)}`)
    .join(' ');

  // Area polygon: series line closed back along the midline (eval 0).
  const areaPoints =
    n > 0
      ? `${PAD_X},${mid} ${linePoints} ${plyToX(n - 1, n).toFixed(1)},${mid}`
      : '';

  function handleMove(ev: React.MouseEvent<SVGSVGElement>) {
    const svg = ref.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const x = ((ev.clientX - rect.left) / rect.width) * W;
    setHoverX(x);
  }

  function nearestPly(x: number): number {
    if (n === 0) return 0;
    const step = (W - 2 * PAD_X) / Math.max(1, n - 1);
    const idx = Math.round((x - PAD_X) / step);
    return Math.max(1, Math.min(n, idx + 1));
  }

  function handleClick(ev: React.MouseEvent<SVGSVGElement>) {
    const svg = ref.current;
    if (!svg || !onSelectPly) return;
    const rect = svg.getBoundingClientRect();
    const x = ((ev.clientX - rect.left) / rect.width) * W;
    onSelectPly(nearestPly(x));
  }

  return (
    <svg
      ref={ref}
      data-testid="eval-graph"
      className="review-card"
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      role="img"
      aria-label="Evaluation over time"
      style={{ cursor: onSelectPly ? 'pointer' : 'default', display: 'block' }}
      onMouseMove={handleMove}
      onMouseLeave={() => setHoverX(null)}
      onClick={handleClick}
    >
      {/* White / black halves */}
      <rect x="0" y="0" width={W} height={mid} fill="var(--review-card-solid)" opacity="0.0" />
      {n > 0 && (
        <polygon points={areaPoints} fill="var(--review-graph-line)" opacity="0.25" />
      )}
      {n > 0 && (
        <polyline
          points={linePoints}
          fill="none"
          stroke="var(--review-graph-line)"
          strokeWidth="1.5"
        />
      )}
      {/* Equality midline */}
      <line x1="0" y1={mid} x2={W} y2={mid} stroke="#888" strokeWidth="0.5" opacity="0.6" />

      {/* Key-moment markers: halo + classification-coloured dot */}
      {keyMoments.map((ply) => {
        const idx = ply - 1;
        if (idx < 0 || idx >= n) return null;
        const cx = plyToX(idx, n);
        const cy = pawnsToY(series[idx]);
        const color = CLASSIFICATION_COLORS[moves[idx].classification];
        return (
          <g key={ply} data-testid="keymoment-dot" data-ply={ply}>
            <circle cx={cx} cy={cy} r="7" fill={color} fillOpacity="0.25" />
            <circle cx={cx} cy={cy} r="3.5" fill={color} />
          </g>
        );
      })}

      {/* Current-ply marker */}
      {currentPly != null && currentPly >= 1 && currentPly <= n && (
        <line
          data-testid="current-ply-line"
          x1={plyToX(currentPly - 1, n)}
          y1="0"
          x2={plyToX(currentPly - 1, n)}
          y2={H}
          stroke="var(--review-accent)"
          strokeWidth="1"
          opacity="0.7"
        />
      )}

      {/* Hover crosshair */}
      {hoverX != null && (
        <line
          data-testid="hover-crosshair"
          x1={hoverX}
          y1="0"
          x2={hoverX}
          y2={H}
          stroke="var(--review-text-dim)"
          strokeWidth="0.75"
          opacity="0.5"
        />
      )}
    </svg>
  );
}

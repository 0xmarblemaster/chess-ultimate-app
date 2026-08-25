/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import { renderIntl } from './intl';
import EvalGraph, { clampEvalToPawns, evalSeries, EVAL_CLAMP } from '../EvalGraph';
import { REVIEW_FIXTURE } from './fixture';

afterEach(cleanup);

describe('clampEvalToPawns', () => {
  it('converts centipawns to pawns', () => {
    expect(clampEvalToPawns({ type: 'cp', value: 320 })).toBeCloseTo(3.2);
    expect(clampEvalToPawns({ type: 'cp', value: -50 })).toBeCloseTo(-0.5);
  });

  it('clamps to ±EVAL_CLAMP', () => {
    expect(clampEvalToPawns({ type: 'cp', value: 5000 })).toBe(EVAL_CLAMP);
    expect(clampEvalToPawns({ type: 'cp', value: -5000 })).toBe(-EVAL_CLAMP);
  });

  it('resolves mate to the rail', () => {
    expect(clampEvalToPawns({ type: 'mate', value: 3 })).toBe(EVAL_CLAMP);
    expect(clampEvalToPawns({ type: 'mate', value: -1 })).toBe(-EVAL_CLAMP);
  });
});

describe('evalSeries', () => {
  it('produces one clamped value per ply', () => {
    const series = evalSeries(REVIEW_FIXTURE.moves);
    expect(series).toHaveLength(REVIEW_FIXTURE.moves.length);
    expect(series[4]).toBeCloseTo(3.2); // ply 5 = +320cp
  });
});

describe('EvalGraph', () => {
  it('renders one key-moment dot group per key moment', () => {
    const { container } = renderIntl(
      <EvalGraph moves={REVIEW_FIXTURE.moves} keyMoments={REVIEW_FIXTURE.keyMoments} />,
    );
    const dots = container.querySelectorAll('[data-testid="keymoment-dot"]');
    expect(dots).toHaveLength(REVIEW_FIXTURE.keyMoments.length);
  });

  it('colours each key-moment dot by its move classification', () => {
    const { container } = renderIntl(
      <EvalGraph moves={REVIEW_FIXTURE.moves} keyMoments={[6]} />,
    );
    const group = container.querySelector('[data-testid="keymoment-dot"][data-ply="6"]')!;
    const solid = group.querySelectorAll('circle')[1];
    // ply 6 is a brilliant → #26C2A3
    expect(solid.getAttribute('fill')?.toUpperCase()).toBe('#26C2A3');
  });

  it('draws a current-ply marker when set', () => {
    const { getByTestId } = renderIntl(
      <EvalGraph moves={REVIEW_FIXTURE.moves} keyMoments={[]} currentPly={3} />,
    );
    expect(getByTestId('current-ply-line')).toBeTruthy();
  });
});

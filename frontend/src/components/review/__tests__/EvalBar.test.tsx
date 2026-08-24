/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, afterEach } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import EvalBar, { whiteFillOffset, evalLabel } from '../EvalBar';

afterEach(cleanup);

describe('whiteFillOffset', () => {
  it('maps win% to the translate offset (100 − whiteWin%)', () => {
    expect(whiteFillOffset(50)).toBe(50);
    expect(whiteFillOffset(79)).toBeCloseTo(21);
    expect(whiteFillOffset(100)).toBe(0);
    expect(whiteFillOffset(0)).toBe(100);
  });

  it('clamps out-of-range inputs', () => {
    expect(whiteFillOffset(140)).toBe(0);
    expect(whiteFillOffset(-20)).toBe(100);
  });
});

describe('evalLabel', () => {
  it('formats centipawns with a sign and one decimal', () => {
    expect(evalLabel({ type: 'cp', value: 320 })).toBe('+3.2');
    expect(evalLabel({ type: 'cp', value: -43 })).toBe('-0.4');
    expect(evalLabel({ type: 'cp', value: 0 })).toBe('0.0');
  });

  it('formats mate as M<n>', () => {
    expect(evalLabel({ type: 'mate', value: 4 })).toBe('M4');
    expect(evalLabel({ type: 'mate', value: -2 })).toBe('M2');
  });
});

describe('EvalBar', () => {
  it('applies the translate3d transform from win%', () => {
    const { getByTestId } = render(
      <EvalBar whiteWinPercent={79} evaluation={{ type: 'cp', value: 320 }} />,
    );
    const fill = getByTestId('eval-bar-fill');
    expect(fill.style.transform).toBe('translate3d(0, 21%, 0)');
    expect(fill.style.transition).toContain('transform');
  });
});

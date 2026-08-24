/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, afterEach } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import TallyTable from '../TallyTable';
import { REVIEW_FIXTURE } from './fixture';

afterEach(cleanup);

describe('TallyTable', () => {
  it('renders each player count from the fixture', () => {
    const { getByTestId } = render(<TallyTable tally={REVIEW_FIXTURE.tally} />);
    expect(getByTestId('tally-w-brilliant').textContent).toBe('1');
    expect(getByTestId('tally-b-brilliant').textContent).toBe('0');
    expect(getByTestId('tally-b-blunder').textContent).toBe('1');
    expect(getByTestId('tally-w-book').textContent).toBe('1');
    expect(getByTestId('tally-b-book').textContent).toBe('1');
  });

  it('colours counts with the classification palette', () => {
    const { getByTestId } = render(<TallyTable tally={REVIEW_FIXTURE.tally} />);
    const cell = getByTestId('tally-w-brilliant');
    expect(cell.style.color).toMatch(/rgb\(38, 194, 163\)|#26C2A3/i);
  });

  it('renders all ten palette rows and hides forced when zero', () => {
    const { getByTestId, queryByTestId } = render(<TallyTable tally={REVIEW_FIXTURE.tally} />);
    expect(getByTestId('tally-row-brilliant')).toBeTruthy();
    expect(getByTestId('tally-row-blunder')).toBeTruthy();
    expect(queryByTestId('tally-row-forced')).toBeNull();
  });
});

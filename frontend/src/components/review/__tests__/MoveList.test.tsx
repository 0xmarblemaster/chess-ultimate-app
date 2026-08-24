/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, afterEach, vi } from 'vitest';
import { cleanup, render, fireEvent } from '@testing-library/react';
import MoveList, { toMovePairs } from '../MoveList';
import { REVIEW_FIXTURE } from './fixture';

afterEach(cleanup);

describe('toMovePairs', () => {
  it('groups plies into white/black move-number rows', () => {
    const pairs = toMovePairs(REVIEW_FIXTURE.moves);
    expect(pairs).toHaveLength(3); // 6 plies → 3 full pairs
    expect(pairs[0]).toMatchObject({ moveNo: 1, white: { ply: 1 }, black: { ply: 2 } });
    expect(pairs[2]).toMatchObject({ moveNo: 3, white: { ply: 5 }, black: { ply: 6 } });
  });
});

describe('MoveList', () => {
  it('renders one node per ply with an 18px classification badge', () => {
    const { getAllByTestId } = render(
      <MoveList moves={REVIEW_FIXTURE.moves} currentPly={0} onSelect={() => {}} />,
    );
    const nodes = getAllByTestId('move-node');
    expect(nodes).toHaveLength(REVIEW_FIXTURE.moves.length);
    // Every node carries an 18×18 badge svg.
    nodes.forEach((node) => {
      const svg = node.querySelector('svg');
      expect(svg?.getAttribute('width')).toBe('18px');
    });
  });

  it('colours SAN by classification (and leaves book neutral)', () => {
    const { getAllByTestId } = render(
      <MoveList moves={REVIEW_FIXTURE.moves} currentPly={0} onSelect={() => {}} />,
    );
    const nodes = getAllByTestId('move-node');
    const blunder = nodes.find((n) => n.getAttribute('data-ply') === '5')!;
    const book = nodes.find((n) => n.getAttribute('data-ply') === '1')!;
    expect(blunder.getAttribute('style')).toContain('--color-classification-blunder');
    expect(book.getAttribute('style')).toContain('--review-text');
  });

  it('highlights the selected ply', () => {
    const { getAllByTestId } = render(
      <MoveList moves={REVIEW_FIXTURE.moves} currentPly={5} onSelect={() => {}} />,
    );
    const nodes = getAllByTestId('move-node');
    const selected = nodes.filter((n) => n.getAttribute('data-selected') === 'true');
    expect(selected).toHaveLength(1);
    expect(selected[0].getAttribute('data-ply')).toBe('5');
  });

  it('sets currentPly when a ply is clicked', () => {
    const onSelect = vi.fn();
    const { getAllByTestId } = render(
      <MoveList moves={REVIEW_FIXTURE.moves} currentPly={0} onSelect={onSelect} />,
    );
    const node = getAllByTestId('move-node').find((n) => n.getAttribute('data-ply') === '3')!;
    fireEvent.click(node);
    expect(onSelect).toHaveBeenCalledWith(3);
  });
});

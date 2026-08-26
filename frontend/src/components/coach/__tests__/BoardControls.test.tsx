/**
 * @vitest-environment jsdom
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';

import en from '../../../../messages/en.json';
import CoachBoardControls from '../BoardControls';

const coach = en.coach;

function makeHandlers() {
  return {
    onReset: vi.fn(),
    onFirst: vi.fn(),
    onPrev: vi.fn(),
    onNext: vi.fn(),
    onLast: vi.fn(),
    onFlip: vi.fn(),
  };
}

function renderControls(handlers: ReturnType<typeof makeHandlers>, boardSize?: number) {
  return render(
    <NextIntlClientProvider locale="en" messages={en as Record<string, unknown>}>
      <CoachBoardControls {...handlers} boardSize={boardSize} />
    </NextIntlClientProvider>
  );
}

afterEach(() => cleanup());

describe('CoachBoardControls — canonical NAV parity', () => {
  let handlers: ReturnType<typeof makeHandlers>;

  beforeEach(() => {
    handlers = makeHandlers();
  });

  it('renders exactly 6 nav cells in canonical order', () => {
    const { container } = renderControls(handlers);
    const cells = container.querySelectorAll('[title]');
    const titles = Array.from(cells).map((c) => c.getAttribute('title'));
    expect(titles).toEqual([
      coach.resetBoard,
      coach.firstMove,
      coach.previousMove,
      coach.nextMove,
      coach.lastMove,
      coach.flipBoard,
    ]);
  });

  it('includes the Reset cell (added — Coach previously lacked it)', () => {
    const { getByTitle } = renderControls(handlers);
    fireEvent.click(getByTitle(coach.resetBoard));
    expect(handlers.onReset).toHaveBeenCalledTimes(1);
  });

  it('wires each cell to its handler', () => {
    const { getByTitle } = renderControls(handlers);
    fireEvent.click(getByTitle(coach.firstMove));
    fireEvent.click(getByTitle(coach.previousMove));
    fireEvent.click(getByTitle(coach.nextMove));
    fireEvent.click(getByTitle(coach.lastMove));
    fireEvent.click(getByTitle(coach.flipBoard));
    expect(handlers.onFirst).toHaveBeenCalledTimes(1);
    expect(handlers.onPrev).toHaveBeenCalledTimes(1);
    expect(handlers.onNext).toHaveBeenCalledTimes(1);
    expect(handlers.onLast).toHaveBeenCalledTimes(1);
    expect(handlers.onFlip).toHaveBeenCalledTimes(1);
  });

  it('renders a single bar wrapping the 6 cells', () => {
    const { container } = renderControls(handlers, 480);
    const bar = container.firstElementChild as HTMLElement;
    // One flush strip; every direct child is a titled nav cell.
    const cells = bar.querySelectorAll('[title]');
    expect(cells).toHaveLength(6);
    expect(bar.children).toHaveLength(6);
  });

  it('uses no text labels and no rounded pills (icons only)', () => {
    const { container } = renderControls(handlers);
    // Every cell contains an SVG glyph and no visible text.
    const cells = container.querySelectorAll('[title]');
    cells.forEach((cell) => {
      expect(cell.querySelector('svg')).not.toBeNull();
      expect(cell.textContent).toBe('');
    });
    // No Tailwind pill classes carried over from the old implementation.
    expect(container.innerHTML).not.toContain('rounded');
  });
});

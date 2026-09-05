/**
 * @vitest-environment jsdom
 *
 * GameDock is the chess.com-style bottom action bar: Menu · Resign · Hint ·
 * Take back. The Menu opens a bottom sheet (Flip board, New game, color line);
 * Resign is gated behind a confirm dialog. Once the game ends, Hint/Take back/
 * Resign are disabled and a prominent New game button is shown.
 */
import { describe, it, expect, afterEach, vi } from 'vitest';
import React from 'react';
import { cleanup, render, fireEvent, waitFor } from '@testing-library/react';

vi.mock('next-intl', () => ({
  useTranslations: () => {
    const t = (key: string) => `bots.${key}`;
    t.has = () => false;
    return t;
  },
}));

vi.mock('next/font/google', () => ({
  Fredoka: () => ({ style: { fontFamily: 'Fredoka' }, variable: 'fredoka', className: 'fredoka' }),
  Nunito: () => ({ style: { fontFamily: 'Nunito' }, variable: 'nunito', className: 'nunito' }),
}));

import GameDock from '../GameDock';
import type { Bot, BotTier } from '@/data/bots';

const makeBot = (tier: BotTier = 'beginner'): Bot => ({
  id: `test-${tier}`,
  name: 'Testy',
  rating: 1500,
  tier,
  description: `A ${tier} test bot`,
  playStyle: 'Solid',
  avatar: '/bots/test.webp',
  emoji: '🤖',
});

const baseProps = {
  bot: makeBot(),
  playerColor: 'w' as const,
  gameResult: null,
  onNewGame: () => {},
  onResign: () => {},
};

afterEach(cleanup);

describe('GameDock rendering', () => {
  it('renders the four action buttons while the game is in progress', () => {
    const { getByTestId } = render(<GameDock {...baseProps} />);
    expect(getByTestId('game-menu-button')).not.toBeNull();
    expect(getByTestId('resign-button')).not.toBeNull();
    expect(getByTestId('hint-button')).not.toBeNull();
    expect(getByTestId('takeback-button')).not.toBeNull();
  });

  it('disables Hint and Take back unless explicitly enabled', () => {
    const { getByTestId } = render(<GameDock {...baseProps} />);
    expect((getByTestId('hint-button') as HTMLButtonElement).disabled).toBe(true);
    expect((getByTestId('takeback-button') as HTMLButtonElement).disabled).toBe(true);
  });

  it('enables Hint and Take back when the flags are set', () => {
    const { getByTestId } = render(
      <GameDock {...baseProps} canHint canTakeback onHint={() => {}} onTakeback={() => {}} />,
    );
    expect((getByTestId('hint-button') as HTMLButtonElement).disabled).toBe(false);
    expect((getByTestId('takeback-button') as HTMLButtonElement).disabled).toBe(false);
  });

  it('shows the result and a prominent New game once the game has ended', () => {
    const { getByTestId, container } = render(
      <GameDock {...baseProps} gameResult="White wins by checkmate!" canHint canTakeback />,
    );
    expect(getByTestId('new-game-button')).not.toBeNull();
    expect(container.textContent).toContain('White wins by checkmate!');
    // Hint / Take back / Resign are disabled at game end.
    expect((getByTestId('hint-button') as HTMLButtonElement).disabled).toBe(true);
    expect((getByTestId('takeback-button') as HTMLButtonElement).disabled).toBe(true);
    expect((getByTestId('resign-button') as HTMLButtonElement).disabled).toBe(true);
  });
});

describe('GameDock hint / take back', () => {
  it('fires onHint and onTakeback when enabled', () => {
    const onHint = vi.fn();
    const onTakeback = vi.fn();
    const { getByTestId } = render(
      <GameDock {...baseProps} canHint canTakeback onHint={onHint} onTakeback={onTakeback} />,
    );
    fireEvent.click(getByTestId('hint-button'));
    fireEvent.click(getByTestId('takeback-button'));
    expect(onHint).toHaveBeenCalledTimes(1);
    expect(onTakeback).toHaveBeenCalledTimes(1);
  });
});

describe('GameDock menu sheet', () => {
  it('opens the menu and exposes Flip board + New game', async () => {
    const onFlip = vi.fn();
    const onNewGame = vi.fn();
    const { getByTestId, queryByTestId } = render(
      <GameDock {...baseProps} onFlip={onFlip} onNewGame={onNewGame} />,
    );

    // Menu closed → items not present.
    expect(queryByTestId('flip-board-button')).toBeNull();

    fireEvent.click(getByTestId('game-menu-button'));
    await waitFor(() => expect(getByTestId('flip-board-button')).not.toBeNull());

    fireEvent.click(getByTestId('flip-board-button'));
    expect(onFlip).toHaveBeenCalledTimes(1);
  });

  it('New game in the menu triggers onNewGame', async () => {
    const onNewGame = vi.fn();
    const { getByTestId } = render(<GameDock {...baseProps} onNewGame={onNewGame} />);
    fireEvent.click(getByTestId('game-menu-button'));
    await waitFor(() => expect(getByTestId('new-game-button')).not.toBeNull());
    fireEvent.click(getByTestId('new-game-button'));
    expect(onNewGame).toHaveBeenCalledTimes(1);
  });
});

describe('GameDock resign confirm flow', () => {
  it('does not resign immediately — it opens a confirm dialog first', async () => {
    const onResign = vi.fn();
    const { getByTestId, queryByTestId } = render(<GameDock {...baseProps} onResign={onResign} />);

    expect(queryByTestId('resign-confirm')).toBeNull();

    fireEvent.click(getByTestId('resign-button'));
    await waitFor(() => expect(getByTestId('resign-confirm')).not.toBeNull());
    expect(onResign).not.toHaveBeenCalled();
  });

  it('keeps the game running when the player cancels', async () => {
    const onResign = vi.fn();
    const { getByTestId, queryByTestId } = render(<GameDock {...baseProps} onResign={onResign} />);

    fireEvent.click(getByTestId('resign-button'));
    await waitFor(() => expect(getByTestId('resign-cancel')).not.toBeNull());
    fireEvent.click(getByTestId('resign-cancel'));

    expect(onResign).not.toHaveBeenCalled();
    await waitFor(() => expect(queryByTestId('resign-confirm')).toBeNull());
    expect(getByTestId('resign-button')).not.toBeNull();
  });

  it('ends the game as a loss when the player confirms', async () => {
    const onResign = vi.fn();
    const { getByTestId } = render(<GameDock {...baseProps} onResign={onResign} />);

    fireEvent.click(getByTestId('resign-button'));
    await waitFor(() => expect(getByTestId('resign-confirm')).not.toBeNull());
    fireEvent.click(getByTestId('resign-confirm'));

    expect(onResign).toHaveBeenCalledTimes(1);
  });
});

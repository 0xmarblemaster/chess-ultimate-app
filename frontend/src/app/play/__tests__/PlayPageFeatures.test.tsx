/**
 * @vitest-environment jsdom
 *
 * PlayPage in-game features (chess.com redesign): Hint draws an engine arrow,
 * Take back restores the previous position and cancels a pending bot move, Flip
 * board toggles orientation, the mobile app chrome is hidden while a game is
 * active, and the floating back button never overlaps the header. Child
 * components/engines are stubbed so the test targets PlayPage's own logic.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import React from 'react';
import { cleanup, render, fireEvent, act } from '@testing-library/react';
import { Chess } from 'chess.js';

const START_FEN = new Chess().fen();

const { evaluatePositionMock, getMoveMock, setChromeHiddenMock, boardProps, dockProps } =
  vi.hoisted(() => ({
    evaluatePositionMock: vi.fn(),
    getMoveMock: vi.fn(),
    setChromeHiddenMock: vi.fn(),
    boardProps: {} as { fen?: string; orientation?: string; hintMove?: [string, string] },
    dockProps: {} as { canHint?: boolean; canTakeback?: boolean },
  }));

vi.mock('next/font/google', () => ({
  Fredoka: () => ({ style: { fontFamily: 'Fredoka' }, variable: 'fredoka', className: 'fredoka' }),
  Nunito: () => ({ style: { fontFamily: 'Nunito' }, variable: 'nunito', className: 'nunito' }),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => {
    const t = (k: string) => k;
    (t as any).has = () => false;
    return t;
  },
}));

vi.mock('@/lib/analytics/events', () => ({
  ANALYTICS_EVENTS: { PLAY_ENGINE_WAIT: 'play_engine_wait' },
  track: vi.fn(),
}));

vi.mock('@/components/ChromeVisibilityContext', () => ({
  useChromeVisibility: () => ({ setChromeHidden: setChromeHiddenMock }),
}));

vi.mock('@/hooks/useMaia', () => ({
  useMaia: () => ({
    status: 'ready',
    error: null,
    evaluatePosition: evaluatePositionMock,
    downloadModel: vi.fn(),
    usingServerFallback: false,
  }),
}));

vi.mock('@/hooks/useStockfishPlay', () => ({
  useStockfishPlay: () => ({ status: 'ready', error: null, getMove: getMoveMock }),
}));

vi.mock('@/components/play/BotGrid', async () => {
  const actual: any = await vi.importActual('@/data/bots');
  const bot = actual.getBotById('luna-1100');
  return {
    default: ({ onSelectBot }: any) =>
      React.createElement(
        'button',
        { 'data-testid': 'pick-bot', onClick: () => onSelectBot(bot) },
        'pick',
      ),
  };
});

vi.mock('@/components/play/GameSetup', () => ({
  default: ({ onPlay, onColorChange }: any) =>
    React.createElement('div', { 'data-testid': 'setup-screen' }, [
      React.createElement('button', { key: 'p', 'data-testid': 'play', onClick: onPlay }, 'play'),
      React.createElement(
        'button',
        { key: 'b', 'data-testid': 'color-black', onClick: () => onColorChange('black') },
        'black',
      ),
    ]),
}));

vi.mock('@/components/play/PlayFriendCard', () => ({ default: () => null }));
vi.mock('@/components/play/GameEndModal', () => ({ default: () => null }));

// Dock stub exposes the feature handlers + availability flags.
vi.mock('@/components/play/GameDock', () => ({
  default: (props: any) => {
    dockProps.canHint = props.canHint;
    dockProps.canTakeback = props.canTakeback;
    return React.createElement('div', null, [
      React.createElement('button', { key: 'h', 'data-testid': 'hint', onClick: props.onHint }, 'hint'),
      React.createElement('button', { key: 't', 'data-testid': 'takeback', onClick: props.onTakeback }, 'takeback'),
      React.createElement('button', { key: 'f', 'data-testid': 'flip', onClick: props.onFlip }, 'flip'),
      React.createElement('button', { key: 'n', 'data-testid': 'new-game', onClick: props.onNewGame }, 'new'),
    ]);
  },
}));

// Board stub records the props PlayPage feeds it and can fire a player move.
vi.mock('@/components/chess/ChessgroundBoard', () => ({
  default: (props: any) => {
    boardProps.fen = props.fen;
    boardProps.orientation = props.orientation;
    boardProps.hintMove = props.hintMove;
    return React.createElement(
      'button',
      { 'data-testid': 'board-move', onClick: () => props.onMove('e2', 'e4') },
      'move',
    );
  },
}));

import PlayPage from '../page';

describe('PlayPage — chrome hiding', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/play');
    setChromeHiddenMock.mockClear();
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('hides the chrome while playing and restores it when leaving the game', () => {
    const { getByTestId } = render(<PlayPage />);

    fireEvent.click(getByTestId('pick-bot')); // setup — not in game
    fireEvent.click(getByTestId('play')); // playing — chrome hidden
    expect(setChromeHiddenMock).toHaveBeenCalledWith(true);

    setChromeHiddenMock.mockClear();
    act(() => {
      window.history.replaceState(null, '', '/play?phase=setup&bot=luna-1100');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    expect(setChromeHiddenMock).toHaveBeenLastCalledWith(false);
  });
});

describe('PlayPage — hint', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/play');
    getMoveMock.mockReset().mockResolvedValue('e2e4');
    boardProps.hintMove = undefined;
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('asks the engine and draws the returned move as a board arrow', async () => {
    const { getByTestId } = render(<PlayPage />);
    fireEvent.click(getByTestId('pick-bot'));
    fireEvent.click(getByTestId('play')); // player is white → their move

    expect(dockProps.canHint).toBe(true);

    await act(async () => {
      fireEvent.click(getByTestId('hint'));
    });

    expect(getMoveMock).toHaveBeenCalledWith(START_FEN, 2600);
    expect(boardProps.hintMove).toEqual(['e2', 'e4']);
  });
});

describe('PlayPage — take back', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/play');
    evaluatePositionMock.mockReset().mockResolvedValue({ policy: { e7e5: 1 } });
    boardProps.fen = undefined;
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('restores the previous position and cancels the pending bot move', async () => {
    vi.useFakeTimers();
    const { getByTestId } = render(<PlayPage />);

    act(() => { fireEvent.click(getByTestId('pick-bot')); });
    act(() => { fireEvent.click(getByTestId('play')); }); // white
    act(() => { fireEvent.click(getByTestId('board-move')); }); // player plays e2e4
    expect(boardProps.fen).not.toBe(START_FEN);
    expect(dockProps.canTakeback).toBe(true);

    act(() => { fireEvent.click(getByTestId('takeback')); });
    expect(boardProps.fen).toBe(START_FEN);

    // The bot's scheduled reply must never fire after a take back.
    await act(async () => { vi.advanceTimersByTime(1000); });
    expect(evaluatePositionMock).not.toHaveBeenCalled();
  });

  it('disables take back until the player has moved', () => {
    const { getByTestId } = render(<PlayPage />);
    fireEvent.click(getByTestId('pick-bot'));
    fireEvent.click(getByTestId('play'));
    expect(dockProps.canTakeback).toBe(false);
  });
});

describe('PlayPage — flip board', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/play');
    boardProps.orientation = undefined;
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('toggles board orientation, starting from the player color', () => {
    const { getByTestId } = render(<PlayPage />);
    fireEvent.click(getByTestId('pick-bot'));
    fireEvent.click(getByTestId('play')); // white
    expect(boardProps.orientation).toBe('white');

    fireEvent.click(getByTestId('flip'));
    expect(boardProps.orientation).toBe('black');

    fireEvent.click(getByTestId('flip'));
    expect(boardProps.orientation).toBe('white');
  });
});

describe('PlayPage — back button layer', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/play');
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('keeps the back button alone in its own absolute layer, never overlapping the header', () => {
    const { getByTestId } = render(<PlayPage />);
    fireEvent.click(getByTestId('pick-bot'));
    fireEvent.click(getByTestId('play'));

    const gameScreen = getByTestId('game-screen');
    const back = getByTestId('play-back-button');
    const header = getByTestId('game-header');

    // Exactly one back button, taken out of flow, in its own top-level layer.
    expect(gameScreen.querySelectorAll('[data-testid="play-back-button"]').length).toBe(1);
    expect(back.parentElement).toBe(gameScreen);
    expect(getComputedStyle(back).position).toBe('absolute');

    // The header lives in a separate subtree — no ancestor/overlap relationship.
    expect(header.parentElement).not.toBe(gameScreen);
    expect(back.contains(header)).toBe(false);
    expect(header.contains(back)).toBe(false);
  });
});

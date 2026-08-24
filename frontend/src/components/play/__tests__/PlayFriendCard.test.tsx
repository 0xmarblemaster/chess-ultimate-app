/**
 * @vitest-environment jsdom
 *
 * PlayFriendCard (phase 6): all user-visible copy is localized via the shared
 * `bots.play.*` catalog. This test backs next-intl with the real English
 * messages so the assertions prove the keys resolve to real localized strings
 * (not just echoed key names). It also covers the `horizontal` variant used on
 * the play page (desktop bar + mobile collapse behaviour).
 */
import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import React from 'react';
import { cleanup, render, fireEvent } from '@testing-library/react';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Back next-intl with the real `bots` catalog so `playText` resolves to the
// actual English strings.
vi.mock('next-intl', async () => {
  const en = (await import('../../../../messages/en.json')).default as Record<string, unknown>;
  const bots = (en as { bots: Record<string, unknown> }).bots;
  const walk = (key: string): unknown =>
    key.split('.').reduce<unknown>((cur, p) => (cur as Record<string, unknown> | undefined)?.[p], bots);
  const useTranslations = () => {
    const t = (key: string, values?: Record<string, string | number>) => {
      const v = walk(key);
      return typeof v === 'string'
        ? v.replace(/\{(\w+)\}/g, (_m, k) => String(values?.[k] ?? ''))
        : key;
    };
    (t as unknown as { has: (k: string) => boolean }).has = (key: string) =>
      typeof walk(key) === 'string';
    return t;
  };
  return { useTranslations };
});

import PlayFriendCard from '../PlayFriendCard';

// MUI useMediaQuery reads window.matchMedia; force a desktop or mobile result.
function setMatchMedia(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

afterEach(cleanup);

describe('PlayFriendCard localization (card variant)', () => {
  it('renders the localized subtitle, labels and button — no hard-coded English left', () => {
    const { getByTestId, getByText } = render(<PlayFriendCard />);

    expect(getByTestId('play-friend-card')).toBeTruthy();
    // Localized copy from bots.play.*
    expect(
      getByText('Create a game and share the link — it opens live for both of you.'),
    ).toBeTruthy();
    expect(getByText('TIME CONTROL')).toBeTruthy();
    expect(getByText('YOUR COLOR')).toBeTruthy();
    expect(getByText('Create game link')).toBeTruthy();
    // Untimed + color options come from the shared catalog.
    expect(getByText('Untimed')).toBeTruthy();
    expect(getByText('White')).toBeTruthy();
    expect(getByText('Black')).toBeTruthy();
    expect(getByText('Random')).toBeTruthy();
  });

  it('does not render its own "Play a friend" title (that lives on the section header)', () => {
    const { queryByText } = render(<PlayFriendCard />);
    expect(queryByText('Play a friend')).toBeNull();
  });
});

describe('PlayFriendCard horizontal variant — desktop', () => {
  beforeEach(() => setMatchMedia(false)); // not mobile

  it('renders a full-width bar with its own title, subtitle, both controls and the button', () => {
    const { getByTestId, getByText, queryByTestId } = render(
      <PlayFriendCard variant="horizontal" />,
    );

    expect(getByTestId('play-friend-bar')).toBeTruthy();
    // The bar owns the title (no section header sits above it anymore).
    expect(getByText('Play a friend')).toBeTruthy();
    expect(
      getByText('Create a game and share the link — it opens live for both of you.'),
    ).toBeTruthy();
    expect(getByText('TIME CONTROL')).toBeTruthy();
    expect(getByText('YOUR COLOR')).toBeTruthy();
    expect(getByTestId('create-challenge')).toBeTruthy();
    // No mobile collapse toggle on desktop.
    expect(queryByTestId('play-friend-toggle')).toBeNull();
  });
});

describe('PlayFriendCard horizontal variant — mobile', () => {
  beforeEach(() => setMatchMedia(true)); // mobile

  it('starts expanded: shows the option controls + full create button, no summary', () => {
    const { getByTestId, getByText, queryByText } = render(
      <PlayFriendCard variant="horizontal" />,
    );

    const toggle = getByTestId('play-friend-toggle');
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    // The option controls are visible on mount.
    expect(getByText('TIME CONTROL')).toBeTruthy();
    expect(getByText('YOUR COLOR')).toBeTruthy();
    // The full CTA label is shown when expanded.
    expect(getByTestId('create-challenge')).toBeTruthy();
    expect(getByText('Create game link')).toBeTruthy();
    // The collapsed-only summary is not shown while expanded.
    expect(queryByText('5 + 0 · Random')).toBeNull();
  });

  it('collapses to a summary + short create button when the pill is tapped', () => {
    const { getByTestId, getByText, queryByText } = render(
      <PlayFriendCard variant="horizontal" />,
    );

    expect(getByText('TIME CONTROL')).toBeTruthy();
    fireEvent.click(getByTestId('play-friend-toggle'));

    expect(getByTestId('play-friend-toggle').getAttribute('aria-expanded')).toBe('false');
    // Options hidden, summary of the defaults shown instead.
    expect(queryByText('TIME CONTROL')).toBeNull();
    expect(queryByText('YOUR COLOR')).toBeNull();
    expect(getByText('5 + 0 · Random')).toBeTruthy();
    // The collapsed pill uses the short CTA label (locale-proof overlap fix).
    expect(getByText('Create')).toBeTruthy();
    expect(queryByText('Create game link')).toBeNull();
  });
});

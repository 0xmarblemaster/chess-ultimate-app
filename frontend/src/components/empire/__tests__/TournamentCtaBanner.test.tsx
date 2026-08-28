/**
 * @vitest-environment jsdom
 *
 * Tests for the Empire tournament registration CTA banner:
 *   - renders the localized title / subtitle / button copy
 *   - the whole card links to /tournaments
 *   - carries the expected data-testids
 */
import { describe, it, expect, afterEach, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

import TournamentCtaBanner from '../TournamentCtaBanner';

afterEach(() => {
  cleanup();
});

describe('TournamentCtaBanner', () => {
  it('renders the title, subtitle, and button copy', () => {
    const { getByTestId } = render(<TournamentCtaBanner />);
    const root = getByTestId('empire-tournament-cta');
    expect(root.textContent).toContain('tournamentCtaTitle');
    expect(root.textContent).toContain('tournamentCtaSubtitle');
    expect(getByTestId('empire-tournament-cta-button').textContent).toContain(
      'tournamentCtaButton',
    );
  });

  it('links the whole card to /tournaments', () => {
    const { getByTestId } = render(<TournamentCtaBanner />);
    const root = getByTestId('empire-tournament-cta');
    expect(root.tagName).toBe('A');
    expect(root.getAttribute('href')).toBe('/tournaments');
  });

  it('passes through a className', () => {
    const { getByTestId } = render(<TournamentCtaBanner className="mt-4" />);
    expect(getByTestId('empire-tournament-cta').className).toContain('mt-4');
  });
});

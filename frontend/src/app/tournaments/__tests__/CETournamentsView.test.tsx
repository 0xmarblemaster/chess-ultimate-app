/**
 * @vitest-environment jsdom
 *
 * Localization tests for CETournamentsView. Renders under a real
 * NextIntlClientProvider seeded with the actual message catalogs and asserts
 * the view shows translated copy (header, banners, empty state, card labels,
 * status badges, actions) rather than hardcoded English — across en/ru/kz and
 * every visitor state. Also checks locale-driven fee/date formatting.
 */
import { describe, it, expect, afterEach } from 'vitest';
import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';

import en from '../../../../messages/en.json';
import ru from '../../../../messages/ru.json';
import kz from '../../../../messages/kz.json';
import CETournamentsView, {
  type CETournamentCard,
  type CEViewer,
} from '../CETournamentsView';

const CATALOGS = { en, ru, kz } as const;

function renderView(
  viewer: CEViewer,
  tournaments: CETournamentCard[],
  locale: keyof typeof CATALOGS = 'en',
) {
  return render(
    <NextIntlClientProvider
      locale={locale}
      messages={CATALOGS[locale] as Record<string, unknown>}
    >
      <CETournamentsView tournaments={tournaments} viewer={viewer} />
    </NextIntlClientProvider>,
  );
}

const sampleCard: CETournamentCard = {
  id: 't-1',
  name: 'Spring Open',
  info: null,
  tournament_date: '2026-03-14',
  start_time: '10:30:00',
  time_format: 'Blitz 5+3',
  registration_fee: 0,
  rounds: 7,
  capacity: 20,
  status: 'open',
  registered_count: 5,
  branch_name: null,
  registration_id: null,
};

afterEach(() => cleanup());

describe('CETournamentsView localization', () => {
  it('renders the English header, subtitle and empty state', () => {
    renderView({ state: 'logged_out' }, []);
    expect(screen.getByText(en.ceTournaments.title)).toBeTruthy();
    expect(screen.getByText(en.ceTournaments.subtitle)).toBeTruthy();
    expect(screen.getByText(en.ceTournaments.empty)).toBeTruthy();
  });

  it('renders the Russian header when locale is ru', () => {
    renderView({ state: 'logged_out' }, [], 'ru');
    expect(screen.getByText(ru.ceTournaments.title)).toBeTruthy();
    expect(screen.getByText(ru.ceTournaments.subtitle)).toBeTruthy();
    // The English original must not leak through.
    expect(screen.queryByText('Tournaments')).toBeNull();
  });

  it('renders the Kazakh header when locale is kz', () => {
    renderView({ state: 'logged_out' }, [], 'kz');
    expect(screen.getByText(kz.ceTournaments.title)).toBeTruthy();
    expect(screen.getByText(kz.ceTournaments.subtitle)).toBeTruthy();
  });

  it('shows the logged-out banner + sign-in link', () => {
    renderView({ state: 'logged_out' }, [sampleCard]);
    expect(
      screen.getByText(en.ceTournaments.loggedOutBanner, { exact: false }),
    ).toBeTruthy();
    expect(screen.getByText(en.ceTournaments.signInToRegister)).toBeTruthy();
  });

  it('shows the unverified banner + verify link', () => {
    renderView({ state: 'unverified' }, [sampleCard]);
    expect(
      screen.getByText(en.ceTournaments.unverifiedBanner, { exact: false }),
    ).toBeTruthy();
    expect(screen.getByText(en.ceTournaments.verifyMembership)).toBeTruthy();
  });

  it('renders card labels, open status and register action (verified)', () => {
    renderView({ state: 'verified', studentName: 'Aidos' }, [sampleCard]);
    expect(screen.getByText(en.ceTournaments.date)).toBeTruthy();
    expect(screen.getByText(en.ceTournaments.rounds)).toBeTruthy();
    expect(screen.getByText(en.ceTournaments.entryFee)).toBeTruthy();
    expect(screen.getByText(en.ceTournaments.players)).toBeTruthy();
    expect(screen.getByText(en.ceTournaments.statusOpen)).toBeTruthy();
    expect(
      screen.getByRole('button', { name: en.ceTournaments.register }),
    ).toBeTruthy();
  });

  it('localizes the free entry fee per locale', () => {
    renderView({ state: 'verified', studentName: null }, [sampleCard]);
    expect(screen.getByText(en.ceTournaments.free)).toBeTruthy();
    cleanup();
    renderView({ state: 'verified', studentName: null }, [sampleCard], 'ru');
    expect(screen.getByText(ru.ceTournaments.free)).toBeTruthy();
  });

  it('formats the date using the app locale, not the browser', () => {
    renderView({ state: 'verified', studentName: null }, [sampleCard], 'ru');
    // ru-RU month names are Cyrillic; en-US would render "Mar".
    const dateText = screen.getByText(ru.ceTournaments.date).nextElementSibling
      ?.textContent;
    expect(dateText).toBeTruthy();
    expect(/[а-яА-Я]/.test(dateText ?? '')).toBe(true);
  });

  it('shows the "full" status and disabled action when at capacity', () => {
    const full: CETournamentCard = {
      ...sampleCard,
      registered_count: 20,
      capacity: 20,
    };
    renderView({ state: 'verified', studentName: 'Aidos' }, [full]);
    expect(screen.getByText(en.ceTournaments.statusFull)).toBeTruthy();
    expect(
      screen.getByRole('button', { name: en.ceTournaments.tournamentFull }),
    ).toBeTruthy();
  });

  it('shows registered state + cancel action for an already-registered member', () => {
    const registered: CETournamentCard = {
      ...sampleCard,
      registration_id: 'reg-1',
    };
    renderView({ state: 'verified', studentName: 'Aidos' }, [registered]);
    expect(screen.getByText(en.ceTournaments.registered)).toBeTruthy();
    expect(
      screen.getByRole('button', {
        name: en.ceTournaments.cancelRegistration,
      }),
    ).toBeTruthy();
  });
});

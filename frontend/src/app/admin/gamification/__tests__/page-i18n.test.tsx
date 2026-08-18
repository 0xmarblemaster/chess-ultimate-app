/**
 * @vitest-environment jsdom
 *
 * Per-locale render smoke test for the admin Gamification page (§14.1).
 * Renders the page under a real NextIntlClientProvider for en / ru / kz and
 * asserts the localized title + tab labels come from the message files (no
 * hardcoded English leaks, no missing-key crash).
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';

import en from '../../../../../messages/en.json';
import ru from '../../../../../messages/ru.json';
import kz from '../../../../../messages/kz.json';

vi.mock('@/contexts/OrganizationContext', () => ({
  useOrganization: () => ({ org: { id: 'org-1', slug: 'ce', name: 'CE' } }),
}));

import AdminGamificationPage from '../page';

// The page fires several fetches on mount; return empty payloads so nothing throws.
global.fetch = vi.fn(() =>
  Promise.resolve(new Response(JSON.stringify({}), { status: 200 })),
) as unknown as typeof fetch;

const locales = { en, ru, kz } as const;

afterEach(() => cleanup());

describe('AdminGamificationPage i18n render', () => {
  it.each(Object.entries(locales))('renders localized title + tabs for %s', (locale, messages) => {
    render(
      <NextIntlClientProvider locale={locale} messages={messages as Record<string, unknown>}>
        <AdminGamificationPage />
      </NextIntlClientProvider>,
    );

    const ns = (messages as typeof en).adminGamification;
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(ns.title);
    // All seven tab labels render from the locale's messages.
    for (const key of ['rules', 'ranks', 'items', 'legions', 'seasons', 'coins', 'ops'] as const) {
      expect(screen.getByText(ns.tabs[key])).toBeTruthy();
    }
  });
});

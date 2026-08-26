/**
 * @vitest-environment jsdom
 *
 * Tenant routing test for /tournaments/page.tsx. The apex host (no CE headers)
 * renders the existing calendar; the chess-empire tenant host (`x-org-id` +
 * `x-org-slug === 'chess-empire'`) renders the CE registration-gate view. Both
 * child views are mocked to identifiable markers so only the routing decision
 * is under test.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';

const headersStore: { current: Record<string, string> } = { current: {} };
vi.mock('next/headers', () => ({
  headers: async () => ({
    get: (name: string) => headersStore.current[name.toLowerCase()] ?? null,
  }),
}));

vi.mock('../ChessEmpireTournaments', () => ({
  __esModule: true,
  default: () => <div>CE REGISTRATION VIEW</div>,
}));
vi.mock('../TournamentsCalendar', () => ({
  __esModule: true,
  default: () => <div>APEX CALENDAR</div>,
}));

import TournamentsPage from '../page';

beforeEach(() => {
  headersStore.current = {};
  cleanup();
});

describe('/tournaments tenant routing', () => {
  it('renders the apex calendar when there is no CE tenant header', async () => {
    const node = await TournamentsPage();
    render(node);
    expect(screen.getByText('APEX CALENDAR')).toBeTruthy();
    expect(screen.queryByText('CE REGISTRATION VIEW')).toBeNull();
  });

  it('renders the CE view on the chess-empire tenant host', async () => {
    headersStore.current = {
      'x-org-id': 'org-ce',
      'x-org-slug': 'chess-empire',
    };
    const node = await TournamentsPage();
    render(node);
    expect(screen.getByText('CE REGISTRATION VIEW')).toBeTruthy();
    expect(screen.queryByText('APEX CALENDAR')).toBeNull();
  });

  it('renders the calendar for a non-CE tenant slug', async () => {
    headersStore.current = { 'x-org-id': 'org-x', 'x-org-slug': 'almatychess' };
    const node = await TournamentsPage();
    render(node);
    expect(screen.getByText('APEX CALENDAR')).toBeTruthy();
  });
});

/**
 * @vitest-environment jsdom
 *
 * Server-component tests for /register/page.tsx. Mocks the Supabase admin
 * client with a scripted row set so we can exercise branch/online rendering,
 * newest-token-per-branch dedupe, revoked/expired filtering, and the empty
 * state.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { cleanup, render } from '@testing-library/react';

interface ScriptedResponse {
  data?: unknown;
  error?: unknown;
}

const tokenScript: { current: ScriptedResponse } = { current: { data: [], error: null } };
const headerStore: { current: Record<string, string | null> } = {
  current: { 'x-org-id': 'org-1' },
};

vi.mock('@/lib/supabase-admin', () => ({
  supabaseAdmin: {
    from: () => {
      const chain: Record<string, unknown> = {
        select: () => chain,
        eq: () => Promise.resolve(tokenScript.current),
      };
      return chain;
    },
  },
}));

vi.mock('next/headers', () => ({
  headers: async () => ({
    get: (key: string) => headerStore.current[key] ?? null,
  }),
}));

vi.mock('next-intl/server', () => ({
  getTranslations: async () => (key: string) => key,
}));

// RegisterPicker's client hooks.
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('@/contexts/OrganizationContext', () => ({
  useBranding: () => ({ name: 'Chess Empire', logoUrl: null, contactEmail: 'help@ce.io' }),
}));

vi.mock('next/image', () => ({
  default: ({ alt, src }: { alt: string; src: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt={alt} src={src} />
  ),
}));

import RegisterPage from '../page';

const iso = (d: string) => new Date(d).toISOString();

describe('/register server page', () => {
  beforeEach(() => {
    tokenScript.current = { data: [], error: null };
    headerStore.current = { 'x-org-id': 'org-1' };
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders a card per branch plus the highlighted online option', async () => {
    tokenScript.current = {
      data: [
        {
          token: 't-branch-1',
          external_branch_id: 'b1',
          branch_name: 'Debut',
          kind: 'branch',
          expires_at: null,
          revoked_at: null,
          created_at: iso('2026-01-01'),
        },
        {
          token: 't-branch-2',
          external_branch_id: 'b2',
          branch_name: 'Almaty',
          kind: 'branch',
          expires_at: null,
          revoked_at: null,
          created_at: iso('2026-01-02'),
        },
        {
          token: 't-online',
          external_branch_id: 'online',
          branch_name: 'Online',
          kind: 'online',
          expires_at: null,
          revoked_at: null,
          created_at: iso('2026-01-03'),
        },
      ],
      error: null,
    };

    const ui = await RegisterPage();
    const { container, getByText } = render(ui);

    expect(getByText('Debut')).toBeTruthy();
    expect(getByText('Almaty')).toBeTruthy();
    // Online highlighted card renders its label.
    expect(getByText('online.title')).toBeTruthy();

    const hrefs = Array.from(container.querySelectorAll('a')).map((a) =>
      a.getAttribute('href'),
    );
    expect(hrefs).toContain('/welcome/t-branch-1');
    expect(hrefs).toContain('/welcome/t-branch-2');
    expect(hrefs).toContain('/welcome/t-online');
  });

  it('dedupes to the newest token per branch', async () => {
    tokenScript.current = {
      data: [
        {
          token: 'stale',
          external_branch_id: 'b1',
          branch_name: 'Debut',
          kind: 'branch',
          expires_at: null,
          revoked_at: null,
          created_at: iso('2026-01-01'),
        },
        {
          token: 'fresh',
          external_branch_id: 'b1',
          branch_name: 'Debut',
          kind: 'branch',
          expires_at: null,
          revoked_at: null,
          created_at: iso('2026-06-01'),
        },
      ],
      error: null,
    };

    const ui = await RegisterPage();
    const { container } = render(ui);

    const branchLinks = Array.from(container.querySelectorAll('a')).map((a) =>
      a.getAttribute('href'),
    );
    expect(branchLinks).toContain('/welcome/fresh');
    expect(branchLinks).not.toContain('/welcome/stale');
    // Exactly one branch card for b1.
    expect(branchLinks.filter((h) => h?.startsWith('/welcome/')).length).toBe(1);
  });

  it('filters out revoked and expired tokens', async () => {
    tokenScript.current = {
      data: [
        {
          token: 'revoked',
          external_branch_id: 'b1',
          branch_name: 'Revoked',
          kind: 'branch',
          expires_at: null,
          revoked_at: iso('2026-01-01'),
          created_at: iso('2026-05-01'),
        },
        {
          token: 'expired',
          external_branch_id: 'b2',
          branch_name: 'Expired',
          kind: 'branch',
          expires_at: iso('2020-01-01'),
          revoked_at: null,
          created_at: iso('2026-05-01'),
        },
        {
          token: 'good',
          external_branch_id: 'b3',
          branch_name: 'Live',
          kind: 'branch',
          expires_at: null,
          revoked_at: null,
          created_at: iso('2026-05-01'),
        },
      ],
      error: null,
    };

    const ui = await RegisterPage();
    const { container, queryByText } = render(ui);

    expect(queryByText('Live')).toBeTruthy();
    expect(queryByText('Revoked')).toBeNull();
    expect(queryByText('Expired')).toBeNull();

    const hrefs = Array.from(container.querySelectorAll('a')).map((a) =>
      a.getAttribute('href'),
    );
    expect(hrefs).toContain('/welcome/good');
    expect(hrefs).not.toContain('/welcome/revoked');
    expect(hrefs).not.toContain('/welcome/expired');
  });

  it('renders the empty state with contact info when no active tokens exist', async () => {
    tokenScript.current = { data: [], error: null };

    const ui = await RegisterPage();
    const { container } = render(ui);

    expect(container.textContent).toContain('emptyTitle');
    expect(container.textContent).toContain('emptyBody');
    // Contact email surfaced as a mailto link.
    const mailto = container.querySelector('a[href^="mailto:"]');
    expect(mailto?.getAttribute('href')).toBe('mailto:help@ce.io');
  });

  it('renders the empty state on the apex host (no x-org-id)', async () => {
    headerStore.current = {};
    tokenScript.current = {
      data: [
        {
          token: 't-branch-1',
          external_branch_id: 'b1',
          branch_name: 'Debut',
          kind: 'branch',
          expires_at: null,
          revoked_at: null,
          created_at: iso('2026-01-01'),
        },
      ],
      error: null,
    };

    const ui = await RegisterPage();
    const { container, queryByText } = render(ui);

    // Never queries Supabase without an org — falls straight to empty state.
    expect(queryByText('Debut')).toBeNull();
    expect(container.textContent).toContain('emptyTitle');
  });
});

/**
 * @vitest-environment jsdom
 *
 * Client tests for OnlineWelcomeFlow. Online invite tokens skip the roster
 * search AND the old name interstitial: on mount the component POSTs
 * `{ branchToken }` to `/api/chess-empire/online/register` and hands off to Clerk
 * sign-up. Covers: auto-register on mount, single call under StrictMode, the
 * signed-out redirect to `/sign-up?invite`, the signed-in `/dashboard` path, and
 * the error + retry branch.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React, { StrictMode } from 'react';
import { act, cleanup, fireEvent, render, waitFor } from '@testing-library/react';

const routerReplace = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: routerReplace, push: vi.fn() }),
}));

const authStore = { isSignedIn: false as boolean };
vi.mock('@clerk/nextjs', () => ({
  useAuth: () => ({ isSignedIn: authStore.isSignedIn }),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock('next/image', () => ({
  default: ({ alt, src }: { alt: string; src: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt={alt} src={src} />
  ),
}));

vi.mock('@/contexts/OrganizationContext', () => ({
  useBranding: () => ({ name: 'Chess Empire', logoUrl: null, primaryColor: '#9333ea' }),
  useOrganization: () => ({ org: null, isWhiteLabel: false }),
}));

const persistWelcomeOnboardingUrl = vi.fn();
const persistBranchWelcomeUrl = vi.fn();
vi.mock('@/lib/invite-storage', () => ({
  persistWelcomeOnboardingUrl: (...a: unknown[]) => persistWelcomeOnboardingUrl(...a),
  persistBranchWelcomeUrl: (...a: unknown[]) => persistBranchWelcomeUrl(...a),
}));

import OnlineWelcomeFlow from '../OnlineWelcomeFlow';

interface MockResponse {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
}

function jsonResponse(body: unknown, status = 200): MockResponse {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

interface FetchCall {
  url: string;
  init?: RequestInit;
}

let fetchCalls: FetchCall[];
let fetchHandler: (call: FetchCall) => Promise<MockResponse>;

beforeEach(() => {
  fetchCalls = [];
  fetchHandler = async () => jsonResponse({ inviteJwt: 'jwt.token.sig' });
  authStore.isSignedIn = false;
  routerReplace.mockReset();
  persistWelcomeOnboardingUrl.mockReset();
  persistBranchWelcomeUrl.mockReset();
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    fetchCalls.push({ url, init });
    return (await fetchHandler({ url, init })) as unknown as Response;
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function registerCalls() {
  return fetchCalls.filter((c) => c.url.includes('/online/register'));
}

describe('OnlineWelcomeFlow', () => {
  it('auto-registers on mount with just the branchToken and redirects to sign-up', async () => {
    render(<OnlineWelcomeFlow branchToken="tok-abc" />);

    await waitFor(() => {
      expect(routerReplace).toHaveBeenCalledWith('/sign-up?invite=jwt.token.sig');
    });

    const calls = registerCalls();
    expect(calls).toHaveLength(1);
    const body = JSON.parse(calls[0].init!.body as string);
    expect(body).toEqual({ branchToken: 'tok-abc' });
    // No name is collected or sent anymore.
    expect(body).not.toHaveProperty('name');
    expect(persistBranchWelcomeUrl).toHaveBeenCalledWith('/welcome/tok-abc');
  });

  it('fires register exactly once under StrictMode (double-invoked effects)', async () => {
    render(
      <StrictMode>
        <OnlineWelcomeFlow branchToken="tok-abc" />
      </StrictMode>,
    );

    await waitFor(() => {
      expect(routerReplace).toHaveBeenCalledWith('/sign-up?invite=jwt.token.sig');
    });
    expect(registerCalls()).toHaveLength(1);
  });

  it('already signed-in: claims server-side and redirects to /dashboard (never /sign-up)', async () => {
    authStore.isSignedIn = true;
    fetchHandler = async (call) => {
      if (call.url.includes('/online/register')) return jsonResponse({ inviteJwt: 'jwt.token.sig' });
      if (call.url.includes('/link/claim')) return jsonResponse({ ok: true, state: 'verified' });
      return jsonResponse({});
    };
    render(<OnlineWelcomeFlow branchToken="tok-abc" />);

    await waitFor(() => {
      const claimCall = fetchCalls.find((c) => c.url.includes('/link/claim'));
      expect(claimCall).toBeDefined();
      expect(JSON.parse(claimCall!.init!.body as string)).toEqual({
        inviteJwt: 'jwt.token.sig',
      });
    });
    await waitFor(() => expect(routerReplace).toHaveBeenCalledWith('/dashboard'));
    expect(
      routerReplace.mock.calls.some(([url]) => String(url).startsWith('/sign-up')),
    ).toBe(false);
  });

  it('shows a generic error with a retry button when register fails, then recovers', async () => {
    fetchHandler = async () => jsonResponse({ error: 'upstream' }, 502);
    const { container, getByRole } = render(<OnlineWelcomeFlow branchToken="tok-abc" />);

    await waitFor(() => expect(container.textContent).toContain('genericError'));
    expect(routerReplace).not.toHaveBeenCalled();
    expect(registerCalls()).toHaveLength(1);

    // Retry succeeds this time.
    fetchHandler = async () => jsonResponse({ inviteJwt: 'jwt.token.sig' });
    await act(async () => {
      fireEvent.click(getByRole('button'));
    });

    await waitFor(() => {
      expect(routerReplace).toHaveBeenCalledWith('/sign-up?invite=jwt.token.sig');
    });
    expect(registerCalls()).toHaveLength(2);
  });
});

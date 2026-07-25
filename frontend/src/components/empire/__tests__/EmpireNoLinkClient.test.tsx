/**
 * @vitest-environment jsdom
 *
 * Behavior tests for the no_link polling client:
 *   - replays a stored invite JWT to /link/claim on mount, refreshing on success
 *   - clears storage only on a signature-class (`invalid`) terminal error
 *   - a terminal 410 (expired beyond grace) shows the expired screen, not the wait
 *   - keeps the stored JWT on an expiry 410 (a manual link may still succeed)
 *   - renders the "reopen" button on the expired screen when a welcome URL exists
 *   - retries the claim + poll on every fresh mount (remount restarts polling)
 *   - polls /link/status and refreshes when the state leaves no_link
 *   - shows the spinner while polling
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup, act } from '@testing-library/react';

const refresh = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh }) }));
vi.mock('next-intl', () => ({ useTranslations: () => (k: string) => k }));

import EmpireNoLinkClient from '../EmpireNoLinkClient';
import {
  CE_INVITE_JWT_STORAGE_KEY as KEY,
  CE_BRANCH_WELCOME_URL_STORAGE_KEY as WELCOME_KEY,
} from '@/lib/invite-storage';

const fetchMock = vi.fn();

function jsonRes(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

const Static = () => <div data-testid="static-message">static</div>;

beforeEach(() => {
  refresh.mockClear();
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  sessionStorage.clear();
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('EmpireNoLinkClient', () => {
  it('shows the setting-up spinner while polling', async () => {
    fetchMock.mockResolvedValue(jsonRes(200, { state: 'no_link' }));
    render(
      <EmpireNoLinkClient>
        <Static />
      </EmpireNoLinkClient>,
    );
    expect(screen.getByTestId('empire-home-nolink-polling')).toBeTruthy();
    expect(screen.getByText('settingUpProfile')).toBeTruthy();
  });

  it('replays a stored JWT to /link/claim and refreshes on success', async () => {
    localStorage.setItem(KEY, 'stored.jwt.tok');
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        String(url).includes('/claim')
          ? jsonRes(200, { ok: true, state: 'verified' })
          : jsonRes(200, { state: 'no_link' }),
      ),
    );

    render(
      <EmpireNoLinkClient>
        <Static />
      </EmpireNoLinkClient>,
    );

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/chess-empire/link/claim',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(localStorage.getItem(KEY)).toBeNull();
    // Refresh + stop → the static child renders.
    await waitFor(() => expect(screen.getByTestId('static-message')).toBeTruthy());
  });

  it('clears storage on a signature-class (invalid) terminal error and keeps polling', async () => {
    localStorage.setItem(KEY, 'bad.sig.tok');
    sessionStorage.setItem(KEY, 'bad.sig.tok');
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        String(url).includes('/claim')
          ? jsonRes(400, { error: 'invalid', terminal: true })
          : jsonRes(200, { state: 'no_link' }),
      ),
    );

    render(
      <EmpireNoLinkClient>
        <Static />
      </EmpireNoLinkClient>,
    );

    await waitFor(() => expect(localStorage.getItem(KEY)).toBeNull());
    expect(sessionStorage.getItem(KEY)).toBeNull();
    expect(refresh).not.toHaveBeenCalled();
    expect(screen.getByTestId('empire-home-nolink-polling')).toBeTruthy();
  });

  it('shows the expired screen (not the wait) on a terminal 410, keeping the JWT', async () => {
    localStorage.setItem(KEY, 'expired.jwt.tok');
    sessionStorage.setItem(KEY, 'expired.jwt.tok');
    let claimCalls = 0;
    fetchMock.mockImplementation((url: string) => {
      if (String(url).includes('/claim')) {
        claimCalls += 1;
        return Promise.resolve(jsonRes(410, { error: 'expired', terminal: true }));
      }
      return Promise.resolve(jsonRes(200, { state: 'no_link' }));
    });

    render(
      <EmpireNoLinkClient>
        <Static />
      </EmpireNoLinkClient>,
    );

    // Terminal expiry → explicit expired screen, waiting card gone.
    await waitFor(() =>
      expect(screen.getByTestId('empire-home-nolink-expired')).toBeTruthy(),
    );
    expect(screen.queryByTestId('empire-home-nolink-polling')).toBeNull();
    expect(screen.getByText('noLinkExpiredTitle')).toBeTruthy();
    expect(claimCalls).toBeGreaterThan(0);
    // The JWT is preserved — a manual link / coach action may still complete it.
    expect(localStorage.getItem(KEY)).toBe('expired.jwt.tok');
    expect(sessionStorage.getItem(KEY)).toBe('expired.jwt.tok');
    expect(refresh).not.toHaveBeenCalled();
  });

  it('renders the reopen button on the expired screen when a welcome URL is stored', async () => {
    localStorage.setItem(KEY, 'expired.jwt.tok');
    localStorage.setItem(WELCOME_KEY, 'https://branch.example/welcome');
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        String(url).includes('/claim')
          ? jsonRes(410, { error: 'expired', terminal: true })
          : jsonRes(200, { state: 'no_link' }),
      ),
    );

    render(
      <EmpireNoLinkClient>
        <Static />
      </EmpireNoLinkClient>,
    );

    const btn = await screen.findByTestId('empire-nolink-expired-reopen');
    expect(btn.getAttribute('href')).toBe('https://branch.example/welcome');
  });

  it('shows the expired screen without a reopen button when no welcome URL is stored', async () => {
    localStorage.setItem(KEY, 'expired.jwt.tok');
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        String(url).includes('/claim')
          ? jsonRes(410, { error: 'expired', terminal: true })
          : jsonRes(200, { state: 'no_link' }),
      ),
    );

    render(
      <EmpireNoLinkClient>
        <Static />
      </EmpireNoLinkClient>,
    );

    await waitFor(() =>
      expect(screen.getByTestId('empire-home-nolink-expired')).toBeTruthy(),
    );
    expect(screen.queryByTestId('empire-nolink-expired-reopen')).toBeNull();
  });

  it('retries the claim + poll on a fresh mount (remount restarts polling)', async () => {
    localStorage.setItem(KEY, 'stored.jwt.tok');
    // A transient 500 keeps the JWT and keeps polling (non-terminal) so the
    // remount-restart behavior stays observable.
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        String(url).includes('/claim')
          ? jsonRes(500, { error: 'server_error' })
          : jsonRes(200, { state: 'no_link' }),
      ),
    );

    const first = render(
      <EmpireNoLinkClient>
        <Static />
      </EmpireNoLinkClient>,
    );
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some((c) => String(c[0]).includes('/claim')),
      ).toBe(true),
    );
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some((c) => String(c[0]).includes('/status')),
      ).toBe(true),
    );

    // Unmount and remount — a fresh page load must retry both the claim and poll.
    first.unmount();
    fetchMock.mockClear();

    render(
      <EmpireNoLinkClient>
        <Static />
      </EmpireNoLinkClient>,
    );
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some((c) => String(c[0]).includes('/claim')),
      ).toBe(true),
    );
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some((c) => String(c[0]).includes('/status')),
      ).toBe(true),
    );
  });

  it('shows dead-end guidance at the poll cap with no JWT and recoverable:false', async () => {
    vi.useFakeTimers();
    try {
      // No stored JWT; status stays no_link and the server says it can't recover.
      fetchMock.mockResolvedValue(jsonRes(200, { state: 'no_link', recoverable: false }));
      render(
        <EmpireNoLinkClient>
          <Static />
        </EmpireNoLinkClient>,
      );
      // Flush the initial claim skip + first status poll (records recoverable)...
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      // ...then blow past the ~10-min poll cap.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(11 * 60_000);
      });

      expect(screen.getByTestId('empire-home-nolink-deadend')).toBeTruthy();
      expect(screen.getByText('noLinkDeadEndTitle')).toBeTruthy();
      expect(screen.queryByTestId('empire-nolink-stalled')).toBeNull();
      expect(refresh).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });

  it('keeps the calm static screen at the poll cap when recoverable:true', async () => {
    vi.useFakeTimers();
    try {
      fetchMock.mockResolvedValue(jsonRes(200, { state: 'no_link', recoverable: true }));
      render(
        <EmpireNoLinkClient>
          <Static />
        </EmpireNoLinkClient>,
      );
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(11 * 60_000);
      });

      // A recoverable wait is not a dead end — the calm static screen shows.
      expect(screen.queryByTestId('empire-home-nolink-deadend')).toBeNull();
      expect(screen.getByTestId('empire-nolink-stalled')).toBeTruthy();
      expect(screen.getByTestId('static-message')).toBeTruthy();
    } finally {
      vi.useRealTimers();
    }
  });

  it('polls /link/status and refreshes when the state leaves no_link', async () => {
    // No stored JWT → claim is skipped, straight to polling.
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        String(url).includes('/status')
          ? jsonRes(200, { state: 'verified' })
          : jsonRes(200, {}),
      ),
    );

    render(
      <EmpireNoLinkClient>
        <Static />
      </EmpireNoLinkClient>,
    );

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    const claimCalled = fetchMock.mock.calls.some((c) =>
      String(c[0]).includes('/claim'),
    );
    expect(claimCalled).toBe(false);
  });
});

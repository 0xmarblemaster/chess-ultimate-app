'use client'

/**
 * Client wrapper for the Chess Empire `no_link` dashboard state.
 *
 * The member row is written asynchronously — by the Clerk `user.created`
 * webhook, by the server-side pending-cookie auto-claim, and (for OAuth signups
 * that dropped `unsafeMetadata`) by the client-side claim. Any of these can
 * land after the dashboard first renders, which would otherwise strand the user
 * on the static "no link" screen.
 *
 * The `children` are ALWAYS the page content (the standard Chesster dashboard) —
 * a `no_link` user gets a fully usable app, never a full-screen waiting takeover.
 * On top of that, on every mount (initial load, `router.refresh`, or Refresh)
 * this:
 *   1. Replays any stashed invite JWT to `/api/chess-empire/link/claim`. The
 *      server accepts an expired-but-signed JWT within a 7-day grace window, and
 *      falls back to the `ce_pending_jti` cookie → pending row. The stashed JWT
 *      is cleared ONLY on success or a signature-class (`invalid`) terminal —
 *      an expiry never wipes it, since the server may still accept it. A
 *      terminal 410 (expired beyond grace, no server-side pending recovery)
 *      surfaces a dismissible "invite expired" banner over the dashboard.
 *   2. Polls `/api/chess-empire/link/status` with capped exponential backoff
 *      (up to ~10 min) and `router.refresh()`es the moment the state leaves
 *      `no_link` (so a branch student whose webhook lands late auto-upgrades
 *      into the CE homepage). After the cap it just keeps rendering the
 *      dashboard; a page reload restarts polling. When the server reports the
 *      link can't recover from here, a dismissible "dead end" banner appears.
 */
import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import {
  CE_INVITE_JWT_STORAGE_KEY,
  readBranchWelcomeUrl,
} from '@/lib/invite-storage'

// Keep polling slowly for ~10 min before falling back to the manual Refresh.
const POLL_MAX_MS = 10 * 60_000
const POLL_BASE_MS = 2_000
const POLL_MAX_INTERVAL_MS = 30_000

function readStoredJwt(): string | null {
  try {
    return (
      sessionStorage.getItem(CE_INVITE_JWT_STORAGE_KEY) ||
      localStorage.getItem(CE_INVITE_JWT_STORAGE_KEY)
    )
  } catch {
    return null
  }
}

function clearStoredJwt(): void {
  try {
    sessionStorage.removeItem(CE_INVITE_JWT_STORAGE_KEY)
    localStorage.removeItem(CE_INVITE_JWT_STORAGE_KEY)
  } catch {
    // ignore — storage unavailable
  }
}

export default function EmpireNoLinkClient({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const t = useTranslations('empire')
  // Bumping this re-runs the claim + poll cycle (Refresh button / restart).
  const [runId, setRunId] = useState(0)
  const [startOverUrl, setStartOverUrl] = useState<string | null>(null)
  // The stashed JWT expired beyond grace with no server-side recovery — the
  // link can never complete from browser state. Show a terminal expired screen
  // instead of the indefinite "setting up" wait.
  const [expired, setExpired] = useState(false)
  // The poll cap was reached with no stashed JWT and a `recoverable: false`
  // status — nothing left can complete the link from here (typically an
  // external browser after an in-app-webview OAuth bounce). Show recovery
  // guidance instead of the calm static "setting up" screen.
  const [deadEnd, setDeadEnd] = useState(false)

  useEffect(() => {
    // localStorage isn't available during SSR, so this must read in an effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStartOverUrl(readBranchWelcomeUrl())
  }, [])

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined
    const start = Date.now()
    let attempt = 0
    // Latest `recoverable` from a no_link status response. Undefined until the
    // first successful poll, so a poll that never reached the server stays a
    // calm wait rather than a false dead end.
    let lastRecoverable: boolean | undefined

    const linked = () => {
      if (cancelled) return
      router.refresh()
    }

    // Returns true when the cycle is terminal (linked or expired) and polling
    // should NOT start.
    async function claimIfPresent(): Promise<boolean> {
      const jwt = readStoredJwt()
      if (!jwt) return false
      try {
        const res = await fetch('/api/chess-empire/link/claim', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ inviteJwt: jwt }),
        })
        if (res.ok) {
          clearStoredJwt()
          linked()
          return true
        }
        const data = await res.json().catch(() => ({}))
        // Only a signature-class terminal is truly hopeless. An expired JWT may
        // still be claimable later via the server-side pending row, so keep it.
        if (data?.error === 'invalid') clearStoredJwt()
        // A terminal 410 means the JWT expired beyond grace AND no server-side
        // pending row could recover it — the link can never complete from here.
        // Surface an explicit expired screen instead of waiting forever. Keep
        // the JWT (harmless, and never clear it on expiry) so a manual link or
        // coach-side action can still succeed.
        if (res.status === 410 && data?.error === 'expired') {
          if (!cancelled) setExpired(true)
          return true
        }
      } catch {
        // Network hiccup — polling still runs and the webhook is the backstop.
      }
      return false
    }

    async function pollStatus(): Promise<void> {
      if (cancelled) return
      if (Date.now() - start >= POLL_MAX_MS) {
        // No stashed JWT to replay and the server says the link can't complete
        // from here — this is a dead end, not a calm wait. Show guidance.
        if (!readStoredJwt() && lastRecoverable === false) setDeadEnd(true)
        return
      }
      try {
        const res = await fetch('/api/chess-empire/link/status')
        if (res.ok) {
          const data = await res.json()
          if (typeof data?.recoverable === 'boolean') {
            lastRecoverable = data.recoverable
          }
          if (data?.state && data.state !== 'no_link') {
            linked()
            return
          }
        }
      } catch {
        // ignore — retry on the next tick
      }
      attempt += 1
      const delay = Math.min(
        POLL_MAX_INTERVAL_MS,
        Math.round(POLL_BASE_MS * Math.pow(1.4, attempt - 1)),
      )
      timer = setTimeout(pollStatus, delay)
    }

    void (async () => {
      const terminal = await claimIfPresent()
      if (!cancelled && !terminal) void pollStatus()
    })()

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [router, runId])

  const restart = useCallback(() => {
    setExpired(false)
    setDeadEnd(false)
    setRunId((n) => n + 1)
  }, [])

  // Close a banner without restarting polling — the dashboard stays usable and a
  // page reload will resume the claim/poll cycle if the user wants to retry.
  const dismissBanner = useCallback(() => {
    setExpired(false)
    setDeadEnd(false)
  }, [])

  // The dashboard is ALWAYS rendered. `expired`/`deadEnd` add a slim, dismissible
  // banner over it instead of replacing the page with a full-screen takeover.
  return (
    <>
      {children}
      {expired && (
        <div
          data-testid="empire-home-nolink-expired"
          className="fixed inset-x-0 bottom-0 z-40 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 border-t border-slate-200 bg-white/95 px-4 py-3 text-sm shadow-[0_-1px_8px_rgba(0,0,0,0.06)] backdrop-blur"
        >
          <p className="text-center text-slate-700">
            <span className="font-semibold text-slate-900">
              {t('noLinkExpiredTitle')}
            </span>{' '}
            {t('noLinkExpiredBody')}
          </p>
          {startOverUrl && (
            <a
              data-testid="empire-nolink-expired-reopen"
              href={startOverUrl}
              className="rounded-full bg-slate-900 px-4 py-1.5 font-semibold text-white hover:bg-slate-700"
            >
              {t('noLinkExpiredReopen')}
            </a>
          )}
          <button
            type="button"
            data-testid="empire-nolink-expired-dismiss"
            onClick={dismissBanner}
            aria-label="Dismiss"
            className="ml-1 text-lg leading-none text-slate-400 hover:text-slate-700"
          >
            ×
          </button>
        </div>
      )}
      {deadEnd && (
        <div
          data-testid="empire-home-nolink-deadend"
          className="fixed inset-x-0 bottom-0 z-40 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 border-t border-slate-200 bg-white/95 px-4 py-3 text-sm shadow-[0_-1px_8px_rgba(0,0,0,0.06)] backdrop-blur"
        >
          <p className="text-center text-slate-700">
            <span className="font-semibold text-slate-900">
              {t('noLinkDeadEndTitle')}
            </span>{' '}
            {t('noLinkDeadEndBody')}
          </p>
          {startOverUrl && (
            <a
              data-testid="empire-nolink-deadend-reopen"
              href={startOverUrl}
              className="rounded-full bg-slate-900 px-4 py-1.5 font-semibold text-white hover:bg-slate-700"
            >
              {t('noLinkExpiredReopen')}
            </a>
          )}
          <button
            type="button"
            data-testid="empire-nolink-deadend-refresh"
            onClick={restart}
            className="font-semibold text-slate-500 underline underline-offset-4 hover:text-slate-700"
          >
            {t('noLinkRefresh')}
          </button>
          <button
            type="button"
            data-testid="empire-nolink-deadend-dismiss"
            onClick={dismissBanner}
            aria-label="Dismiss"
            className="ml-1 text-lg leading-none text-slate-400 hover:text-slate-700"
          >
            ×
          </button>
        </div>
      )}
    </>
  )
}

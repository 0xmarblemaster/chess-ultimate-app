/**
 * Online-students onboarding (client state machine, no interstitial).
 *
 * Online invite tokens (`branch_invite_tokens.kind='online'`) have no Chess
 * Empire roster to match against, so we skip the search/confirm flow entirely.
 * The name is asked again on the Clerk sign-up form, so this page no longer
 * collects one: on mount it mints a synthetic-student invite JWT via
 * `/api/chess-empire/online/register` (no name) and hands off to Clerk sign-up
 * exactly like the branch flow. The minted JWT carries the token's access TTL so
 * the webhook can time-box the linked member.
 */
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { useTranslations } from 'next-intl';
import Image from 'next/image';
import { useBranding } from '@/contexts/OrganizationContext';
import {
  persistWelcomeOnboardingUrl,
  persistBranchWelcomeUrl,
} from '@/lib/invite-storage';

interface OnlineWelcomeFlowProps {
  branchToken: string;
}

export default function OnlineWelcomeFlow({ branchToken }: OnlineWelcomeFlowProps) {
  const t = useTranslations('welcome');
  const router = useRouter();
  const { isSignedIn } = useAuth();
  const branding = useBranding();

  const [error, setError] = useState<string | null>(null);
  // Strict mode runs effects twice in dev; the ref makes register fire once.
  const registeredRef = useRef(false);

  // Persist where onboarding started so the sign-up guard can bounce an
  // abandoned bare sign-up back here (matches the branch flow).
  useEffect(() => {
    persistWelcomeOnboardingUrl(
      window.location.pathname + window.location.search,
    );
  }, []);

  const register = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch('/api/chess-empire/online/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branchToken }),
      });
      if (!res.ok) {
        setError(t('genericError'));
        return;
      }
      const body = (await res.json()) as { inviteJwt?: string };
      if (!body.inviteJwt) {
        setError(t('genericError'));
        return;
      }

      persistBranchWelcomeUrl(`/welcome/${encodeURIComponent(branchToken)}`);

      // Already signed in (rare for online sign-ups): claim server-side and go
      // straight to the dashboard, mirroring the branch flow.
      if (isSignedIn) {
        try {
          await fetch('/api/chess-empire/link/claim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ inviteJwt: body.inviteJwt }),
          });
        } catch {
          // Dashboard no_link poller replays the stashed JWT as a backstop.
        }
        router.replace('/dashboard');
        return;
      }

      router.replace(`/sign-up?invite=${encodeURIComponent(body.inviteJwt)}`);
    } catch {
      setError(t('genericError'));
    }
  }, [branchToken, isSignedIn, router, t]);

  // Auto-register on mount — no name input, no continue button. `register`
  // only ever calls setState after an awaited network round-trip (never
  // synchronously in the effect body), so the set-state-in-effect heuristic is
  // a false positive here.
  useEffect(() => {
    if (registeredRef.current) return;
    registeredRef.current = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void register();
  }, [register]);

  const onRetry = useCallback(() => {
    void register();
  }, [register]);

  return (
    <div className="flex flex-col items-center justify-start pt-16 md:justify-center md:pt-0 min-h-screen bg-purple-600 md:bg-gray-50 px-4 pb-[env(safe-area-inset-bottom)]">
      <div className="w-full max-w-md bg-white rounded-3xl p-6 md:p-8 mt-4 md:mt-0 shadow-xl">
        <div className="text-center mb-6">
          <div className="bg-white rounded-full inline-flex items-center justify-center shadow-lg w-24 h-24 md:w-28 md:h-28 overflow-hidden">
            {branding.logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={branding.logoUrl}
                alt={branding.name}
                className="w-full h-full object-contain"
              />
            ) : (
              <Image
                src="/static/images/chesster-logo-v3.png"
                alt={branding.name}
                width={112}
                height={112}
                className="w-full h-full object-contain"
                priority
              />
            )}
          </div>
        </div>

        <h1 className="text-2xl font-bold text-gray-800 text-center">
          {t('online.title')}
        </h1>
        <p className="text-sm text-gray-500 mt-2 text-center">
          {t('online.subtitle')}
        </p>

        {error ? (
          <>
            <p role="alert" className="text-sm text-red-500 mt-6 text-center">
              {error}
            </p>
            <button
              type="button"
              onClick={onRetry}
              className="mt-6 w-full bg-purple-600 hover:bg-purple-700 rounded-2xl py-4 font-bold uppercase tracking-wide text-white border-b-4 border-purple-800 active:border-b-2 active:translate-y-0.5 transition-all focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-300 focus-visible:ring-offset-2"
            >
              {t('online.continue')}
            </button>
          </>
        ) : (
          <p
            role="status"
            className="text-sm text-gray-500 mt-8 text-center animate-pulse"
          >
            {t('verifying')}
          </p>
        )}
      </div>
    </div>
  );
}

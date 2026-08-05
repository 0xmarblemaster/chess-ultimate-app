/**
 * Online-students onboarding (client state machine, single step).
 *
 * Online invite tokens (`branch_invite_tokens.kind='online'`) have no Chess
 * Empire roster to match against, so we skip the search/confirm flow entirely:
 * collect a display name, mint a synthetic-student invite JWT via
 * `/api/chess-empire/online/register`, then hand off to Clerk sign-up exactly
 * like the branch flow. The minted JWT carries the token's access TTL so the
 * webhook can time-box the linked member.
 */
'use client';

import { useCallback, useEffect, useState } from 'react';
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

  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Persist where onboarding started so the sign-up guard can bounce an
  // abandoned bare sign-up back here (matches the branch flow).
  useEffect(() => {
    persistWelcomeOnboardingUrl(
      window.location.pathname + window.location.search,
    );
  }, []);

  const onSubmit = useCallback(async () => {
    const trimmed = name.trim();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/chess-empire/online/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ branchToken, name: trimmed }),
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
    } finally {
      setSubmitting(false);
    }
  }, [name, submitting, branchToken, isSignedIn, router, t]);

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

        <div className="mt-6">
          <label htmlFor="online-name" className="sr-only">
            {t('online.nameLabel')}
          </label>
          <input
            id="online-name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onSubmit();
            }}
            placeholder={t('online.namePlaceholder')}
            className="w-full rounded-2xl border-2 border-gray-200 py-4 px-5 text-base placeholder:text-gray-400 transition-shadow focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:ring-offset-2"
          />
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-500 mt-4">
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting || name.trim().length === 0}
          className="mt-6 w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 disabled:border-gray-400 rounded-2xl py-4 font-bold uppercase tracking-wide text-white border-b-4 border-purple-800 active:border-b-2 active:translate-y-0.5 transition-all focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-300 focus-visible:ring-offset-2"
        >
          {submitting ? t('verifying') : t('online.continue')}
        </button>
      </div>
    </div>
  );
}

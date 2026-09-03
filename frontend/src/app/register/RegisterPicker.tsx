/**
 * Branch-picker registration UI (white-label tenants).
 *
 * Client half of the `/register` page. The server component resolves the org's
 * active branch-invite tokens and hands them here as plain data; this component
 * renders the tenant-branded picker — one Duolingo-style card per branch (each
 * links to its existing `/welcome/<token>` flow) plus a highlighted "online
 * student" card offering 3 days of free access. Falls back to a contact screen
 * when the org has no active tokens.
 *
 * Design mirrors the sign-in page exactly: purple background, white rounded-3xl
 * card, tenant logo via `useBranding`, Duolingo-style buttons.
 */
'use client';

import { useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import Image from 'next/image';
import { useBranding } from '@/contexts/OrganizationContext';

/** How long the purple selected state stays visible before redirecting. */
const SELECT_REDIRECT_DELAY_MS = 350;

export interface RegisterOption {
  /** Opaque branch_invite_tokens.token — routes to `/welcome/<token>`. */
  token: string;
  branchName: string;
}

interface RegisterPickerProps {
  branches: RegisterOption[];
  online: RegisterOption | null;
}

export default function RegisterPicker({ branches, online }: RegisterPickerProps) {
  const t = useTranslations('register');
  const tGlobal = useTranslations();
  const branding = useBranding();
  const isEmpty = branches.length === 0 && !online;

  const [selectedToken, setSelectedToken] = useState<string | null>(null);
  const redirecting = useRef(false);

  const handleSelect = (event: React.MouseEvent<HTMLAnchorElement>, token: string) => {
    event.preventDefault();
    if (redirecting.current) return;
    redirecting.current = true;
    setSelectedToken(token);
    const href = event.currentTarget.href;
    window.setTimeout(() => {
      window.location.assign(href);
    }, SELECT_REDIRECT_DELAY_MS);
  };

  return (
    <div className="flex flex-col items-center justify-start pt-16 md:justify-center md:pt-0 min-h-screen bg-purple-600 md:bg-gray-50 px-4 pb-[env(safe-area-inset-bottom)]">
      <div className="w-full max-w-md bg-white rounded-3xl p-6 md:p-8 mt-4 md:mt-0 shadow-xl">
        {/* Tenant-aware branding */}
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
          <h1 className="text-2xl font-bold text-gray-800 mt-4">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>

        {isEmpty ? (
          <div className="text-center">
            <h2 className="text-lg font-bold text-gray-800">{t('emptyTitle')}</h2>
            <p className="text-sm text-gray-500 mt-2">{t('emptyBody')}</p>
            {branding.contactEmail ? (
              <p className="text-sm text-gray-500 mt-4">
                {t('contactLabel')}:{' '}
                <a
                  href={`mailto:${branding.contactEmail}`}
                  className="text-purple-600 font-bold hover:underline"
                >
                  {branding.contactEmail}
                </a>
              </p>
            ) : null}
          </div>
        ) : (
          <div className="space-y-3">
            {branches.length > 0 && (
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                {t('branchesHeading')}
              </p>
            )}

            {branches.map((branch) => (
              <a
                key={branch.token}
                href={`/welcome/${encodeURIComponent(branch.token)}`}
                onClick={(e) => handleSelect(e, branch.token)}
                aria-pressed={selectedToken === branch.token}
                className={`block w-full text-center rounded-2xl py-4 px-4 font-bold transition-all border-2 ${
                  selectedToken === branch.token
                    ? 'border-purple-600 ring-2 ring-purple-600 bg-purple-50 text-purple-700'
                    : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300'
                }`}
              >
                {branch.branchName}
              </a>
            ))}

            {online && (
              <a
                href={`/welcome/${encodeURIComponent(online.token)}`}
                onClick={(e) => handleSelect(e, online.token)}
                aria-pressed={selectedToken === online.token}
                className={`block w-full rounded-2xl p-4 text-left bg-gradient-to-b from-purple-600 to-purple-700 text-white border-b-4 border-purple-800 hover:from-purple-500 hover:to-purple-600 active:border-b-2 active:translate-y-0.5 transition-all ${
                  selectedToken === online.token
                    ? 'ring-2 ring-purple-600 ring-offset-2'
                    : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold uppercase tracking-wide">
                    {t('online.title')}
                  </span>
                  <span className="text-xs font-bold uppercase bg-white/20 rounded-full px-2 py-0.5">
                    {t('online.badge')}
                  </span>
                </div>
                <p className="text-sm text-white/90 mt-1">{t('online.subtitle')}</p>
              </a>
            )}
          </div>
        )}

        {/* Custom footer with sign-in link (mirrors the sign-in page footer) */}
        <div className="text-center mt-4">
          <span className="text-gray-400 text-sm">{tGlobal('auth.haveAccount')} </span>
          <a href="/sign-in" className="text-purple-600 font-bold text-sm hover:underline">
            {tGlobal('common.signIn')}
          </a>
        </div>
      </div>
    </div>
  );
}

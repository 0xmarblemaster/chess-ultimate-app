'use client';

/**
 * Full-width "Tournament Registration" CTA banner for the Empire student
 * home page (Variation B: amber/gold card between the hero and stat pills).
 *
 * The entire card is a single `next/link` to `/tournaments`, so the whole
 * banner is clickable; the "Register" pill on the right is purely visual.
 * A pure-CSS diagonal shimmer (see `.tournament-cta-shimmer` in globals.css)
 * sweeps across it and is disabled under `prefers-reduced-motion`.
 */
import Link from 'next/link';
import { useTranslations } from 'next-intl';

export default function TournamentCtaBanner({ className = '' }: { className?: string }) {
  const t = useTranslations('empire');

  return (
    <Link
      href="/tournaments"
      data-testid="empire-tournament-cta"
      className={`relative overflow-hidden block rounded-2xl shadow-sm bg-gradient-to-r from-amber-500 to-yellow-400 text-slate-900 transition hover:shadow-md ${className}`}
    >
      {/* Diagonal shimmer sweep — decorative, never intercepts the click. */}
      <span
        aria-hidden="true"
        className="tournament-cta-shimmer pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 -skew-x-12 bg-gradient-to-r from-transparent via-white/40 to-transparent"
      />
      <div className="relative p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center gap-4">
        <div
          className="w-12 h-12 rounded-xl grid place-items-center bg-white/25 shrink-0"
          aria-hidden="true"
        >
          <svg
            width={26}
            height={26}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
            <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
            <path d="M4 22h16" />
            <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
            <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
            <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-lg font-bold tracking-tight leading-tight">
            {t('tournamentCtaTitle')}
          </div>
          <div className="mt-0.5 text-sm font-medium text-slate-800">
            {t('tournamentCtaSubtitle')}
          </div>
        </div>
        <span
          data-testid="empire-tournament-cta-button"
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 text-white text-sm font-semibold shrink-0"
        >
          {t('tournamentCtaButton')}
          <svg
            width={14}
            height={14}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.5}
            aria-hidden="true"
          >
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </span>
      </div>
    </Link>
  );
}

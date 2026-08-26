'use client';

/**
 * Chess Empire tournaments — client view + registration gate.
 *
 * Renders the league schedule ported from the public app.chessempire.kz page
 * (name · date/time · venue · format · fee · rounds · capacity meter · status),
 * restyled to sit inside the Chesster app shell. Three visitor states share the
 * same list: logged-out and unverified visitors see the card + a prompt on
 * Register; verified members get one-click self-registration with a name-confirm
 * step and a Cancel action once registered.
 */
import { useState } from 'react';
import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';

export interface CETournamentCard {
  id: string;
  name: string;
  info: string | null;
  tournament_date: string;
  start_time: string | null;
  time_format: string | null;
  registration_fee: number;
  rounds: number;
  capacity: number;
  /** 'open' | 'closed' | 'cancelled'. */
  status: string;
  registered_count: number;
  branch_name: string | null;
  /** Non-null when the viewing member is already registered. */
  registration_id: string | null;
}

export type CEViewer =
  | { state: 'logged_out' }
  | { state: 'unverified' }
  | { state: 'verified'; studentName: string | null };

const SIGN_IN_HREF = '/sign-in?redirect_url=/tournaments';
const VERIFY_HREF = '/dashboard';

/** App locale → BCP-47 tag for Intl date/number formatting. */
const LOCALE_TAG: Record<string, string> = {
  en: 'en-US',
  ru: 'ru-RU',
  kz: 'kk-KZ',
};

function formatDate(iso: string, tag: string): string {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(tag, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function formatTime(t: string | null): string {
  if (!t) return '—';
  return String(t).slice(0, 5);
}

function formatFee(fee: number, tag: string, freeLabel: string): string {
  const n = Number(fee || 0);
  if (n === 0) return freeLabel;
  return `${n.toLocaleString(tag)} ₸`;
}

function StatusBadge({
  isFull,
  isOpen,
}: {
  isFull: boolean;
  isOpen: boolean;
}) {
  const t = useTranslations('ceTournaments');
  const { label, className } = isFull
    ? {
        label: t('statusFull'),
        className:
          'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
      }
    : isOpen
      ? {
          label: t('statusOpen'),
          className:
            'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
        }
      : {
          label: t('statusClosed'),
          className:
            'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
        };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}
    >
      {label}
    </span>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">
        {label}
      </div>
      <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mt-0.5">
        {value}
      </div>
    </div>
  );
}

function TournamentCard({
  card,
  viewer,
}: {
  card: CETournamentCard;
  viewer: CEViewer;
}) {
  const t = useTranslations('ceTournaments');
  const locale = useLocale();
  const tag = LOCALE_TAG[locale] ?? 'en-US';
  const [registrationId, setRegistrationId] = useState<string | null>(
    card.registration_id,
  );
  const [registeredCount, setRegisteredCount] = useState(card.registered_count);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  const isRegistered = registrationId !== null;
  const isFull = registeredCount >= card.capacity;
  const isOpen = card.status === 'open' && !isFull;
  const fillPct = Math.min(
    100,
    Math.round((registeredCount / Math.max(1, card.capacity)) * 100),
  );

  /** Localize a server `{ error, message }` payload by code, else fall back. */
  function resolveError(
    data: { error?: string; message?: string },
    fallbackKey: 'errors.registerFailed' | 'errors.cancelFailed',
  ): string {
    const code = data.error;
    if (code && t.has(`errors.${code}`)) return t(`errors.${code}`);
    return data.message || t(fallbackKey);
  }

  async function doRegister() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/chess-empire/tournaments/${card.id}/register`, {
        method: 'POST',
      });
      const data = (await res.json().catch(() => ({}))) as {
        registration_id?: string;
        registered_count?: number;
        error?: string;
        message?: string;
      };
      if (!res.ok) {
        setError(resolveError(data, 'errors.registerFailed'));
        return;
      }
      setRegistrationId(data.registration_id ?? 'registered');
      setRegisteredCount(data.registered_count ?? registeredCount + 1);
      setConfirming(false);
    } catch {
      setError(t('errors.network'));
    } finally {
      setBusy(false);
    }
  }

  async function doCancel() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/chess-empire/tournaments/${card.id}/register`, {
        method: 'DELETE',
      });
      const data = (await res.json().catch(() => ({}))) as {
        error?: string;
        message?: string;
      };
      if (!res.ok) {
        setError(resolveError(data, 'errors.cancelFailed'));
        return;
      }
      setRegistrationId(null);
      setRegisteredCount((c) => Math.max(0, c - 1));
    } catch {
      setError(t('errors.network'));
    } finally {
      setBusy(false);
    }
  }

  function onRegisterClick() {
    setError(null);
    if (viewer.state === 'logged_out') {
      setNotice(t('loggedOutNotice'));
      return;
    }
    if (viewer.state === 'unverified') {
      setNotice(t('unverifiedNotice'));
      return;
    }
    setConfirming(true);
  }

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100 leading-snug">
          {card.name}
        </h3>
        <StatusBadge isFull={isFull} isOpen={isOpen} />
      </div>

      {card.branch_name && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {card.branch_name}
        </p>
      )}

      {card.info && (
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-3">
          {card.info}
        </p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
        <DetailItem
          label={t('date')}
          value={formatDate(card.tournament_date, tag)}
        />
        <DetailItem label={t('time')} value={formatTime(card.start_time)} />
        <DetailItem label={t('format')} value={card.time_format || '—'} />
        <DetailItem label={t('rounds')} value={String(card.rounds)} />
        <DetailItem
          label={t('entryFee')}
          value={formatFee(card.registration_fee, tag, t('free'))}
        />
        <DetailItem
          label={t('players')}
          value={`${registeredCount}/${card.capacity}`}
        />
      </div>

      <div className="mt-3">
        <div className="h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${fillPct}%`,
              backgroundColor: isFull ? '#dc2626' : 'var(--brand-primary)',
            }}
          />
        </div>
      </div>

      <div className="mt-4">
        {isRegistered ? (
          <div className="flex items-center justify-between gap-3">
            <span className="inline-flex items-center gap-1 text-sm font-medium text-green-600 dark:text-green-400">
              {t('registered')}
            </span>
            <button
              type="button"
              onClick={doCancel}
              disabled={busy}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              {busy ? t('cancelling') : t('cancelRegistration')}
            </button>
          </div>
        ) : confirming && viewer.state === 'verified' ? (
          <div>
            <p className="text-sm text-gray-700 dark:text-gray-200">
              {t.rich('confirmPrompt', {
                name: viewer.studentName || t('yourself'),
                b: (chunks) => (
                  <span className="font-semibold">{chunks}</span>
                ),
              })}
            </p>
            <div className="flex items-center gap-2 mt-3">
              <button
                type="button"
                onClick={doRegister}
                disabled={busy}
                className="px-4 py-1.5 text-sm rounded-lg font-medium text-white disabled:opacity-50"
                style={{ backgroundColor: 'var(--brand-primary)' }}
              >
                {busy ? t('registering') : t('confirm')}
              </button>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                disabled={busy}
                className="px-3 py-1.5 text-sm rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
              >
                {t('notNow')}
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={onRegisterClick}
            disabled={viewer.state === 'verified' && !isOpen}
            className="px-4 py-1.5 text-sm rounded-lg font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            style={{ backgroundColor: 'var(--brand-primary)' }}
          >
            {viewer.state === 'verified' && !isOpen
              ? isFull
                ? t('tournamentFull')
                : t('registrationClosed')
              : t('register')}
          </button>
        )}

        {notice && !isRegistered && (
          <div className="mt-3 text-sm text-gray-700 dark:text-gray-200">
            <p>{notice}</p>
            {viewer.state === 'logged_out' && (
              <Link
                href={SIGN_IN_HREF}
                className="inline-block mt-1 font-medium underline"
                style={{ color: 'var(--brand-primary)' }}
              >
                {t('signInToRegister')} →
              </Link>
            )}
            {viewer.state === 'unverified' && (
              <Link
                href={VERIFY_HREF}
                className="inline-block mt-1 font-medium underline"
                style={{ color: 'var(--brand-primary)' }}
              >
                {t('verifyMembership')} →
              </Link>
            )}
          </div>
        )}

        {error && (
          <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
      </div>
    </div>
  );
}

export default function CETournamentsView({
  tournaments,
  viewer,
}: {
  tournaments: CETournamentCard[];
  viewer: CEViewer;
}) {
  const t = useTranslations('ceTournaments');
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {t('title')}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {t('subtitle')}
        </p>
      </div>

      {viewer.state === 'logged_out' && (
        <div className="mb-6 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 p-4 text-sm text-gray-700 dark:text-gray-200">
          {t('loggedOutBanner')}{' '}
          <Link
            href={SIGN_IN_HREF}
            className="font-medium underline"
            style={{ color: 'var(--brand-primary)' }}
          >
            {t('signInToRegister')}
          </Link>
          .
        </div>
      )}

      {viewer.state === 'unverified' && (
        <div className="mb-6 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 p-4 text-sm text-gray-700 dark:text-gray-200">
          {t('unverifiedBanner')}{' '}
          <Link
            href={VERIFY_HREF}
            className="font-medium underline"
            style={{ color: 'var(--brand-primary)' }}
          >
            {t('verifyMembership')}
          </Link>
          .
        </div>
      )}

      {tournaments.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-10 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            {t('empty')}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {tournaments.map((tournament) => (
            <TournamentCard
              key={tournament.id}
              card={tournament}
              viewer={viewer}
            />
          ))}
        </div>
      )}
    </div>
  );
}

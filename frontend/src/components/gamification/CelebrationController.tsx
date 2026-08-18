/**
 * Fires CelebrationOverlay for rank-up and streak-milestone moments (§3, §5.5, §6).
 *
 * Mounted where the gamification profile is loaded client-side (the profile
 * page). It diffs the profile against a small per-student localStorage snapshot
 * via `nextCelebration` (pure) and renders the matching overlay once. Item-unlock
 * moments are fired at the point of purchase (the shop), not here.
 */
'use client';

import { useEffect, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import {
  type CelebrationEvent,
  type CelebrationState,
  nextCelebration,
} from '@/lib/gamification/celebration-triggers';
import type { GamificationProfile } from '@/lib/gamification/profile';
import { CelebrationOverlay, LevelUpCelebration } from './CelebrationOverlay';

const STORAGE_PREFIX = 'gam.celebrations.';

function rankName(rank: NonNullable<GamificationProfile['rank']>, locale: string): string {
  if (locale === 'ru') return rank.name_ru;
  if (locale === 'kz') return rank.name_kk;
  return rank.name_en;
}

export function CelebrationController({ profile }: { profile: GamificationProfile | null }) {
  const t = useTranslations('gamification');
  const locale = useLocale();
  const [event, setEvent] = useState<CelebrationEvent>(null);

  useEffect(() => {
    if (!profile || !profile.linked || typeof window === 'undefined') return;
    const key = STORAGE_PREFIX + (profile.student_id ?? 'me');
    let prev: CelebrationState = {};
    try {
      const raw = window.localStorage.getItem(key);
      if (raw) prev = JSON.parse(raw) as CelebrationState;
    } catch {
      prev = {};
    }
    const { event: next, state } = nextCelebration(prev, profile);
    try {
      window.localStorage.setItem(key, JSON.stringify(state));
    } catch {
      /* storage disabled — the overlay still fires this session */
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot fire after the localStorage diff
    if (next) setEvent(next);
  }, [profile]);

  if (!event) return null;

  if (event.type === 'rankUp' && profile?.rank) {
    return (
      <LevelUpCelebration
        newLevel={rankName(profile.rank, locale)}
        levelIcon="♟️"
        xpGained={0}
        onClose={() => setEvent(null)}
      />
    );
  }

  if (event.type === 'streakMilestone') {
    return (
      <CelebrationOverlay
        type="streak"
        title={`🔥 ${event.weeks} ${t('weekStreak')}!`}
        subtitle={t('keepItGoing')}
        icon="🔥"
        onClose={() => setEvent(null)}
        autoClose={false}
      />
    );
  }

  return null;
}

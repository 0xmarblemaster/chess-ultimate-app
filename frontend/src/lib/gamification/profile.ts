/**
 * Gamification profile assembly (shared by the profile API route and its tests).
 *
 * Pure with respect to inputs: given the org config, rank ladder, and the two
 * read-model rows, it produces the client-facing profile payload. Kept separate
 * from the route so the shaping/auth logic can be unit tested.
 */
import {
  type GamificationConfig,
  type RankRow,
  rankProgress,
  roundHalf,
} from './economy';

export interface PlayerRow {
  xp_total: number | string;
  coin_balance: number | string;
  rank_code: string | null;
  tournaments_played: number;
  wins_total: number | string;
}

export interface StreakRow {
  current_weeks: number;
  best_weeks: number;
  run_start_week: string | null;
  last_active_week: string | null;
}

export interface GamificationProfile {
  linked: boolean;
  student_id?: string;
  xp: number;
  coins: number;
  rank: {
    code: string;
    name_ru: string;
    name_kk: string;
    name_en: string;
    icon_url?: string | null;
  } | null;
  rank_progress: {
    pct: number;
    xp_into_rank: number;
    xp_for_next: number;
    next_code: string | null;
    next_min_xp: number | null;
  };
  streak: {
    current_weeks: number;
    best_weeks: number;
    last_active_week: string | null;
    next_milestone: { weeks: number; reward: number } | null;
  };
  stats: { tournaments_played: number; wins_total: number };
  /** Current legion (crest + name) — null while unmapped/unknown (Phase 3). */
  legion: ProfileLegion | null;
  /** Permanent trophy items with provenance — «Зал славы» (Phase 3, §7.4). */
  trophies: ProfileTrophy[];
}

export interface ProfileLegion {
  id: string;
  name: string;
  totem?: string | null;
  crest_url?: string | null;
  color_primary?: string | null;
  color_secondary?: string | null;
}

export interface ProfileTrophy {
  item_id: string;
  name_ru: string;
  name_kk: string;
  name_en: string;
  art_url: string | null;
  acquisition_note: string | null;
  season_id: string | null;
  acquired_at: string | null;
}

/** Optional Phase 3 additions layered onto the base profile (legion + trophies). */
export interface ProfileExtras {
  legion?: ProfileLegion | null;
  trophies?: ProfileTrophy[];
}

function num(v: unknown): number {
  const n = typeof v === 'string' ? parseFloat(v) : (v as number);
  return Number.isFinite(n) ? n : 0;
}

/** Empty/hidden profile for unlinked students (D-8). */
export const UNLINKED_PROFILE: Pick<GamificationProfile, 'linked'> = { linked: false };

/** Smallest milestone strictly above the current streak length. */
export function nextMilestone(
  config: GamificationConfig,
  currentWeeks: number,
): { weeks: number; reward: number } | null {
  const entries = Object.entries(config.streak.milestones ?? {})
    .map(([k, v]) => ({ weeks: parseInt(k, 10), reward: Number(v) }))
    .filter((m) => Number.isFinite(m.weeks) && m.weeks > 0)
    .sort((a, b) => a.weeks - b.weeks);
  return entries.find((m) => m.weeks > currentWeeks) ?? null;
}

export function buildProfile(
  studentId: string,
  player: PlayerRow | null,
  streak: StreakRow | null,
  ranks: RankRow[],
  config: GamificationConfig,
  extras: ProfileExtras = {},
): GamificationProfile {
  const xp = roundHalf(num(player?.xp_total));
  const coins = roundHalf(num(player?.coin_balance));
  const progress = rankProgress(ranks, xp);
  const currentWeeks = streak?.current_weeks ?? 0;

  return {
    linked: true,
    student_id: studentId,
    xp,
    coins,
    rank: progress.current
      ? {
          code: progress.current.code,
          name_ru: progress.current.name_ru,
          name_kk: progress.current.name_kk,
          name_en: progress.current.name_en,
          icon_url: progress.current.icon_url ?? null,
        }
      : null,
    rank_progress: {
      pct: progress.pct,
      xp_into_rank: progress.xpIntoRank,
      xp_for_next: progress.xpForNext,
      next_code: progress.next?.code ?? null,
      next_min_xp: progress.next?.min_xp ?? null,
    },
    streak: {
      current_weeks: currentWeeks,
      best_weeks: streak?.best_weeks ?? 0,
      last_active_week: streak?.last_active_week ?? null,
      next_milestone: nextMilestone(config, currentWeeks),
    },
    stats: {
      tournaments_played: player?.tournaments_played ?? 0,
      wins_total: roundHalf(num(player?.wins_total)),
    },
    legion: extras.legion ?? null,
    trophies: extras.trophies ?? [],
  };
}

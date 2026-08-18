/**
 * Celebration trigger logic (PRD §3, §5.5, §6) — pure, no DOM/storage.
 *
 * Diffs a small persisted snapshot against the current gamification profile to
 * decide whether a rank-up or streak-milestone moment just happened, and returns
 * the next snapshot to persist. The controller owns localStorage + rendering;
 * this stays unit-testable.
 *
 * Milestone detection is list-free: we remember the milestone the profile last
 * reported as "next" (`pending_milestone`) and fire once `current_weeks` reaches
 * it, tracking the highest already-celebrated milestone so it never repeats.
 */
import type { GamificationProfile } from './profile';

export interface CelebrationState {
  rank_code?: string | null;
  /** The `next_milestone.weeks` observed on the previous load. */
  pending_milestone?: number | null;
  /** Highest milestone weeks already celebrated (never re-fires). */
  celebrated_milestone?: number | null;
}

export type CelebrationEvent =
  | { type: 'rankUp'; rank_code: string }
  | { type: 'streakMilestone'; weeks: number }
  | null;

/**
 * Decide the next celebration from the previous snapshot + current profile.
 * Returns the event to fire (or null) and the snapshot to persist. Rank-up takes
 * priority; a concurrent milestone is held back (streak fields unchanged) so it
 * fires on the next load rather than being dropped. A first load with an empty
 * snapshot only establishes the baseline — never celebrates.
 */
export function nextCelebration(
  prev: CelebrationState,
  profile: GamificationProfile,
): { event: CelebrationEvent; state: CelebrationState } {
  const newRank = profile.rank?.code ?? null;

  // Rank-up: rank code changed from a known prior value (XP only rises, so any
  // change is an increase). Hold streak state so a same-tick milestone survives.
  if (prev.rank_code != null && newRank && newRank !== prev.rank_code) {
    return {
      event: { type: 'rankUp', rank_code: newRank },
      state: { ...prev, rank_code: newRank },
    };
  }

  const pending = prev.pending_milestone ?? null;
  const currentWeeks = profile.streak?.current_weeks ?? 0;
  const nextWeeks = profile.streak?.next_milestone?.weeks ?? null;
  const celebratedBefore = prev.celebrated_milestone ?? null;

  let event: CelebrationEvent = null;
  let celebrated = celebratedBefore;
  if (
    pending != null &&
    currentWeeks >= pending &&
    (celebratedBefore == null || celebratedBefore < pending)
  ) {
    event = { type: 'streakMilestone', weeks: pending };
    celebrated = pending;
  }

  return {
    event,
    state: {
      rank_code: newRank,
      pending_milestone: nextWeeks,
      celebrated_milestone: celebrated,
    },
  };
}

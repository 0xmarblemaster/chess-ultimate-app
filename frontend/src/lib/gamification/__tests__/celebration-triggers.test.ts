import { describe, it, expect } from 'vitest';
import { type CelebrationState, nextCelebration } from '../celebration-triggers';
import type { GamificationProfile } from '../profile';

function profile(over: {
  rank?: string;
  weeks?: number;
  nextMilestone?: number | null;
}): GamificationProfile {
  return {
    linked: true,
    student_id: 'stu-1',
    xp: 100,
    coins: 100,
    rank: over.rank
      ? { code: over.rank, name_ru: '', name_kk: '', name_en: over.rank }
      : null,
    rank_progress: { pct: 0, xp_into_rank: 0, xp_for_next: 0, next_code: null, next_min_xp: null },
    streak: {
      current_weeks: over.weeks ?? 0,
      best_weeks: over.weeks ?? 0,
      last_active_week: null,
      next_milestone:
        over.nextMilestone === undefined
          ? null
          : over.nextMilestone == null
            ? null
            : { weeks: over.nextMilestone, reward: over.nextMilestone },
    },
    stats: { tournaments_played: 0, wins_total: 0 },
    legion: null,
    trophies: [],
  };
}

describe('nextCelebration', () => {
  it('never celebrates on a first (empty) snapshot — just baselines', () => {
    const { event, state } = nextCelebration({}, profile({ rank: 'knight', weeks: 2, nextMilestone: 3 }));
    expect(event).toBeNull();
    expect(state).toEqual({ rank_code: 'knight', pending_milestone: 3, celebrated_milestone: null });
  });

  it('fires a rank-up when the rank code changes from a known value', () => {
    const prev: CelebrationState = { rank_code: 'knight', pending_milestone: 3, celebrated_milestone: null };
    const { event } = nextCelebration(prev, profile({ rank: 'bishop', weeks: 2, nextMilestone: 3 }));
    expect(event).toEqual({ type: 'rankUp', rank_code: 'bishop' });
  });

  it('does not re-fire a rank-up when the rank is unchanged', () => {
    const prev: CelebrationState = { rank_code: 'bishop', pending_milestone: 3, celebrated_milestone: null };
    const { event } = nextCelebration(prev, profile({ rank: 'bishop', weeks: 2, nextMilestone: 3 }));
    expect(event).toBeNull();
  });

  it('fires a streak milestone once the pending target is reached', () => {
    const prev: CelebrationState = { rank_code: 'knight', pending_milestone: 3, celebrated_milestone: null };
    const { event, state } = nextCelebration(prev, profile({ rank: 'knight', weeks: 3, nextMilestone: 5 }));
    expect(event).toEqual({ type: 'streakMilestone', weeks: 3 });
    expect(state.pending_milestone).toBe(5);
    expect(state.celebrated_milestone).toBe(3);
  });

  it('does not re-fire an already-celebrated milestone', () => {
    const prev: CelebrationState = { rank_code: 'knight', pending_milestone: 5, celebrated_milestone: 3 };
    // still short of 5 → no fire
    const { event } = nextCelebration(prev, profile({ rank: 'knight', weeks: 4, nextMilestone: 5 }));
    expect(event).toBeNull();
  });

  it('prioritizes rank-up and holds the milestone for the next load', () => {
    const prev: CelebrationState = { rank_code: 'knight', pending_milestone: 3, celebrated_milestone: null };
    const p = profile({ rank: 'bishop', weeks: 3, nextMilestone: 5 });
    const first = nextCelebration(prev, p);
    expect(first.event).toEqual({ type: 'rankUp', rank_code: 'bishop' });
    // streak fields preserved so the milestone survives.
    expect(first.state.pending_milestone).toBe(3);
    const second = nextCelebration(first.state, p);
    expect(second.event).toEqual({ type: 'streakMilestone', weeks: 3 });
  });
});

import { describe, expect, it } from 'vitest';
import { DEFAULT_CONFIG } from '../economy';
import { UNLINKED_PROFILE, buildProfile, nextMilestone } from '../profile';

const RANKS = [
  { code: 'pawn', name_ru: 'Пешка', name_kk: 'Сарбаз', name_en: 'Pawn', min_xp: 0, sort_order: 1 },
  { code: 'knight', name_ru: 'Конь', name_kk: 'Ат', name_en: 'Knight', min_xp: 10, sort_order: 2 },
  { code: 'bishop', name_ru: 'Слон', name_kk: 'Піл', name_en: 'Bishop', min_xp: 30, sort_order: 3 },
  { code: 'rook', name_ru: 'Ладья', name_kk: 'Тура', name_en: 'Rook', min_xp: 70, sort_order: 4 },
];

describe('buildProfile', () => {
  it('shapes a linked profile with rank progress + stats', () => {
    const player = {
      xp_total: 47.5,
      coin_balance: 40,
      rank_code: 'bishop',
      tournaments_played: 8,
      wins_total: 21.5,
    };
    const streak = { current_weeks: 2, best_weeks: 4, run_start_week: '2026-01-05', last_active_week: '2026-01-12' };
    const p = buildProfile('s1', player, streak, RANKS, DEFAULT_CONFIG);

    expect(p.linked).toBe(true);
    expect(p.student_id).toBe('s1');
    expect(p.xp).toBe(47.5);
    expect(p.coins).toBe(40);
    expect(p.rank?.code).toBe('bishop');
    expect(p.rank_progress.next_code).toBe('rook');
    expect(p.rank_progress.xp_into_rank).toBe(17.5); // 47.5 − 30
    expect(p.rank_progress.xp_for_next).toBe(40); // 70 − 30
    expect(p.rank_progress.pct).toBeCloseTo(43.75);
    expect(p.streak.current_weeks).toBe(2);
    expect(p.streak.next_milestone).toEqual({ weeks: 3, reward: 3 });
    expect(p.stats).toEqual({ tournaments_played: 8, wins_total: 21.5 });
  });

  it('handles a fresh player with no rows (zero-start)', () => {
    const p = buildProfile('s2', null, null, RANKS, DEFAULT_CONFIG);
    expect(p.xp).toBe(0);
    expect(p.coins).toBe(0);
    expect(p.rank?.code).toBe('pawn');
    expect(p.streak.current_weeks).toBe(0);
    expect(p.stats.tournaments_played).toBe(0);
  });

  it('coerces numeric strings from Postgres', () => {
    const p = buildProfile('s3', { xp_total: '12.5', coin_balance: '10', rank_code: 'knight', tournaments_played: 3, wins_total: '5' }, null, RANKS, DEFAULT_CONFIG);
    expect(p.xp).toBe(12.5);
    expect(p.rank?.code).toBe('knight');
  });
});

describe('nextMilestone', () => {
  it('returns the smallest milestone above the current streak', () => {
    expect(nextMilestone(DEFAULT_CONFIG, 0)).toEqual({ weeks: 3, reward: 3 });
    expect(nextMilestone(DEFAULT_CONFIG, 3)).toEqual({ weeks: 5, reward: 5 });
    expect(nextMilestone(DEFAULT_CONFIG, 10)).toEqual({ weeks: 20, reward: 25 });
    expect(nextMilestone(DEFAULT_CONFIG, 20)).toBeNull();
  });
});

describe('UNLINKED_PROFILE', () => {
  it('is hidden/empty (D-8)', () => {
    expect(UNLINKED_PROFILE).toEqual({ linked: false });
  });
});

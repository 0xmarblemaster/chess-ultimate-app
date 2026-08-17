import { describe, expect, it } from 'vitest';
import {
  DEFAULT_CONFIG,
  computeStreak,
  computeTournamentAward,
  isoWeekMonday,
  normalizeConfig,
  rankForXp,
  rankProgress,
  roundHalf,
} from '../economy';

const RANKS = [
  { code: 'pawn', name_ru: 'Пешка', name_kk: 'Сарбаз', name_en: 'Pawn', min_xp: 0, sort_order: 1 },
  { code: 'knight', name_ru: 'Конь', name_kk: 'Ат', name_en: 'Knight', min_xp: 10, sort_order: 2 },
  { code: 'bishop', name_ru: 'Слон', name_kk: 'Піл', name_en: 'Bishop', min_xp: 30, sort_order: 3 },
  { code: 'rook', name_ru: 'Ладья', name_kk: 'Тура', name_en: 'Rook', min_xp: 70, sort_order: 4 },
  { code: 'queen', name_ru: 'Ферзь', name_kk: 'Уәзір', name_en: 'Queen', min_xp: 150, sort_order: 5 },
  { code: 'king', name_ru: 'Король', name_kk: 'Патша', name_en: 'King', min_xp: 300, sort_order: 6 },
];

describe('computeTournamentAward — half-point math (D-2)', () => {
  it('awards participation + score × win rate', () => {
    expect(computeTournamentAward(DEFAULT_CONFIG, 'league_c', 1)).toEqual({ xp: 2, coins: 2, wins: 1 });
    expect(computeTournamentAward(DEFAULT_CONFIG, 'league_b', 3)).toEqual({ xp: 7, coins: 7, wins: 3 });
    expect(computeTournamentAward(DEFAULT_CONFIG, 'rated', 2)).toEqual({ xp: 7, coins: 7, wins: 2 });
  });

  it('a draw in league C is +0.5 XP (0.5 granularity)', () => {
    expect(computeTournamentAward(DEFAULT_CONFIG, 'league_c', 0.5)).toEqual({ xp: 1.5, coins: 1.5, wins: 0.5 });
  });

  it('participation only for an unknown / unmapped kind', () => {
    expect(computeTournamentAward(DEFAULT_CONFIG, 'mystery', 5)).toEqual({ xp: 1, coins: 1, wins: 5 });
  });

  it('coins follow coin_per_xp', () => {
    const cfg = normalizeConfig({ coin_per_xp: 2 });
    expect(computeTournamentAward(cfg, 'league_c', 1).coins).toBe(4);
  });

  it('guards against negative / NaN scores', () => {
    expect(computeTournamentAward(DEFAULT_CONFIG, 'league_c', -3).xp).toBe(1);
    expect(computeTournamentAward(DEFAULT_CONFIG, 'league_c', NaN).xp).toBe(1);
  });
});

describe('rankForXp / rankProgress — boundary math', () => {
  it('picks the highest rank at or below the xp threshold', () => {
    expect(rankForXp(RANKS, 0)?.code).toBe('pawn');
    expect(rankForXp(RANKS, 9.5)?.code).toBe('pawn');
    expect(rankForXp(RANKS, 10)?.code).toBe('knight'); // boundary is inclusive
    expect(rankForXp(RANKS, 29.5)?.code).toBe('knight');
    expect(rankForXp(RANKS, 30)?.code).toBe('bishop');
    expect(rankForXp(RANKS, 300)?.code).toBe('king');
    expect(rankForXp(RANKS, 99999)?.code).toBe('king');
  });

  it('computes progress toward the next rank', () => {
    const p = rankProgress(RANKS, 20);
    expect(p.current?.code).toBe('knight');
    expect(p.next?.code).toBe('bishop');
    expect(p.xpIntoRank).toBe(10);
    expect(p.xpForNext).toBe(20);
    expect(p.pct).toBe(50);
  });

  it('caps at 100% for the top rank', () => {
    const p = rankProgress(RANKS, 500);
    expect(p.current?.code).toBe('king');
    expect(p.next).toBeNull();
    expect(p.pct).toBe(100);
  });
});

describe('isoWeekMonday', () => {
  it('normalizes any day to its ISO Monday', () => {
    // 2026-01-07 is a Wednesday → Monday 2026-01-05
    expect(isoWeekMonday('2026-01-07')).toBe('2026-01-05');
    expect(isoWeekMonday('2026-01-05')).toBe('2026-01-05');
    // Sunday belongs to the week that started the previous Monday
    expect(isoWeekMonday('2026-01-11')).toBe('2026-01-05');
    expect(isoWeekMonday('2026-01-12T09:53:32Z')).toBe('2026-01-12');
  });
});

describe('computeStreak — reset / freeze (§5.5, D-7)', () => {
  const cfg = DEFAULT_CONFIG.streak; // bonus_min 2, bonus_xp 1, milestones 3/5/10/20

  it('builds a streak over consecutive weeks with bonuses + milestone', () => {
    const r = computeStreak(['2026-01-05', '2026-01-12', '2026-01-19'], cfg);
    expect(r.current_weeks).toBe(3);
    expect(r.best_weeks).toBe(3);
    const bonuses = r.awards.filter((a) => a.kind === 'streak_bonus');
    const milestones = r.awards.filter((a) => a.kind === 'streak_milestone');
    expect(bonuses).toHaveLength(2); // weeks 2 and 3 (streak ≥ 2)
    expect(milestones).toHaveLength(1); // reached 3 weeks
    expect(milestones[0].amount).toBe(3);
  });

  it('resets to 0 after a missed (non-frozen) week', () => {
    const r = computeStreak(['2026-01-05', '2026-01-12', '2026-01-26'], cfg); // 01-19 missed
    expect(r.current_weeks).toBe(1);
    expect(r.best_weeks).toBe(2);
    expect(r.awards.filter((a) => a.kind === 'streak_bonus')).toHaveLength(1);
  });

  it('holiday freeze windows are transparent — no reset, streak continues', () => {
    const frozen = {
      ...cfg,
      freeze_windows: [{ from: '2026-01-19', until: '2026-01-19', label: 'каникулы' }],
    };
    // participation weeks 01-05, 01-12, then skip 01-19 (frozen), resume 01-26
    const r = computeStreak(['2026-01-05', '2026-01-12', '2026-01-26'], frozen);
    expect(r.current_weeks).toBe(3); // not reset
    expect(r.awards.filter((a) => a.kind === 'streak_milestone')).toHaveLength(1);
  });

  it('disables bonuses when bonus_xp = 0', () => {
    const r = computeStreak(['2026-01-05', '2026-01-12', '2026-01-19'], { ...cfg, bonus_xp: 0 });
    expect(r.awards.filter((a) => a.kind === 'streak_bonus')).toHaveLength(0);
  });

  it('milestone idempotency suffix ties to the run start', () => {
    const r = computeStreak(['2026-01-05', '2026-01-12', '2026-01-19'], cfg);
    const ms = r.awards.find((a) => a.kind === 'streak_milestone');
    expect(ms?.idempotencySuffix).toBe(':2026-01-05:3');
  });
});

describe('roundHalf', () => {
  it('rounds to 0.5 granularity', () => {
    expect(roundHalf(1.4)).toBe(1.5);
    expect(roundHalf(1.24)).toBe(1);
    expect(roundHalf(2.75)).toBe(3);
  });
});

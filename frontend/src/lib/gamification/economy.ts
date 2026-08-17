/**
 * Gamification core economy — pure, framework-free logic.
 *
 * Everything here is deterministic and side-effect-free so it can be unit
 * tested without a database. The sync engine and profile API consume these
 * functions; all rates come from the org's gamification_settings (D-6, no
 * hardcoded economy in code paths — the defaults below are only used to
 * seed/repair a missing settings row).
 */

// ---------------------------------------------------------------------------
// Config shape (mirrors gamification_settings.config JSONB)
// ---------------------------------------------------------------------------

export interface StreakConfig {
  bonus_min: number;
  bonus_xp: number;
  milestones: Record<string, number>; // { "3": 3, "5": 5, ... }
  freeze_windows: Array<{ from: string; until: string; label?: string }>;
}

export interface GamificationConfig {
  participation_xp: number;
  win_xp: Record<string, number>; // keyed by CE tournament kind
  coin_per_xp: number;
  top_n: number;
  min_tournaments_for_trophy: number;
  count_unlinked_in_standings: boolean;
  streak: StreakConfig;
  league_thresholds: { a_min: number; b_min: number };
}

/** Sensible defaults (D-6). Runtime reads the settings row; this only seeds it. */
export const DEFAULT_CONFIG: GamificationConfig = {
  participation_xp: 1,
  win_xp: { league_c: 1, league_b: 2, razryad_4: 3, razryad_3: 3, rated: 3, pro: 5 },
  coin_per_xp: 1,
  top_n: 5,
  min_tournaments_for_trophy: 3,
  count_unlinked_in_standings: false,
  streak: {
    bonus_min: 2,
    bonus_xp: 1,
    milestones: { '3': 3, '5': 5, '10': 10, '20': 25 },
    freeze_windows: [],
  },
  league_thresholds: { a_min: 801, b_min: 450 },
};

/** Merge a (possibly partial) stored config over the defaults. */
export function normalizeConfig(raw: unknown): GamificationConfig {
  const c = (raw ?? {}) as Partial<GamificationConfig>;
  return {
    ...DEFAULT_CONFIG,
    ...c,
    win_xp: { ...DEFAULT_CONFIG.win_xp, ...(c.win_xp ?? {}) },
    streak: {
      ...DEFAULT_CONFIG.streak,
      ...(c.streak ?? {}),
      milestones: { ...DEFAULT_CONFIG.streak.milestones, ...(c.streak?.milestones ?? {}) },
      freeze_windows: c.streak?.freeze_windows ?? DEFAULT_CONFIG.streak.freeze_windows,
    },
    league_thresholds: { ...DEFAULT_CONFIG.league_thresholds, ...(c.league_thresholds ?? {}) },
  };
}

/** Round to 0.5 granularity (draws → half points). Guards float drift. */
export function roundHalf(n: number): number {
  return Math.round(n * 2) / 2;
}

// ---------------------------------------------------------------------------
// Tournament awards — xp = participation + score × win_xp[kind]  (§5.1, D-2)
// ---------------------------------------------------------------------------

export interface TournamentAward {
  xp: number;
  coins: number;
  /** Swiss score = wins + 0.5×draws; the half-point-aware "wins" contribution. */
  wins: number;
}

export function winXpForKind(config: GamificationConfig, kind: string | null | undefined): number {
  if (!kind) return 0;
  return config.win_xp[kind] ?? 0;
}

/**
 * Award for one tournament result. `score` is CE `tournament_results.score`
 * (already wins + 0.5×draws). Participation is always granted for showing up.
 */
export function computeTournamentAward(
  config: GamificationConfig,
  kind: string | null | undefined,
  score: number,
): TournamentAward {
  const winXp = winXpForKind(config, kind);
  const safeScore = Number.isFinite(score) && score > 0 ? score : 0;
  const xp = roundHalf(config.participation_xp + safeScore * winXp);
  return {
    xp,
    coins: roundHalf(xp * config.coin_per_xp),
    wins: roundHalf(safeScore),
  };
}

// ---------------------------------------------------------------------------
// Ranks — derived from lifetime XP against the ladder  (§6)
// ---------------------------------------------------------------------------

export interface RankRow {
  code: string;
  name_ru: string;
  name_kk: string;
  name_en: string;
  min_xp: number;
  icon_url?: string | null;
  sort_order: number;
}

export interface RankProgress {
  current: RankRow | null;
  next: RankRow | null;
  xpIntoRank: number; // xp above current rank's floor
  xpForNext: number; // span from current floor to next floor (0 if maxed)
  pct: number; // 0..100 progress toward next rank
}

/** Highest rank whose min_xp ≤ xp. Ranks need not be pre-sorted. */
export function rankForXp(ranks: RankRow[], xp: number): RankRow | null {
  const sorted = [...ranks].sort((a, b) => a.min_xp - b.min_xp);
  let current: RankRow | null = null;
  for (const r of sorted) {
    if (xp >= r.min_xp) current = r;
    else break;
  }
  // If no rank has min_xp ≤ xp (e.g. all floors > 0), fall back to the lowest.
  return current ?? sorted[0] ?? null;
}

export function rankProgress(ranks: RankRow[], xp: number): RankProgress {
  const sorted = [...ranks].sort((a, b) => a.min_xp - b.min_xp);
  const current = rankForXp(sorted, xp);
  if (!current) return { current: null, next: null, xpIntoRank: 0, xpForNext: 0, pct: 100 };
  const next = sorted.find((r) => r.min_xp > current.min_xp) ?? null;
  const xpIntoRank = roundHalf(Math.max(0, xp - current.min_xp));
  if (!next) return { current, next: null, xpIntoRank, xpForNext: 0, pct: 100 };
  const xpForNext = roundHalf(next.min_xp - current.min_xp);
  const pct = xpForNext > 0 ? Math.min(100, Math.max(0, (xpIntoRank / xpForNext) * 100)) : 100;
  return { current, next, xpIntoRank, xpForNext, pct };
}

// ---------------------------------------------------------------------------
// ISO-week helpers (UTC to avoid TZ drift)
// ---------------------------------------------------------------------------

/** Monday (YYYY-MM-DD) of the ISO week containing `dateStr` (date or datetime). */
export function isoWeekMonday(dateStr: string): string {
  const d = new Date(dateStr.slice(0, 10) + 'T00:00:00Z');
  const day = d.getUTCDay(); // 0=Sun..6=Sat
  const shift = day === 0 ? -6 : 1 - day; // back to Monday
  d.setUTCDate(d.getUTCDate() + shift);
  return d.toISOString().slice(0, 10);
}

function addDaysUTC(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Inclusive list of Monday dates from `startMonday` to `endMonday`, step 1 week. */
function weekRange(startMonday: string, endMonday: string): string[] {
  const out: string[] = [];
  let w = startMonday;
  // guard against pathological ranges
  for (let i = 0; i < 10000 && w <= endMonday; i++) {
    out.push(w);
    w = addDaysUTC(w, 7);
  }
  return out;
}

function isWeekFrozen(weekMonday: string, windows: StreakConfig['freeze_windows']): boolean {
  for (const win of windows ?? []) {
    if (!win?.from || !win?.until) continue;
    const from = isoWeekMonday(win.from);
    const until = isoWeekMonday(win.until);
    if (weekMonday >= from && weekMonday <= until) return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Streaks — tournament-week streaks (§5.5, D-7)
// ---------------------------------------------------------------------------

export interface StreakBonusEntry {
  kind: 'streak_bonus' | 'streak_milestone';
  week: string; // ISO Monday the award is attributed to (occurred_at)
  amount: number; // XP (coins mirror at coin_per_xp)
  idempotencySuffix: string; // appended after "streak:"/"streak_ms:" + student
}

export interface StreakResult {
  current_weeks: number;
  best_weeks: number;
  run_start_week: string | null;
  last_active_week: string | null;
  awards: StreakBonusEntry[];
}

/**
 * Deterministically replay a student's participation weeks to produce the
 * streak state and the full list of streak bonus/milestone awards.
 *
 * Frozen weeks (school holidays) are transparent: they neither extend nor
 * break a run. A non-frozen week with no participation resets the run to 0.
 * Because milestone keys are tied to (run_start_week, milestone) and per-week
 * bonus keys to the week, re-running over the same history is idempotent.
 *
 * @param occurredAts tournament dates (any order, may repeat within a week)
 */
export function computeStreak(occurredAts: string[], cfg: StreakConfig): StreakResult {
  const participation = new Set(occurredAts.map((d) => isoWeekMonday(d)));
  const weeks = [...participation].sort();
  const result: StreakResult = {
    current_weeks: 0,
    best_weeks: 0,
    run_start_week: null,
    last_active_week: null,
    awards: [],
  };
  if (weeks.length === 0) return result;

  const milestoneThresholds = Object.keys(cfg.milestones ?? {})
    .map((k) => parseInt(k, 10))
    .filter((n) => Number.isFinite(n) && n > 0)
    .sort((a, b) => a - b);

  let run = 0;
  let runStart: string | null = null;

  for (const week of weekRange(weeks[0], weeks[weeks.length - 1])) {
    if (isWeekFrozen(week, cfg.freeze_windows)) continue; // transparent
    if (participation.has(week)) {
      run += 1;
      if (run === 1) runStart = week;
      result.last_active_week = week;
      // Per-tournament (per-week) streak bonus while streak ≥ bonus_min.
      if (cfg.bonus_xp > 0 && run >= cfg.bonus_min) {
        result.awards.push({
          kind: 'streak_bonus',
          week,
          amount: cfg.bonus_xp,
          idempotencySuffix: `:${week}`,
        });
      }
      // One-time milestone when the run first reaches a threshold.
      if (milestoneThresholds.includes(run)) {
        const amount = cfg.milestones[String(run)];
        if (amount > 0) {
          result.awards.push({
            kind: 'streak_milestone',
            week,
            amount,
            idempotencySuffix: `:${runStart}:${run}`,
          });
        }
      }
    } else {
      run = 0;
      runStart = null;
    }
    if (run > result.best_weeks) result.best_weeks = run;
  }

  result.current_weeks = run;
  result.run_start_week = runStart;
  return result;
}

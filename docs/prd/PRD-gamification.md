# PRD: Chess Empire Gamification System

**Status:** v2 — all open questions resolved (decisions log in §15), ready for Phase 1 build
**Date:** 2026-08-17 (v1 same day; v2 incorporates director/Alex answers)
**Source:** Concept spec from Chess Empire school director (Russian original, 17 sections)
**Surfaces:** `chess-empire.chesster.io` (primary), Chesster admin panel
**Related:** `EMPIRE_PAYMENTS_PRD.md` (coin purchase rail), `docs/adr/0005-subdomain-per-tenant-multi-tenancy.md`

---

## 1. Overview

A two-part gamification system for kids at the Chess Empire chess school:

1. **Personal progression** — XP (earned only, never spent), ranks (Пешка → Король), coins (earned or purchased, spendable), streaks, a customizable avatar, a cosmetics shop, and permanent trophy items.
2. **Team competition** — every branch is a **Legion**; legions compete in seasonal **Legion Cups** scored by each legion's **Top-N** (default 5) players, neutralizing branch-size advantage.

**Core value separation (the design's contract, must never be violated):**

| Value | Earn | Buy | Spend | Lose |
|---|---|---|---|---|
| XP | ✅ chess activity + streaks | ❌ never | ❌ never | ❌ never |
| Coins | ✅ 1:1 with earned XP | ✅ real money (KZT) | ✅ cosmetics | via spending only |
| Trophies | ✅ specific achievements | ❌ never | ❌ never | ❌ never |

Buying coins grants **0 XP**. Rank is derived from XP only. All purchasable items are cosmetic.

Although built for Chess Empire first, everything is **org-scoped** (white-label pattern) so any future tenant can enable it.

## 2. Goals / Non-Goals

**Goals (MVP, spec §17):** real player profile (XP, rank, coins, legion, stats), XP+coin awarding from tournament results, tournament streaks as a bonus XP/coin source, rank ladder, coin purchase, avatar with slots, 20–30 cosmetic items (placeholder art), shop, legions, Top-N standings, Legion Cup table, seasons, one season trophy type, trophy history, full admin configurability.

**Non-goals (post-MVP, spec §17):** quests, chests/loot boxes (never — kids product), item trading/gifting, additional trophy types, special events, XP from non-tournament sources beyond streaks (lessons/puzzles/attendance — architecture must allow it, MVP doesn't ship it).

## 3. Current-State Audit — what exists and what happens to it

This PRD **replaces mock surfaces and repairs broken pipelines**, not just adds new screens.

| Existing surface | Location | Today | Action |
|---|---|---|---|
| `XPDisplay` / `XPGain` | `frontend/src/components/gamification/XPDisplay.tsx` | Presentational, fed `useState(450)` mock | **Keep component**, feed from real profile API; add rank context next to it |
| `StreakBanner` / `StreakMini` | `components/gamification/StreakBanner.tsx` | Mock `useState(5)` | **Repurpose** as the tournament-streak banner fed by real streak data (§5.5). Copy changes from "day streak" to tournament-week streak |
| `LessonPath`, `CelebrationOverlay` | `components/gamification/` | Mock progress | Reuse `CelebrationOverlay` for XP-gain / rank-up / item-unlock / streak-milestone moments |
| Profile page | `app/profile/page.tsx` | Hardcoded XP, streak, 6 fake achievements, fake stats | **Rewrite** as the real gamified profile (§9.1) |
| Dashboard | `app/dashboard/ChessterDashboard.tsx` | Mock XP/streak | Feed real XP/rank; CE surface uses EmpireHomePage instead |
| Empire homepage | `components/empire/EmpireHomePage.tsx` | Real ratings/rank; achievements strip **wired but never populated** by `empire-homepage-render.tsx` | Populate strip; add rank/XP/coins/legion/streak widgets (§9.2) |
| CE achievements | CE edge fn `analytics-students?action=achievements` | **Computes on the fly**, returns `{name, description}` only — ignores the seeded `achievements`/`student_achievements` tables with i18n/icons/tiers; Chesster's `CEAchievement` type expects `id/icon_url/earned_at` it never gets | **Fix edge function** to read the real tables and return full shape; seed `student_achievements` from the same signals (§8.4) |
| League definitions | 3 conflicting scales: CE view (`>800`→A, `≥450`→B), Chesster `lib/league.ts` (`≥900`/`≥500`), Chesster `player_ratings` (C/B/A/Master by 1400/1800/2200) | Inconsistent | **Canonical per-org league config** in gamification settings; CE org uses CE DB thresholds; `lib/league.ts` fallback reads org config (§8.5) |
| Leaderboard | `app/leaderboard/page.tsx` → Flask `/api/ratings/leaderboard` | Real, Chesster-native ratings | Untouched; new Legion standings are a separate surface |

## 4. Identity & Subject Model

**The gamification subject is the CE `student_id`** (Supabase `papgcizhfkngubwofjuo`), not the Clerk user:

- Tournament results key on `student_id`; many students have no Chesster account yet.
- XP/coins **accrue for all active students regardless of app signup** — the ledger is keyed by `student_id`, so nothing is lost while a kid is unlinked.
- **Unlinked students are hidden everywhere** (decision D-8): they do not appear in legion member lists, Top-N, or standings, and their season XP does **not** count toward legion totals until they link. On linking (existing `organization_members` flow, `lib/chess-empire-member.ts`), their accrued XP/coins/rank become visible instantly and their season points join the legion score on the next standings refresh. Side effect we lean into: *linking a strong player immediately boosts the legion* — a built-in reason for kids to get classmates onboarded. Config flag `count_unlinked_in_standings` (default `false`) preserves the option to flip this later.
- Clerk user ↔ student resolution reuses the existing verified-link machinery. Coin **spending** and purchases require a verified linked account (parent-verified).

All new tables live in **Chesster's Supabase** (`qtzujwiqzbgyhdgulvcd`), org-scoped via `organization_id`. The CE DB stays **read-only** to us — the XP engine ingests from it, never writes back.

## 5. XP Engine

### 5.1 Sources — tournaments

Ingested from CE `tournament_results` (joined to `tournaments_uploads` for `kind` + `tournament_date`):

| Event | XP (default, admin-editable) |
|---|---|
| Tournament participation | +1 |
| Game won, `league_c` tournament | +1 per win |
| Game won, `league_b` tournament | +2 per win |
| Game won, `razryad_4` / `razryad_3` tournament | +3 per win (the "league A" rate — D-1) |
| Game won, `rated` tournament | +3 per win (default; admin-editable) |
| Game won, "Pro" tier | +5 per win (reserved config slot — no CE kind maps to it yet) |

**Wins are per game, draws count half (D-2).** Swiss `score` already equals `wins + 0.5 × draws`, so the award formula is simply:

```
xp = participation_xp + score × win_xp[kind]
```

A draw in league C = +0.5 XP. **XP and coin amounts therefore have 0.5 granularity** — ledger columns are `NUMERIC(8,1)`, and the UI renders halves («47.5 XP»). If the director later prefers whole numbers, doubling every rate in admin config achieves it without migration.

### 5.2 Ledger (append-only, idempotent)

Every award is a row in `xp_ledger`. **Never** update a balance column; balances are `SUM(amount)` (materialized in `player_gamification` for read speed, recomputed transactionally).

- `idempotency_key = 'ce_result:' + tournament_results.id` (UNIQUE) — re-uploaded Swiss-Manager files and re-runs of the sync job can never double-award.
- `occurred_at = tournament_date` (not ingestion time) — **season attribution follows the tournament date**, so late uploads land in the right season.
- If a CE result row is deleted/re-uploaded (admin fixes a bad import), a compensating negative entry reverses it (`reason='ce_result_reversed'`); the new upload's rows award fresh. Sync detects this by diffing known result IDs per upload.

### 5.3 Ingestion

CE has no webhooks (browser admin writes directly to Supabase). **Cron sync** (every 15 min, `CRON_SECRET`-guarded route `POST /api/chess-empire/gamification/sync`, same pattern as Empire Payments PRD): cursor on `tournament_results.created_at`, pull new rows via CE service key, award XP+coins in one transaction per row, then update streaks (§5.5) and refresh standings (§8.3). Manual "Sync now" button in admin.

**Launch is zero-start (D-5):** the sync cursor initializes at the launch timestamp; historical results are never awarded. Everyone begins at Пешка / 0 XP / 0 coins, and the first season's race starts fair. Tournament/win counters on the profile likewise count from launch (derived from the ledger) so numbers stay mutually consistent. The backfill script from v1 is retained behind the admin Ops tab as a disabled capability, in case the director ever changes course.

### 5.4 Coins coupling

**1 earned XP = 1 earned coin** (D-3; rate `coin_per_xp` admin-editable). The sync writes a paired `coin_ledger` row with the same idempotency key. Separate ledgers from day one so the coupling can change later without migration. Streak bonuses (§5.5) award coins at the same 1:1 rate.

### 5.5 Streaks (new — D-7)

The director asked for streaks as an earnable XP/coin source. Since the MVP's only activity signal is tournaments, the streak unit is the **tournament week**:

- A student's streak = number of **consecutive ISO weeks with ≥1 tournament participation**. Miss a week → streak resets to 0 (grace rules below).
- Computed during sync from `occurred_at` (tournament date), stored in `player_streaks` (current, best, last active week).

**Earning model — two admin-configurable layers:**

1. **Per-tournament streak bonus:** while streak ≥ `streak_bonus_min` (default 2), every tournament participation earns `streak_bonus_xp` extra (default +1 XP/+1 coin) on top of normal awards. Keeps a small always-on drip that rewards consistency without dwarfing wins.
2. **Milestone bonuses (one-time per streak run):** reaching a milestone week count pays a one-off bonus. Defaults:

| Streak reaches | Bonus XP (+coins 1:1) |
|---|---|
| 3 weeks | +3 |
| 5 weeks | +5 |
| 10 weeks | +10 |
| 20 weeks | +25 |

Both layers are rows in the normal ledgers (`reason='streak_bonus'` / `'streak_milestone'`, idempotency key `streak:{student}:{iso_week}` / `streak_ms:{student}:{run_start_week}:{milestone}`) — so they flow into ranks, coins, and **season/legion points** like any other XP.

**Guardrails:**
- Milestone table and both rates fully admin-editable (Rules tab); setting `streak_bonus_xp=0` and emptying the table disables the system.
- **Holiday grace:** admin can mark date ranges as "school holidays" (`streak_freeze_windows` in config); weeks inside them neither extend nor break streaks. Prevents mass resets over каникулы, which would otherwise punish everyone and poison the feature.
- Streak bonuses are earned XP like any other — they count toward season points by design (keeps the model simple; magnitudes are small relative to tournament XP).
- UI: `StreakBanner` repurposed (🔥 «5 недель подряд!»), next-milestone progress shown, `CelebrationOverlay` on milestone hit.

**Post-MVP extension (architecture-ready, not built):** the CE DB already tracks lesson **attendance** — an attendance-week streak is the natural second streak type and reuses the same ledger/milestone machinery with a different source signal.

## 6. Ranks

Derived from lifetime XP against org-scoped `rank_definitions`:

| Rank | code | Default min XP |
|---|---|---|
| Пешка | `pawn` | 0 |
| Конь | `knight` | 10 |
| Слон | `bishop` | 30 |
| Ладья | `rook` | 70 |
| Ферзь | `queen` | 150 |
| Король | `king` | 300 |

Thresholds, names (i18n ru/kk/en), icons, and even the list itself are admin-editable (spec §4, §15). Rank recomputed on every XP award; rank-up fires a `CelebrationOverlay` + optional Telegram/notification hook (post-MVP). Rank never decreases (XP never decreases except admin reversal of erroneous imports).

**Naming collision:** CE already has razryad ranks and a level/lesson rank. UI must label this as **«Ранг»** distinct from «Разряд»; profile shows both.

## 7. Coins, Shop, Items, Avatar

### 7.1 Coin ledger

Same append-only pattern. `source ∈ (earn_xp, streak, purchase, spend, admin_adjust, refund)`. Balance = SUM; spending goes through a Postgres RPC (`spend_coins(student, item)`) that row-locks, checks balance ≥ price, inserts negative ledger row + inventory row atomically. **No client-side writes anywhere** (RLS: authenticated users read own rows only; writes service-role only). Balances carry 0.5 granularity (§5.1); shop prices are whole numbers.

### 7.2 Item catalog

`items`: `id, organization_id, sku, name_{ru,kk,en}, description_{...}, slot, rarity ∈ (common, rare, epic, legendary), price_coins (NULL for trophies), kind ∈ (purchasable, trophy, default), art_url, anim_url, available bool, available_from/until, acquisition_note, sort_order`.

- **Purchasable** — bought with coins (thus indirectly with money). Never grants XP or chess advantage.
- **Trophy** — `price_coins IS NULL`, unobtainable via shop; granted only by the season-award job (or manual admin grant with reason). Card shows provenance: *«Чемпион Кубка Легионов — Осень 2026»*.
- **Default** — free starter items (e.g., standard blue shield), auto-granted on profile creation.

MVP slots (admin-extensible enum in config): `shield`, `armor`, `cloak`, `helmet`, `weapon`, `pet`, `background`, `frame`, `effect`. MVP ships **20–30 items across ≥5 slots**.

**Art is placeholder-first (D-9):** launch with generated placeholder art (nano-banana batch under one style guide — consistent silhouette/palette per rarity so the shop doesn't look broken). The director will submit final designs later; `art_url` is swappable per item via admin upload (reuses `branding/upload` storage pattern) with zero schema impact. Placeholder items are flagged `is_placeholder_art` so admin can track replacement progress.

### 7.3 Inventory & loadout

- `player_items`: `student_id, item_id, acquired_via ∈ (purchase, default, trophy, admin_grant), season_id (for trophies), acquired_at`. UNIQUE(student, item). Trophies are permanent — no delete path exposed.
- `player_loadout`: one equipped item per slot. Avatar renderer composites slot layers over the base character.

### 7.4 Shop UI

Grid by slot with rarity styling, price, owned/equipped states; insufficient-balance state deep-links to coin purchase. Trophy items appear in a separate **«Зал славы»** (trophy case) section of the profile — visible provenance, never in the shop.

## 8. Legions, Seasons, Legion Cup

### 8.1 Legions

`legions`: `id, organization_id, name, totem, crest_url, color_primary/secondary, ce_branch_id` (maps to CE `branches.id`; admin-editable mapping per spec §15 — also covers branch merges). Crests launch as placeholders like items (D-9).

**Branch transfers: points move with the kid (D-11).** Standings are computed by grouping each student's season XP under their **current** branch→legion mapping (refreshed from CE `students.branch_id` on every sync) — not by per-row attribution. A mid-season transfer therefore moves the student's entire season score to the new legion and removes it from the old one at the next refresh. `xp_ledger.legion_id` is still snapshotted at award time, but strictly as an audit trail, never for scoring.

### 8.2 Seasons

`seasons`: `id, organization_id, name ("Осень 2026"), starts_at, ends_at, status ∈ (draft, active, closed), top_n (default 5), trophy_item_id, winner_legion_id, closed_at`. One active season per org. XP rows with `occurred_at` inside the window count toward it.

**Cadence is deliberately unscheduled (D-10):** no hardcoded quarterly rhythm. Admin creates each season with arbitrary dates in the Seasons tab; close is **auto-freeze at `ends_at` + explicit admin confirm** before results finalize and trophies grant. Between seasons the Cup page shows the last archive + «Скоро новый сезон».

### 8.3 Scoring & standings

**1 legion point = 1 season XP = 1 coin earned (D-3).** A student's season score = SUM of their `xp_ledger` amounts (all reasons, streaks included) with `occurred_at` inside the season window; a legion's score = sum of its **Top-N linked** students' season scores (unlinked excluded per D-8). Recomputed on every sync (a kid entering Top-N changes the legion total — this is inherent; standings are a query, not a stored number). Materialized view or cached query, refreshed post-sync:

- Legion table: place, points, gap to neighbors («До первого места: 25 очков»).
- Intra-legion: student's own rank, Top-N list, and «До попадания в ТОП-5: 7 очков» — the second-ladder motivation (spec §12).
- Ties: shared placement; tiebreak by season wins, then earlier attainment of the score.

### 8.4 Season close & trophies

Auto-freeze at `ends_at`, then admin confirms close (D-10): standings frozen into `season_results` (JSONB snapshot + normalized winner), then the trophy job grants `trophy_item_id` to **eligible** members of the winning legion. Eligibility (D-4): ≥ `min_tournaments_for_trophy` (default **3**, admin-editable) tournament participations within the season — the spec's «активные участники». Only linked students receive trophies (unlinked kids' items would be invisible anyway; a late-linking kid within an admin-set grace period can be granted manually from the Ops tab). New season starts fresh; XP/ranks/coins/items/streaks all persist (spec §13) — only season points reset.

History: `seasons` + `season_results` power a season archive page; trophies in inventory carry `season_id` forever.

### 8.5 League scale reconciliation (repair task)

Gamification config stores the canonical league thresholds per org (CE: rating `>800`→A, `≥450`→B, else C — matching CE's `calc_league_from_rating`). Chesster's `lib/league.ts` fallback and any CE-surface league badge read this config instead of hardcoded 900/500. Chesster-native `player_ratings` C/B/A/Master scale is a **different product surface** (online play) and stays as-is, but must never be shown on the CE surface.

## 9. UI Spec

### 9.1 Profile (`app/profile/page.tsx` — rewrite; CE surface variant)

Spec §2 fields: avatar (composited loadout) · name · rank (icon + name + progress bar to next rank) · XP · coin balance · streak (🔥 weeks + next milestone) · legion (crest + name) · tournaments played · total wins (both since launch, per D-5) · achievements strip (repaired, §3) · trophy case with provenance · customize + shop CTAs. Kid-friendly, big shapes, ru/kk/en via existing i18n `gamification` namespace (extend keys).

### 9.2 Empire homepage additions (`EmpireHomePage.tsx`)

Compact rank+XP chip, coin balance, streak flame, legion standing widget («🐆 Снежные Барсы — 2 место · 487 очков · до 1-го места: 25»), personal Top-N proximity line, populated achievements strip. `empire-homepage-render.tsx` extended to fetch the gamification profile alongside ratings.

### 9.3 New pages (CE surface)

- `/legion` — own legion: crest, Top-N, member list (linked students only) with season scores, my position.
- `/cup` — Legion Cup table, gaps, countdown to season end, past-season archive.
- `/shop`, `/avatar` (customization), `/coins` (purchase — Phase 4).

### 9.4 Admin (extends `app/admin/settings/` + new `admin/gamification/`)

Follows the existing pattern: Next route → Clerk-gated proxy → Flask `backend/routes/admin.py` (whitelisted fields) → Supabase. Tabs:

1. **Rules** — participation XP, per-kind win XP (incl. `rated` + reserved `pro`), coin_per_xp, league thresholds, top_n, trophy eligibility threshold, streak settings (bonus rate, min streak, milestone table, holiday freeze windows).
2. **Ranks** — CRUD ladder (name i18n, min XP, icon, order).
3. **Items** — CRUD catalog, art upload (reuse `branding/upload` storage pattern), price, rarity, availability windows, kind, placeholder-art tracking.
4. **Legions** — CRUD, CE-branch mapping, crest upload.
5. **Seasons** — create/activate/close (auto-freeze + confirm), trophy item picker, live standings preview, season archive.
6. **Coin packages & rate** (Phase 4) — package CRUD, KZT prices, base rate — **all pricing lives here, nothing hardcoded (D-6)**.
7. **Ops** — sync status/cursor, "Sync now", award audit log (ledger browser with reversal action), manual trophy grant, disabled backfill trigger (D-5).

Every parameter from spec §15 maps to one of these tabs; nothing is hardcoded.

## 10. Coin Purchase (Phase 4)

Rides the **Empire Payments** provider abstraction (`src/lib/empire-payments/providers.ts`, Kaspi-first — see that PRD; note it is spec-only today, so Phase 4 depends on it or ships a minimal subset):

- **Admin-defined packages and rates (D-6):** package sizes and KZT prices are created entirely in the admin Coin tab; no default pricing ships in code. Launch pricing is the director's call, changeable any time.
- Flow is **parent-facing**: purchase screen states clearly this is for a parent; Kaspi payment link/QR; confirmation (webhook if available, else admin manual-confirm queue) → `coin_ledger` credit `source='purchase'`, idempotency on payment ID.
- **+0 XP on purchase, ever** (enforced: sync + streak job are the only XP writers).
- Refund path: admin-initiated compensating ledger entries; if spent coins exceed remaining balance, balance may go to 0 but items are revoked only manually (kid-friendliness > strictness).
- Compliance: purchases by minors require parent action — copy, receipts to parent email/phone from CE `students.parent_*`.

## 11. Data Model (Chesster Supabase — new migration set)

```sql
-- All tables: organization_id UUID NOT NULL REFERENCES organizations(id), RLS: read own-org (students read own rows), write service-role only.

gamification_settings(organization_id PK, config JSONB, updated_at, updated_by)
  -- config: {participation_xp: 1,
  --          win_xp: {league_c: 1, league_b: 2, razryad_4: 3, razryad_3: 3, rated: 3, pro: 5},
  --          coin_per_xp: 1, top_n: 5, min_tournaments_for_trophy: 3,
  --          count_unlinked_in_standings: false,
  --          streak: {bonus_min: 2, bonus_xp: 1, milestones: {3: 3, 5: 5, 10: 10, 20: 25},
  --                   freeze_windows: [{from, until, label}]},
  --          league_thresholds: {a_min: 801, b_min: 450}, avatar_slots: [...]}

rank_definitions(id, organization_id, code, name_ru, name_kk, name_en, min_xp, icon_url, sort_order)

xp_ledger(id, organization_id, student_id BIGINT,           -- CE student id
          amount NUMERIC(8,1) NOT NULL,                      -- 0.5 granularity (draws); negative only for reversals
          reason TEXT,                                       -- participation | wins | streak_bonus | streak_milestone | ce_result_reversed | admin_adjust
          source_type TEXT, source_id TEXT,
          idempotency_key TEXT UNIQUE NOT NULL,
          legion_id UUID, season_id UUID,                    -- audit snapshot ONLY — scoring uses current mapping (D-11)
          occurred_at TIMESTAMPTZ NOT NULL,                  -- tournament_date
          created_at TIMESTAMPTZ DEFAULT now())

coin_ledger(id, organization_id, student_id, amount NUMERIC(10,1),  -- + earn/purchase, − spend
            source TEXT CHECK (source IN ('earn_xp','streak','purchase','spend','admin_adjust','refund')),
            source_id TEXT, idempotency_key TEXT UNIQUE NOT NULL, created_at)

player_gamification(organization_id, student_id PK,          -- materialized read model
            xp_total NUMERIC(10,1), coin_balance NUMERIC(10,1), rank_code TEXT,
            tournaments_played INT, wins_total NUMERIC(8,1), updated_at)

player_streaks(organization_id, student_id PK,
            current_weeks INT DEFAULT 0, best_weeks INT DEFAULT 0,
            run_start_week DATE, last_active_week DATE, updated_at)

items(id, organization_id, sku UNIQUE, slot, rarity, kind CHECK (kind IN ('purchasable','trophy','default')),
      price_coins INT NULL, name_ru/kk/en, description_ru/kk/en, art_url, anim_url, is_placeholder_art BOOL,
      available BOOL, available_from, available_until, acquisition_note, sort_order)

player_items(id, organization_id, student_id, item_id, acquired_via, season_id NULL, acquired_at,
             UNIQUE(student_id, item_id))

player_loadout(organization_id, student_id, slot, item_id, PRIMARY KEY(student_id, slot))

legions(id, organization_id, ce_branch_id BIGINT UNIQUE, name, totem, crest_url, color_primary, color_secondary)

seasons(id, organization_id, name, starts_at, ends_at, status CHECK (status IN ('draft','active','closed')),
        top_n INT, trophy_item_id, winner_legion_id NULL, closed_at NULL)

season_results(season_id PK, standings JSONB, per_student JSONB, finalized_at)

gamification_sync_state(organization_id PK, last_result_created_at, last_run_at, last_status, last_error)

coin_packages(id, organization_id, coins INT, price_kzt INT, active BOOL)          -- Phase 4; rows created only via admin (D-6)
coin_purchases(id, organization_id, student_id, package_id, amount_kzt, provider,   -- Phase 4
               provider_ref, status CHECK (status IN ('pending','paid','failed','refunded')), created_at, paid_at)

-- RPC: spend_coins(p_student, p_item) — lock, balance check, ledger insert + inventory insert, atomic.
```

## 12. APIs

**Player (Next API routes, Clerk-auth, resolve student via existing link):**
`GET /api/gamification/profile` (xp, rank+progress, coins, streak, legion, stats, loadout, trophies) · `GET /api/gamification/items` · `POST /api/gamification/shop/buy` (RPC) · `PUT /api/gamification/loadout` · `GET /api/gamification/legion` · `GET /api/gamification/cup` (standings + my proximity) · `GET /api/gamification/seasons` (archive).

**Admin (existing proxy pattern → Flask):** CRUD for settings/ranks/items/legions/seasons; `POST .../seasons/{id}/close`; ledger browser + reversal; manual trophy grant; sync trigger/status.

**System:** `POST /api/chess-empire/gamification/sync` (cron, `CRON_SECRET`) — awards, streak update, standings refresh in one pass.

## 13. Launch Plan (zero-start — D-5)

- Sync cursor initialized to launch timestamp; no historical awards. Everyone starts at Пешка, 0 XP, 0 coins, streak 0.
- Default items auto-granted to all linked students at launch so avatars aren't naked.
- First season created in `draft`, activated by admin when ready — its start can coincide with launch for a clean «Сезон 1» narrative (the fair-start rationale behind D-5).
- Placeholder art batch (20–30 items + crests per legion) generated and seeded before launch; swapped as the director delivers final designs.

## 14. Phasing (each phase = one Ralph run, sequential)

| Phase | Scope |
|---|---|
| **1. Core economy** | Migrations, sync + idempotent XP/coin ledgers (0.5 granularity), ranks, streaks engine + banner, `player_gamification`, real profile API, profile page rewrite, EmpireHomePage chips, admin Rules+Ranks tabs, achievements edge-fn repair |
| **2. Cosmetics** | Items, inventory, loadout, avatar renderer, shop UI, admin Items tab, placeholder art batch (20–30 items) |
| **3. Legions & Cup** | Legions (+placeholder crests), seasons, standings (current-branch scoring, unlinked-hidden), `/legion` + `/cup`, season auto-freeze + close + trophy job, trophy case, admin Legions+Seasons tabs |
| **4. Monetization** | Coin packages (admin-defined pricing), purchase flow on Empire Payments rail, admin Coin tab, reconciliation |

All decision blockers are resolved — Phase 1 is ready to dispatch. Phases 1–3 = spec §17 MVP. Phase 4 trails (depends on Empire Payments build) — coins are earnable meanwhile. Per workspace rules: tests every phase (ledger idempotency, reversal, half-point math, streak reset/freeze logic, RPC balance safety, standings math incl. transfer + link/unlink recompute, season close, RLS), suite run from main session before a phase is DONE.

## 15. Decisions Log (was: Open Questions — all resolved 2026-08-17)

| # | Question | Decision |
|---|---|---|
| D-1 | «Pro-лига» doesn't exist as a CE tournament kind | Map `razryad_4`/`razryad_3` (and `rated` by default) to the +3 rate; keep `pro: 5` as a reserved config slot |
| D-2 | Definition of «победа» | Per game won; **draws count as half**. Award = `score × rate` |
| D-3 | Legion point definition | **1 point = 1 XP = 1 coin** earned in-season |
| D-4 | Trophy eligibility («активные участники») | ≥3 tournament participations in the season, admin-editable |
| D-5 | Backfill vs zero-start | **Start everyone at zero**; no historical awards; backfill capability shelved |
| D-6 | Coin pricing | No hardcoded rates — packages and KZT prices set entirely in admin dashboard |
| D-7 | Streaks | **In scope as an XP/coin source** — tournament-week streaks with per-tournament bonus + one-time milestones, admin-configured, holiday freeze windows (§5.5) |
| D-8 | Unlinked students | **Hidden until linked** — excluded from all lists and legion scoring; XP still accrues silently in the ledger |
| D-9 | Art | **Placeholders now** (nano-banana batch, style-guided); director submits final designs later, swapped via admin upload |
| D-10 | Season cadence | **Admin-set, no fixed rhythm**; auto-freeze at end date + admin confirm to close |
| D-11 | Mid-season branch transfer | **Points move with the kid** — standings score by current branch mapping; ledger `legion_id` is audit-only |

## 16. Success Metrics

- Tournament participation rate per active student (primary — the director's stated goal), before/after and per season.
- Streak health: % of active students holding a ≥3-week streak (D-7's purpose is regularity).
- **Link rate** — % of CE students with linked accounts, now doubly important since unlinked kids don't score for their legion (D-8 makes this a growth loop; track it).
- Shop engagement (% spending earned coins); Legion Cup engagement: % of students checking `/cup` during a season's final week.
- Phase 4: coin purchase conversion, ARPU — tracked but explicitly secondary to participation.

## 17. Risks

- **CE ingestion is client-side** (browser admin inserts) — malformed uploads flow straight into XP. Mitigation: reversal path (§5.2), award audit log, sync sanity checks (score ≤ rounds, known student).
- **D-8 skew:** legions with low link rates under-score regardless of chess strength — standings measure *linked* strength. Mitigated by the link-rate metric + making linking a school-driven onboarding push at launch; `count_unlinked_in_standings` flag exists if the director wants to flip it.
- **Streak resets during holidays** would feel unfair — freeze windows (§5.5) must be populated by admin before each holiday; surface a reminder in the admin Ops tab.
- **Empire Payments doesn't exist yet** — Phase 4 blocked on it; sequence accordingly.
- **Economy tuning** — thresholds/prices will be wrong on the first try; that's why literally every number is admin config (spec §15). Ship, measure, tune.
- **Two-DB coupling** — sync depends on CE service key + schema stability; `gamification_sync_state.last_error` surfaces breakage in admin Ops tab.

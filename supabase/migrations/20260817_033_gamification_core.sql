-- ============================================================================
-- 20260817_033_gamification_core.sql
-- Gamification Phase 1 — Core economy (PRD-gamification.md §11)
--
-- Org-scoped gamification: XP/coin ledgers (append-only, idempotent, 0.5
-- granularity), materialized read model, tournament-week streaks, rank ladder,
-- per-org settings, and the CE sync cursor.
--
-- Subject key: CE student_id (Supabase papgcizhfkngubwofjuo). It is a UUID in
-- CE, stored here as TEXT so it matches organization_members.external_student_id
-- (the verified-link identifier, always a string) without casts.
--
-- Security model (matches supabase/migrations/20260601_008_rls_hardening.sql and
-- the 20260721 lockdown migrations): RLS enabled everywhere. Authenticated org
-- members may SELECT their org's rows via is_org_member(). All writes are
-- service-role only (Next.js route handlers / Flask, both BYPASSRLS) — there are
-- no client INSERT/UPDATE/DELETE policies. The CE DB is never written.
--
-- Idempotent: safe to re-run (IF NOT EXISTS / ON CONFLICT DO NOTHING).
-- ============================================================================

-- Shared updated_at trigger --------------------------------------------------
CREATE OR REPLACE FUNCTION gamification_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- gamification_settings — one config blob per org (D-6: nothing hardcoded).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gamification_settings (
  organization_id UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
  config          JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by      TEXT
);

DROP TRIGGER IF EXISTS trg_gamification_settings_updated ON gamification_settings;
CREATE TRIGGER trg_gamification_settings_updated
  BEFORE UPDATE ON gamification_settings
  FOR EACH ROW EXECUTE FUNCTION gamification_touch_updated_at();

-- ---------------------------------------------------------------------------
-- gamification_ranks — admin-editable rank ladder (Пешка → Король).
-- Rank is derived from lifetime XP against min_xp.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gamification_ranks (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  code            TEXT NOT NULL,
  name_ru         TEXT NOT NULL,
  name_kk         TEXT NOT NULL,
  name_en         TEXT NOT NULL,
  min_xp          NUMERIC(8,1) NOT NULL DEFAULT 0,
  icon_url        TEXT,
  sort_order      INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (organization_id, code)
);
CREATE INDEX IF NOT EXISTS idx_gam_ranks_org ON gamification_ranks (organization_id, sort_order);

DROP TRIGGER IF EXISTS trg_gamification_ranks_updated ON gamification_ranks;
CREATE TRIGGER trg_gamification_ranks_updated
  BEFORE UPDATE ON gamification_ranks
  FOR EACH ROW EXECUTE FUNCTION gamification_touch_updated_at();

-- ---------------------------------------------------------------------------
-- xp_ledger — append-only, idempotent. Balance = SUM(amount). Never updated.
-- amount NUMERIC(8,1): 0.5 granularity (draws). Negative only for reversals.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS xp_ledger (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  student_id      TEXT NOT NULL,                 -- CE student id (UUID as text)
  amount          NUMERIC(8,1) NOT NULL,
  reason          TEXT NOT NULL,                 -- tournament | streak_bonus | streak_milestone | ce_result_reversed | admin_adjust
  wins            NUMERIC(8,1),                  -- Swiss score contribution (tournament rows only); NULL otherwise
  source_type     TEXT,                          -- e.g. ce_result
  source_id       TEXT,                          -- e.g. tournament_results.id
  idempotency_key TEXT NOT NULL UNIQUE,
  legion_id       UUID,                          -- audit snapshot only (D-11); Phase 3
  season_id       UUID,                          -- audit snapshot only; Phase 3
  occurred_at     TIMESTAMPTZ NOT NULL,          -- tournament_date (season attribution)
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Additive column for existing installs (CREATE TABLE IF NOT EXISTS is a no-op once created).
ALTER TABLE xp_ledger ADD COLUMN IF NOT EXISTS wins NUMERIC(8,1);
CREATE INDEX IF NOT EXISTS idx_xp_ledger_org_student ON xp_ledger (organization_id, student_id);
CREATE INDEX IF NOT EXISTS idx_xp_ledger_occurred ON xp_ledger (organization_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_xp_ledger_source ON xp_ledger (source_type, source_id);

-- ---------------------------------------------------------------------------
-- coin_ledger — 1:1 coupling with earned XP (D-3). Same idempotency pattern.
-- Separate ledger so coupling can change later without migration.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coin_ledger (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  student_id      TEXT NOT NULL,
  amount          NUMERIC(10,1) NOT NULL,        -- + earn/purchase, − spend
  source          TEXT NOT NULL CHECK (source IN ('earn_xp','streak','purchase','spend','admin_adjust','refund')),
  source_id       TEXT,
  idempotency_key TEXT NOT NULL UNIQUE,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_coin_ledger_org_student ON coin_ledger (organization_id, student_id);

-- ---------------------------------------------------------------------------
-- player_gamification — materialized read model (balances = SUM, recomputed
-- transactionally by the sync engine). PK (org, student).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS player_gamification (
  organization_id    UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  student_id         TEXT NOT NULL,
  xp_total           NUMERIC(10,1) NOT NULL DEFAULT 0,
  coin_balance       NUMERIC(10,1) NOT NULL DEFAULT 0,
  rank_code          TEXT,
  tournaments_played INT NOT NULL DEFAULT 0,
  wins_total         NUMERIC(8,1) NOT NULL DEFAULT 0,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, student_id)
);

-- ---------------------------------------------------------------------------
-- streak_state — tournament-week streak per student (§5.5, D-7).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS streak_state (
  organization_id  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  student_id       TEXT NOT NULL,
  current_weeks    INT NOT NULL DEFAULT 0,
  best_weeks       INT NOT NULL DEFAULT 0,
  run_start_week   DATE,                          -- ISO Monday of current run start
  last_active_week DATE,                          -- ISO Monday of last participation week
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, student_id)
);

-- ---------------------------------------------------------------------------
-- gamification_sync_state — CE ingestion cursor (zero-start, D-5).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gamification_sync_state (
  organization_id         UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
  cursor_initialized_at   TIMESTAMPTZ,            -- launch timestamp; results before this are never awarded
  last_result_created_at  TIMESTAMPTZ,            -- high-water mark on tournament_results.created_at
  last_run_at             TIMESTAMPTZ,
  last_status             TEXT,
  last_error              TEXT
);

-- ============================================================================
-- Row Level Security — read own-org (authenticated); writes service-role only.
-- ============================================================================
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'gamification_settings','gamification_ranks','xp_ledger','coin_ledger',
    'player_gamification','streak_state','gamification_sync_state'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t);
    EXECUTE format('REVOKE ALL ON %I FROM anon, authenticated;', t);
    EXECUTE format('GRANT SELECT ON %I TO authenticated;', t);
    EXECUTE format('DROP POLICY IF EXISTS "org_member_read" ON %I;', t);
    EXECUTE format(
      'CREATE POLICY "org_member_read" ON %I FOR SELECT USING (is_org_member(%I.organization_id));',
      t, t
    );
  END LOOP;
END $$;

-- ============================================================================
-- Seed defaults for the Chess Empire org (D-6: sensible defaults ship as rows).
-- Scoped by slug so this stays portable; ON CONFLICT keeps re-runs safe.
-- ============================================================================
INSERT INTO gamification_settings (organization_id, config)
SELECT o.id, jsonb_build_object(
  'participation_xp', 1,
  'win_xp', jsonb_build_object(
    'league_c', 1, 'league_b', 2, 'razryad_4', 3, 'razryad_3', 3, 'rated', 3, 'pro', 5
  ),
  'coin_per_xp', 1,
  'top_n', 5,
  'min_tournaments_for_trophy', 3,
  'count_unlinked_in_standings', false,
  'streak', jsonb_build_object(
    'bonus_min', 2,
    'bonus_xp', 1,
    'milestones', jsonb_build_object('3', 3, '5', 5, '10', 10, '20', 25),
    'freeze_windows', '[]'::jsonb
  ),
  'league_thresholds', jsonb_build_object('a_min', 801, 'b_min', 450)
)
FROM organizations o
WHERE o.slug = 'chess-empire'
ON CONFLICT (organization_id) DO NOTHING;

INSERT INTO gamification_ranks (organization_id, code, name_ru, name_kk, name_en, min_xp, sort_order)
SELECT o.id, r.code, r.name_ru, r.name_kk, r.name_en, r.min_xp, r.sort_order
FROM organizations o
CROSS JOIN (VALUES
  ('pawn',   'Пешка',  'Сарбаз', 'Pawn',   0,   1),
  ('knight', 'Конь',   'Ат',     'Knight', 10,  2),
  ('bishop', 'Слон',   'Піл',    'Bishop', 30,  3),
  ('rook',   'Ладья',  'Тура',   'Rook',   70,  4),
  ('queen',  'Ферзь',  'Уәзір',  'Queen',  150, 5),
  ('king',   'Король', 'Патша',  'King',   300, 6)
) AS r(code, name_ru, name_kk, name_en, min_xp, sort_order)
WHERE o.slug = 'chess-empire'
ON CONFLICT (organization_id, code) DO NOTHING;

-- ============================================================================
-- ROLLBACK (manual):
--   DROP TABLE IF EXISTS gamification_sync_state, streak_state, player_gamification,
--     coin_ledger, xp_ledger, gamification_ranks, gamification_settings CASCADE;
--   DROP FUNCTION IF EXISTS gamification_touch_updated_at();
-- ============================================================================

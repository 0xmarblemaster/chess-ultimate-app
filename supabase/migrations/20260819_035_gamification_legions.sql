-- ============================================================================
-- 20260819_035_gamification_legions.sql
-- Gamification Phase 3 — Legions, Seasons, Legion Cup (PRD-gamification.md §8, §11)
--
-- Team competition on top of the Phase 1 economy: every CE branch is a Legion;
-- legions compete in seasonal Legion Cups scored by each legion's Top-N linked
-- players (§8.3). Standings are a QUERY, never a stored number — scoring groups
-- each student's season XP under their CURRENT branch→legion mapping (D-11), so
-- a mid-season transfer moves the whole score. Only the season snapshot frozen
-- at close (season_results) and awarded trophies are persisted.
--
-- Subject key: CE student_id (TEXT), matching Phase 1/2 tables. CE branch ids
-- are UUIDs in CE, so ce_branch_id is TEXT here (matching student_id's choice in
-- migration 033) — NOT the BIGINT the PRD schema sketch used.
--
-- Security model (matches 20260817_033 / 20260818_034): RLS enabled everywhere;
-- authenticated org members may SELECT their org's rows via is_org_member(); all
-- writes are service-role only (Next.js / Flask, BYPASSRLS).
--
-- Idempotent: safe to re-run (IF NOT EXISTS / ON CONFLICT DO NOTHING). Reuses the
-- gamification_touch_updated_at() trigger defined in migration 033.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- legions — one per CE branch (§8.1). ce_branch_id maps to CE branches.id and is
-- admin-editable (covers branch merges, §15); NULL until the admin maps it, so
-- the UNIQUE index is partial (many legions may be unmapped at once).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS legions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  ce_branch_id    TEXT,                          -- CE branches.id (UUID as text); NULL = unmapped
  name            TEXT NOT NULL,
  totem           TEXT,
  crest_url       TEXT,
  color_primary   TEXT,
  color_secondary TEXT,
  sort_order      INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- One legion per (org, branch) when mapped; unmapped (NULL) rows are unconstrained.
CREATE UNIQUE INDEX IF NOT EXISTS uq_legions_org_branch
  ON legions (organization_id, ce_branch_id) WHERE ce_branch_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_legions_org ON legions (organization_id, sort_order);

DROP TRIGGER IF EXISTS trg_legions_updated ON legions;
CREATE TRIGGER trg_legions_updated
  BEFORE UPDATE ON legions
  FOR EACH ROW EXECUTE FUNCTION gamification_touch_updated_at();

-- ---------------------------------------------------------------------------
-- seasons — arbitrary-date competition windows (§8.2, D-10). One active season
-- per org (partial unique index). XP rows with occurred_at inside the window
-- count toward it. Close is auto-freeze at ends_at + explicit admin confirm.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS seasons (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name              TEXT NOT NULL,
  starts_at         TIMESTAMPTZ NOT NULL,
  ends_at           TIMESTAMPTZ NOT NULL,
  status            TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','closed')),
  top_n             INT NOT NULL DEFAULT 5,
  trophy_item_id    UUID REFERENCES items(id) ON DELETE SET NULL,
  winner_legion_id  UUID REFERENCES legions(id) ON DELETE SET NULL,
  closed_at         TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_seasons_org ON seasons (organization_id, starts_at DESC);
-- Enforce "one active season per org".
CREATE UNIQUE INDEX IF NOT EXISTS uq_seasons_one_active
  ON seasons (organization_id) WHERE status = 'active';

DROP TRIGGER IF EXISTS trg_seasons_updated ON seasons;
CREATE TRIGGER trg_seasons_updated
  BEFORE UPDATE ON seasons
  FOR EACH ROW EXECUTE FUNCTION gamification_touch_updated_at();

-- ---------------------------------------------------------------------------
-- season_results — the frozen standings snapshot written at close (§8.4). JSONB
-- so the archive page and audit never depend on recomputing a past window.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS season_results (
  season_id       UUID PRIMARY KEY REFERENCES seasons(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  standings       JSONB NOT NULL DEFAULT '[]'::jsonb,   -- legion table snapshot
  per_student     JSONB NOT NULL DEFAULT '[]'::jsonb,   -- per-student season scores
  winner_legion_id UUID,
  finalized_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_season_results_org ON season_results (organization_id);

-- ============================================================================
-- Row Level Security — read own-org (authenticated); writes service-role only.
-- ============================================================================
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['legions', 'seasons', 'season_results'] LOOP
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
-- Seed placeholder legions for the Chess Empire org (D-9). Crest SVGs ship under
-- public/gamification/crests/ (frontend/scripts/gen-placeholder-crests.mjs).
-- ce_branch_id stays NULL — the admin maps each legion to a CE branch in the
-- Legions tab. Scoped by slug for portability; ON CONFLICT-free via NOT EXISTS
-- guard on (org, name) so re-runs don't duplicate.
-- ============================================================================
INSERT INTO legions (organization_id, name, totem, crest_url, color_primary, color_secondary, sort_order)
SELECT o.id, c.name, c.totem, c.crest_url, c.color_primary, c.color_secondary, c.sort_order
FROM organizations o
CROSS JOIN (VALUES
  ('Снежные Барсы',     'leopard', '/gamification/crests/snow-leopards.svg',  '#38bdf8', '#0369a1', 1),
  ('Золотые Орлы',      'eagle',   '/gamification/crests/golden-eagles.svg',  '#f59e0b', '#b45309', 2),
  ('Железные Медведи',  'bear',    '/gamification/crests/iron-bears.svg',     '#94a3b8', '#334155', 3),
  ('Серые Волки',       'wolf',    '/gamification/crests/grey-wolves.svg',    '#64748b', '#1e293b', 4),
  ('Рыжие Лисы',        'fox',     '/gamification/crests/red-foxes.svg',      '#fb923c', '#c2410c', 5),
  ('Багровые Львы',     'lion',    '/gamification/crests/crimson-lions.svg',  '#ef4444', '#991b1b', 6)
) AS c(name, totem, crest_url, color_primary, color_secondary, sort_order)
WHERE o.slug = 'chess-empire'
  AND NOT EXISTS (
    SELECT 1 FROM legions l WHERE l.organization_id = o.id AND l.name = c.name
  );

-- ============================================================================
-- Seed the first season in `draft` (§13). Admin activates it when ready; its
-- window can coincide with launch for a clean «Сезон 1» narrative.
-- ============================================================================
INSERT INTO seasons (organization_id, name, starts_at, ends_at, status, top_n)
SELECT o.id, 'Сезон 1 — Осень 2026', '2026-09-01T00:00:00Z', '2026-11-30T23:59:59Z', 'draft', 5
FROM organizations o
WHERE o.slug = 'chess-empire'
  AND NOT EXISTS (
    SELECT 1 FROM seasons s WHERE s.organization_id = o.id
  );

-- ============================================================================
-- ROLLBACK (manual):
--   DROP TABLE IF EXISTS season_results, seasons, legions CASCADE;
-- ============================================================================

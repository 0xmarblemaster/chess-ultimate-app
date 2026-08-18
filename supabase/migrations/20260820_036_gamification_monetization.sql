-- ============================================================================
-- 20260820_036_gamification_monetization.sql
-- Gamification Phase 4 — Monetization (PRD-gamification.md §10, §11, §14)
--
-- Coin purchases: admin-defined packages (sizes + KZT prices) and a manual-
-- confirm purchase queue. Coins are the ONLY thing money buys; buying coins
-- grants 0 XP (§10 — sync + streak job stay the sole XP writers). Purchase
-- pricing is entirely admin-created (D-6) — this migration ships NO default
-- pricing rows. Payment itself rides the Empire Payments provider abstraction
-- (Kaspi-first, src/lib/empire-payments/providers.ts); confirmation is manual
-- (admin marks a claimed payment paid) and credits coin_ledger idempotently
-- keyed on the payment id so a double-click cannot double-credit.
--
-- Subject key: CE student_id (TEXT), matching Phase 1-3 tables. Money amounts
-- are whole KZT (INT) — Kaspi tenge has no sub-unit here.
--
-- Security model (matches 20260817_033 / 034 / 035): RLS enabled everywhere;
-- authenticated org members may SELECT their org's rows via is_org_member();
-- all writes are service-role only (Next.js / Flask, BYPASSRLS).
--
-- Idempotent: safe to re-run (IF NOT EXISTS). Reuses the
-- gamification_touch_updated_at() trigger defined in migration 033.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- coin_packages — buyable coin bundles (§11). coins granted for price_kzt. All
-- rows are admin-created in the Coins tab (D-6); NO defaults are seeded here.
-- `active` toggles a package's visibility on the parent-facing /coins grid
-- without deleting it (so historical purchases keep a valid package_id).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coin_packages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  coins           INT NOT NULL CHECK (coins > 0),
  price_kzt       INT NOT NULL CHECK (price_kzt > 0),
  active          BOOLEAN NOT NULL DEFAULT true,
  sort_order      INT NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_coin_packages_org ON coin_packages (organization_id, sort_order);

DROP TRIGGER IF EXISTS trg_coin_packages_updated ON coin_packages;
CREATE TRIGGER trg_coin_packages_updated
  BEFORE UPDATE ON coin_packages
  FOR EACH ROW EXECUTE FUNCTION gamification_touch_updated_at();

-- ---------------------------------------------------------------------------
-- coin_purchases — the manual-confirm queue (§10, §11). A parent pays via the
-- provider (Kaspi) out-of-band, then taps «Я оплатил(а)» which inserts a row
-- with status='pending' (== "pending verification"). An admin later marks it
-- 'paid' (crediting coins) / 'refunded' / 'failed'.
--
--   pending  → paid      : admin confirms; coin_ledger credit source='purchase'
--   pending  → failed    : admin rejects an unmatched claim
--   paid     → refunded  : admin refund; compensating coin_ledger source='refund'
--
-- amount_kzt is snapshotted from the package at claim time so a later price
-- edit never rewrites history. provider_ref holds an optional transfer id the
-- parent/manager types in to match the Kaspi transaction.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coin_purchases (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  student_id      TEXT NOT NULL,
  package_id      UUID REFERENCES coin_packages(id) ON DELETE SET NULL,
  coins           INT NOT NULL,                  -- snapshot of package.coins at claim time
  amount_kzt      INT NOT NULL,                  -- snapshot of package.price_kzt at claim time
  provider        TEXT NOT NULL,                 -- 'kaspi' | 'bank_transfer' (Empire Payments rail)
  provider_ref    TEXT,                          -- optional transfer id the manager matches on
  status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','paid','failed','refunded')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  paid_at         TIMESTAMPTZ,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_coin_purchases_org_status
  ON coin_purchases (organization_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_coin_purchases_org_student
  ON coin_purchases (organization_id, student_id, created_at DESC);

DROP TRIGGER IF EXISTS trg_coin_purchases_updated ON coin_purchases;
CREATE TRIGGER trg_coin_purchases_updated
  BEFORE UPDATE ON coin_purchases
  FOR EACH ROW EXECUTE FUNCTION gamification_touch_updated_at();

-- ============================================================================
-- Row Level Security — read own-org (authenticated); writes service-role only.
-- Same pattern as Phases 1-3.
-- ============================================================================
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['coin_packages', 'coin_purchases'] LOOP
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
-- No seed data: all coin pricing is admin-created in the Coins tab (D-6).
--
-- ROLLBACK (manual):
--   DROP TABLE IF EXISTS coin_purchases, coin_packages CASCADE;
-- ============================================================================

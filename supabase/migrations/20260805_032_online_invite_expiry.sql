-- Migration: Online-students invite track + time-boxed access.
--
-- Adds a second onboarding track ('online') to the existing branch-invite
-- machinery, plus a per-member access expiry so online students get a bounded
-- (default 72h) window before they must re-onboard.
--
--  - branch_invite_tokens.kind             — 'branch' (default) | 'online'. An
--    'online' token skips the CE student-search/confirm flow entirely (there is
--    no CE roster to match against) and mints a synthetic-student invite JWT.
--  - branch_invite_tokens.access_ttl_hours — access window granted to a member
--    who onboards via this token; NULL means no time limit (branch tokens).
--  - organization_members.access_expires_at — absolute expiry stamped at link
--    time (now() + access_ttl_hours). NULL means never expires, so existing
--    branch students are untouched.
--
-- RLS: no new policies — the existing branch_invite_tokens / organization_members
-- policies cover access. Service-role writes bypass RLS by design.
--
-- Idempotent. Safe to re-run.

-- ─── branch_invite_tokens ──────────────────────────────────────────────────

ALTER TABLE branch_invite_tokens
  ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'branch';

ALTER TABLE branch_invite_tokens
  ADD COLUMN IF NOT EXISTS access_ttl_hours INT;

-- Guard the domain of `kind` without failing if the constraint already exists.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'branch_invite_tokens_kind_check'
  ) THEN
    ALTER TABLE branch_invite_tokens
      ADD CONSTRAINT branch_invite_tokens_kind_check
      CHECK (kind IN ('branch', 'online'));
  END IF;
END $$;

-- ─── organization_members ──────────────────────────────────────────────────

ALTER TABLE organization_members
  ADD COLUMN IF NOT EXISTS access_expires_at TIMESTAMPTZ;

-- Separate-track admin query: list all online students in an org.
CREATE INDEX IF NOT EXISTS idx_org_members_online_source
  ON organization_members (organization_id, external_source)
  WHERE external_source = 'online';

-- ROLLBACK (commented):
-- DROP INDEX IF EXISTS idx_org_members_online_source;
-- ALTER TABLE organization_members DROP COLUMN IF EXISTS access_expires_at;
-- ALTER TABLE branch_invite_tokens DROP CONSTRAINT IF EXISTS branch_invite_tokens_kind_check;
-- ALTER TABLE branch_invite_tokens DROP COLUMN IF EXISTS access_ttl_hours;
-- ALTER TABLE branch_invite_tokens DROP COLUMN IF EXISTS kind;

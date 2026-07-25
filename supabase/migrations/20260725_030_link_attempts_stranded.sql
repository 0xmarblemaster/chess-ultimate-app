-- Migration: `stranded` link_attempts status + `claim` attempted_source.
--
-- Stranded-user recovery hardening (2026-07-25). A student who ran the verify
-- step BEFORE the 2026-07-24 durability fix can still strand: their stashed
-- invite JWT expires beyond the claim grace, they have no `pending_registrations`
-- row and no `ce_pending_jti` cookie, so no path can complete the link. The
-- claim route now emits a one-time `stranded` audit row (attempted_source
-- `claim`) for such users so admins can find and link them manually
-- (`scripts/list-stranded-students.mjs`).
--
-- CHECK constraints don't support ADD IF NOT EXISTS, so drop + recreate with the
-- extra values. Idempotent. Safe to re-run.

ALTER TABLE link_attempts
  DROP CONSTRAINT IF EXISTS link_attempts_status_check;

ALTER TABLE link_attempts
  ADD CONSTRAINT link_attempts_status_check
  CHECK (status IN (
    'success',
    'pending_row_success',
    'no_match',
    'multiple_match',
    'jwt_missing',
    'jwt_invalid',
    'jwt_expired',
    'jwt_replayed',
    'webhook_error',
    'stranded'
  ));

ALTER TABLE link_attempts
  DROP CONSTRAINT IF EXISTS link_attempts_attempted_source_check;

ALTER TABLE link_attempts
  ADD CONSTRAINT link_attempts_attempted_source_check
  CHECK (attempted_source IN (
    'jwt',
    'email_auto',
    'admin_manual',
    'backfill',
    'claim'
  ));

-- ROLLBACK (commented):
-- ALTER TABLE link_attempts DROP CONSTRAINT IF EXISTS link_attempts_status_check;
-- ALTER TABLE link_attempts ADD CONSTRAINT link_attempts_status_check
--   CHECK (status IN ('success','pending_row_success','no_match','multiple_match',
--     'jwt_missing','jwt_invalid','jwt_expired','jwt_replayed','webhook_error'));
-- ALTER TABLE link_attempts DROP CONSTRAINT IF EXISTS link_attempts_attempted_source_check;
-- ALTER TABLE link_attempts ADD CONSTRAINT link_attempts_attempted_source_check
--   CHECK (attempted_source IN ('jwt','email_auto','admin_manual','backfill'));

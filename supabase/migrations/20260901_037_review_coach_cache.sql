-- ============================================================================
-- 20260901_037_review_coach_cache.sql
-- Review Coach v1 (REVIEW_COACH_PRD.md §6.4) — persistent LLM-explanation cache.
--
-- Backs the two-layer cache for the Review page's per-move "Explain" (F1) and
-- whole-game recap (F3). Layer 1 (this table) is shared and persistent so the
-- same position+move+locale is answered once across all games and users; the
-- client keeps an in-memory Layer 2 for same-session instant repeats.
--
--   * Per-move Explain key: fen + uci + locale (position-based, dedups across
--     different games/users).
--   * Game-summary key:     pgn_hash + locale.
--   * A prompt_version prefix lives inside cache_key so a prompt change is a
--     clean cache bust (no TTL for v1 — a position's explanation is stable).
--
-- Security model (matches supabase/migrations/20260721_rls_lockdown_*.sql):
-- RLS enabled. Authenticated users may SELECT (read). There are NO client
-- INSERT/UPDATE/DELETE policies, so writes are service-role only — the Next.js
-- route handler (BYPASSRLS via service_role) is the sole writer. The browser
-- never touches this table directly; reads and writes both go through
-- /api/coach/review-cache.
--
-- Idempotent: safe to re-run (IF NOT EXISTS / DROP POLICY IF EXISTS).
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS review_coach_cache (
  cache_key   TEXT PRIMARY KEY,
  kind        TEXT NOT NULL CHECK (kind IN ('explain', 'summary')),
  locale      TEXT NOT NULL,
  content     TEXT NOT NULL,
  model       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE review_coach_cache ENABLE ROW LEVEL SECURITY;

-- Authenticated read (defense-in-depth; the app reads via the server route).
DROP POLICY IF EXISTS review_coach_cache_read ON review_coach_cache;
CREATE POLICY review_coach_cache_read
  ON review_coach_cache
  FOR SELECT
  TO authenticated
  USING (true);

-- No INSERT/UPDATE/DELETE policies: writes are service-role only (server route).

COMMIT;

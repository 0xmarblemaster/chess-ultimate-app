-- Migration: coach_sessions + coach_messages
-- Persists coach conversations (text + voice) so a Hermes restart no longer
-- wipes shared session memory. Idempotent — safe to run multiple times.

CREATE TABLE IF NOT EXISTS coach_sessions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    board_state TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coach_sessions_user_id ON coach_sessions(user_id);

CREATE TABLE IF NOT EXISTS coach_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES coach_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'text',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coach_messages_session_id ON coach_messages(session_id);

-- ============================================
-- Migration 002: Analysis Chat Tables
-- ============================================
-- Create tables for multi-tenant server-managed chat
-- for position analysis, game analysis, and puzzles
--
-- Tables:
-- 1. analysis_conversations - Chat sessions
-- 2. analysis_chat_messages - Individual messages
-- 3. api_usage - Usage tracking for cost control
--
-- Author: Chess Ultimate App
-- Date: 2025-11-10
-- ============================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Table: analysis_conversations
-- Purpose: Track chat sessions for analysis tools
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,  -- Clerk user ID
    conversation_type TEXT NOT NULL CHECK (conversation_type IN ('position', 'game', 'puzzle', 'general')),
    context JSONB DEFAULT '{}',  -- FEN, PGN, puzzle data, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX idx_conversations_user_id ON analysis_conversations(user_id);
CREATE INDEX idx_conversations_type ON analysis_conversations(conversation_type);
CREATE INDEX idx_conversations_updated ON analysis_conversations(updated_at DESC);

-- Comment
COMMENT ON TABLE analysis_conversations IS 'Chat sessions for chess analysis tools (position, game, puzzle)';
COMMENT ON COLUMN analysis_conversations.user_id IS 'Clerk user ID from JWT token';
COMMENT ON COLUMN analysis_conversations.conversation_type IS 'Type of analysis: position, game, puzzle, or general';
COMMENT ON COLUMN analysis_conversations.context IS 'JSONB containing FEN, PGN, moves, or other context data';

-- ============================================
-- Table: analysis_chat_messages
-- Purpose: Store individual chat messages
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES analysis_conversations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,  -- Clerk user ID (denormalized for queries)
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    fen TEXT,  -- Position at time of message (optional)
    tokens_used INTEGER DEFAULT 0,  -- For cost tracking
    model TEXT,  -- Model used (e.g., 'claude-3-5-sonnet-20241022')
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX idx_messages_conversation ON analysis_chat_messages(conversation_id, timestamp);
CREATE INDEX idx_messages_user ON analysis_chat_messages(user_id, timestamp DESC);
CREATE INDEX idx_messages_timestamp ON analysis_chat_messages(timestamp DESC);

-- Comment
COMMENT ON TABLE analysis_chat_messages IS 'Individual messages in analysis chat conversations';
COMMENT ON COLUMN analysis_chat_messages.role IS 'Message role: user (human), assistant (AI), or system (context)';
COMMENT ON COLUMN analysis_chat_messages.tokens_used IS 'Approximate tokens used for cost tracking';
COMMENT ON COLUMN analysis_chat_messages.fen IS 'Chess position (FEN) at time of message for context';

-- ============================================
-- Table: api_usage
-- Purpose: Track API usage for cost control and analytics
-- ============================================
CREATE TABLE IF NOT EXISTS api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,  -- Clerk user ID
    endpoint TEXT NOT NULL,  -- API endpoint called (e.g., '/api/chat/analysis')
    tokens_used INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0.00,  -- Cost in USD
    model TEXT,  -- Model used
    response_time_ms INTEGER,  -- Response time in milliseconds
    success BOOLEAN DEFAULT TRUE,  -- Whether request succeeded
    error_message TEXT,  -- Error message if failed
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for analytics and cost tracking
CREATE INDEX idx_usage_user ON api_usage(user_id, timestamp DESC);
CREATE INDEX idx_usage_timestamp ON api_usage(timestamp DESC);
CREATE INDEX idx_usage_endpoint ON api_usage(endpoint, timestamp DESC);
CREATE INDEX idx_usage_success ON api_usage(success, timestamp DESC) WHERE success = FALSE;

-- Comment
COMMENT ON TABLE api_usage IS 'API usage tracking for cost control, analytics, and rate limiting';
COMMENT ON COLUMN api_usage.cost IS 'Estimated cost in USD based on token usage and model pricing';
COMMENT ON COLUMN api_usage.response_time_ms IS 'Response time in milliseconds for performance monitoring';

-- ============================================
-- Function: Update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-updating updated_at
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON analysis_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Sample queries for verification
-- ============================================

-- Get user's recent conversations
-- SELECT * FROM analysis_conversations
-- WHERE user_id = 'user_xxxxx'
-- ORDER BY updated_at DESC
-- LIMIT 10;

-- Get conversation with messages
-- SELECT
--     c.id,
--     c.conversation_type,
--     c.created_at,
--     json_agg(
--         json_build_object(
--             'role', m.role,
--             'content', m.content,
--             'timestamp', m.timestamp
--         ) ORDER BY m.timestamp
--     ) as messages
-- FROM analysis_conversations c
-- LEFT JOIN analysis_chat_messages m ON m.conversation_id = c.id
-- WHERE c.id = 'conversation_uuid'
-- GROUP BY c.id;

-- Get user's API usage summary (last 30 days)
-- SELECT
--     user_id,
--     COUNT(*) as total_requests,
--     SUM(tokens_used) as total_tokens,
--     SUM(cost) as total_cost,
--     AVG(response_time_ms) as avg_response_time,
--     COUNT(*) FILTER (WHERE success = FALSE) as failed_requests
-- FROM api_usage
-- WHERE user_id = 'user_xxxxx'
--   AND timestamp > NOW() - INTERVAL '30 days'
-- GROUP BY user_id;

-- ============================================
-- Migration complete
-- ============================================

-- Verify tables were created
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN ('analysis_conversations', 'analysis_chat_messages', 'api_usage')
ORDER BY table_name;

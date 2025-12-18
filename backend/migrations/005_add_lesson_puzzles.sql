-- Migration: Add lesson_puzzles table for multi-puzzle lessons
-- Created: 2025-11-28
-- Description: Allows a single lesson to contain multiple puzzles (e.g., from Lichess studies)
--              with per-puzzle progress tracking

BEGIN;

-- ============================================
-- LESSON PUZZLES TABLE
-- ============================================
-- Stores multiple puzzles per lesson, ordered by order_index
-- Used for lessons that have many related puzzles (e.g., "Rook Mate in 1" with 20 puzzles)

CREATE TABLE IF NOT EXISTS lesson_puzzles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lesson_id UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
  order_index INT NOT NULL,

  -- Puzzle data (same structure as single-puzzle lessons)
  fen TEXT NOT NULL,
  solution_move TEXT NOT NULL,  -- UCI notation (e.g., "e2e4")
  hint_text TEXT,
  success_message TEXT,

  -- Source tracking (for imported puzzles)
  source_url TEXT,      -- e.g., "https://lichess.org/study/VTUxy8HW"
  source_id TEXT,       -- e.g., Lichess chapter ID
  source_name TEXT,     -- e.g., "Chapter: Puzzle 1"

  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Each lesson can only have one puzzle at each order_index
  UNIQUE(lesson_id, order_index)
);

-- Index for fast lookup of puzzles by lesson
CREATE INDEX IF NOT EXISTS idx_lesson_puzzles_lesson_id ON lesson_puzzles(lesson_id);
CREATE INDEX IF NOT EXISTS idx_lesson_puzzles_order ON lesson_puzzles(lesson_id, order_index);

-- ============================================
-- USER PUZZLE PROGRESS TABLE
-- ============================================
-- Tracks which puzzles a user has completed within a lesson

CREATE TABLE IF NOT EXISTS user_puzzle_progress (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,  -- Clerk user ID
  puzzle_id UUID NOT NULL REFERENCES lesson_puzzles(id) ON DELETE CASCADE,

  -- Progress data
  completed_at TIMESTAMP WITH TIME ZONE,
  attempts INT DEFAULT 0,
  time_spent_seconds INT DEFAULT 0,

  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Each user can only have one progress record per puzzle
  UNIQUE(user_id, puzzle_id)
);

-- Index for fast lookup of user progress
CREATE INDEX IF NOT EXISTS idx_user_puzzle_progress_user ON user_puzzle_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_puzzle_progress_puzzle ON user_puzzle_progress(puzzle_id);

-- ============================================
-- ADD COLUMN TO LESSONS FOR MULTI-PUZZLE CONFIG
-- ============================================

-- Add column to indicate if lesson uses multi-puzzle system
ALTER TABLE lessons
ADD COLUMN IF NOT EXISTS has_multiple_puzzles BOOLEAN DEFAULT FALSE;

-- Add column for total puzzle count (denormalized for performance)
ALTER TABLE lessons
ADD COLUMN IF NOT EXISTS puzzle_count INT DEFAULT 0;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE lesson_puzzles IS 'Stores multiple puzzles per lesson for multi-puzzle exercises';
COMMENT ON COLUMN lesson_puzzles.order_index IS 'Display order within the lesson (1-based)';
COMMENT ON COLUMN lesson_puzzles.source_url IS 'Original source URL (e.g., Lichess study)';
COMMENT ON COLUMN lesson_puzzles.source_id IS 'ID from source system for deduplication';

COMMENT ON TABLE user_puzzle_progress IS 'Tracks per-puzzle completion for multi-puzzle lessons';
COMMENT ON COLUMN user_puzzle_progress.attempts IS 'Number of attempts before solving';

COMMIT;

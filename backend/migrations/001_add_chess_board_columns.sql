-- Migration: Add columns for animated chess board exercises
-- Created: 2025-01-20
-- Description: Adds solution_move, exercise_type, hint_text, and success_message columns to lessons table

BEGIN;

-- Add solution_move column (UCI notation like "e2e4")
ALTER TABLE lessons
ADD COLUMN IF NOT EXISTS solution_move TEXT;

-- Add exercise_type column with default
ALTER TABLE lessons
ADD COLUMN IF NOT EXISTS exercise_type TEXT DEFAULT 'one_move_puzzle';

-- Add hint_text column
ALTER TABLE lessons
ADD COLUMN IF NOT EXISTS hint_text TEXT;

-- Add success_message column
ALTER TABLE lessons
ADD COLUMN IF NOT EXISTS success_message TEXT;

-- Fix existing data: Set solution_move to a placeholder for lessons that have exercise_fen but no solution_move
-- This ensures the constraint won't be violated
UPDATE lessons
SET solution_move = 'e2e4'  -- Placeholder move
WHERE exercise_fen IS NOT NULL
  AND solution_move IS NULL;

-- Now we can safely add the constraint
ALTER TABLE lessons
DROP CONSTRAINT IF EXISTS valid_exercise;

ALTER TABLE lessons
ADD CONSTRAINT valid_exercise CHECK (
  (exercise_fen IS NULL AND solution_move IS NULL) OR
  (exercise_fen IS NOT NULL AND solution_move IS NOT NULL)
);

-- Add check constraint for exercise_type (separate from column definition for compatibility)
ALTER TABLE lessons
DROP CONSTRAINT IF EXISTS check_exercise_type;

ALTER TABLE lessons
ADD CONSTRAINT check_exercise_type CHECK (
  exercise_type IN ('one_move_puzzle', 'multi_move', 'position_eval', 'opening_practice')
);

-- Create index for faster exercise queries
CREATE INDEX IF NOT EXISTS idx_lessons_exercise_type ON lessons(exercise_type)
WHERE exercise_fen IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN lessons.solution_move IS 'UCI notation for the correct move (e.g., e2e4, e7e8q)';
COMMENT ON COLUMN lessons.exercise_type IS 'Type of chess exercise: one_move_puzzle, multi_move, position_eval, opening_practice';
COMMENT ON COLUMN lessons.hint_text IS 'Hint text to help students solve the exercise';
COMMENT ON COLUMN lessons.success_message IS 'Custom message shown after solving the exercise';

COMMIT;

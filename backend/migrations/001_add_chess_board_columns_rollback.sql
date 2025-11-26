-- Rollback: Remove animated chess board columns
-- Created: 2025-01-20
-- Description: Removes all columns added for animated chess board feature

BEGIN;

-- Drop constraint
ALTER TABLE lessons
DROP CONSTRAINT IF EXISTS valid_exercise;

-- Drop index
DROP INDEX IF EXISTS idx_lessons_exercise_type;

-- Drop columns
ALTER TABLE lessons
DROP COLUMN IF EXISTS solution_move,
DROP COLUMN IF EXISTS exercise_type,
DROP COLUMN IF EXISTS hint_text,
DROP COLUMN IF EXISTS success_message;

COMMIT;

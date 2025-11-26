-- Migration: Add arrow overlay columns for exercise visualization
-- Created: 2025-01-20
-- Description: Adds arrow_from_square and arrow_path columns to lessons table for Lichess-style arrow hints

BEGIN;

-- Add arrow_from_square column (e.g., "e3" - where the piece starts)
ALTER TABLE lessons
ADD COLUMN IF NOT EXISTS arrow_from_square TEXT;

-- Add arrow_path column (JSONB array of intermediate squares, e.g., ["f4"])
ALTER TABLE lessons
ADD COLUMN IF NOT EXISTS arrow_path JSONB;

-- Add comments for documentation
COMMENT ON COLUMN lessons.arrow_from_square IS 'Starting square for arrow hint overlay (e.g., e3)';
COMMENT ON COLUMN lessons.arrow_path IS 'Array of intermediate squares for multi-move arrow path (e.g., ["f4"])';

-- Update "The King" lesson with arrow data
-- King is at e3, needs to go to f5 via f4
UPDATE lessons
SET
  arrow_from_square = 'e3',
  arrow_path = '["f4"]'::jsonb
WHERE title = 'The King'
  AND exercise_fen = '7k/8/8/8/8/4K3/8/8 w - - 0 1';

COMMIT;

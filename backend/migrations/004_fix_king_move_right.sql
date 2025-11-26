-- Migration: Fix "The King: Move Right" exercise
-- Created: 2025-01-24
-- Description: Remove pawn from FEN and add arrow data for the second king exercise

BEGIN;

-- Update the lesson with slug 'the-king-move-right'
-- 1. Remove pawn from FEN (change from 7k/8/8/8/8/4K2P/8/8 to 7k/8/8/8/8/4K3/8/8)
-- 2. Change solution to e3h3
-- 3. Add arrow data showing path from e3 to h3 via f3, g3

UPDATE lessons
SET
  exercise_fen = '7k/8/8/8/8/4K3/8/8 w - - 0 1',
  solution_move = 'e3h3',
  arrow_from_square = 'e3',
  arrow_path = '["f3", "g3"]'::jsonb,
  exercise_solution = jsonb_set(
    COALESCE(exercise_solution, '{}'::jsonb),
    '{arrow}',
    '{"from": "e3", "path": ["f3", "g3"]}'::jsonb
  )
WHERE slug = 'the-king-move-right';

-- Verify the update
SELECT
  title,
  exercise_fen,
  solution_move,
  arrow_from_square,
  arrow_path
FROM lessons
WHERE slug = 'the-king-move-right';

COMMIT;

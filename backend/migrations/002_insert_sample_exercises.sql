-- Insert sample exercises for testing animated chess board
-- Created: 2025-01-20
-- Description: Adds 3 sample 1-move puzzle exercises
-- Updated to match actual schema (uses module_id, order_index)

BEGIN;

-- Get the first module ID from the sample data (Tactical Motifs module)
WITH first_module AS (
  SELECT id FROM modules ORDER BY created_at LIMIT 1
)

-- Exercise 1: Back rank mate
INSERT INTO lessons (
  module_id, title, content, lesson_type, order_index,
  exercise_fen, solution_move, exercise_type, hint_text, success_message
)
SELECT
  id,
  'Exercise 1: Back Rank Mate',
  'The back rank mate is one of the most important checkmate patterns. When a king is trapped on its starting rank by its own pawns, a rook or queen can deliver checkmate.',
  'exercise',
  100,
  '6k1/5ppp/8/8/8/8/8/R6K w - - 0 1',
  'a1a8',
  'one_move_puzzle',
  'The black king is trapped by its own pawns. Can you deliver checkmate on the back rank?',
  'Perfect! That''s back rank mate! The king had nowhere to go.'
FROM first_module
WHERE NOT EXISTS (
  SELECT 1 FROM lessons WHERE title = 'Exercise 1: Back Rank Mate'
);

-- Exercise 2: Knight fork
WITH first_module AS (
  SELECT id FROM modules ORDER BY created_at LIMIT 1
)
INSERT INTO lessons (
  module_id, title, content, lesson_type, order_index,
  exercise_fen, solution_move, exercise_type, hint_text, success_message
)
SELECT
  id,
  'Exercise 2: Knight Fork',
  'A knight fork is when the knight attacks two pieces at once. In this position, the knight can fork the king and queen, winning the queen!',
  'exercise',
  101,
  'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1',
  'f3g5',
  'one_move_puzzle',
  'Look for a knight move that attacks two pieces at once!',
  'Excellent! You won the queen with a knight fork!'
FROM first_module
WHERE NOT EXISTS (
  SELECT 1 FROM lessons WHERE title = 'Exercise 2: Knight Fork'
);

-- Exercise 3: Pin the knight
WITH first_module AS (
  SELECT id FROM modules ORDER BY created_at LIMIT 1
)
INSERT INTO lessons (
  module_id, title, content, lesson_type, order_index,
  exercise_fen, solution_move, exercise_type, hint_text, success_message
)
SELECT
  id,
  'Exercise 3: Pin the Knight',
  'A pin is when a piece cannot move without exposing a more valuable piece. Move your bishop to pin the knight to the king!',
  'exercise',
  102,
  'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 0 1',
  'f1b5',
  'one_move_puzzle',
  'Use your bishop to give check and attack the knight!',
  'Great! The knight is pinned and you''re attacking it too!'
FROM first_module
WHERE NOT EXISTS (
  SELECT 1 FROM lessons WHERE title = 'Exercise 3: Pin the Knight'
);

COMMIT;

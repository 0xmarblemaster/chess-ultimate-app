import type { ReviewResult } from '../types';

/** A small but schema-complete review result for component tests. */
export const REVIEW_FIXTURE: ReviewResult = {
  version: 2,
  engine: 'sf-d14',
  plies: 6,
  opening: { eco: 'C00', name: 'French Defense: Classical Variation', lastBookPly: 2 },
  accuracy: { w: 91.4, b: 62.3 },
  estRating: { w: 1250, b: 1400 },
  keyMoments: [5, 6],
  phases: {
    opening: { w: 95.0, b: 88.0 },
    middlegame: { w: 89.0, b: 40.0 },
    endgame: { w: null, b: null },
  },
  tally: {
    w: {
      brilliant: 1,
      great: 1,
      best: 1,
      excellent: 0,
      good: 0,
      book: 1,
      inaccuracy: 0,
      mistake: 0,
      miss: 0,
      blunder: 0,
      forced: 0,
    },
    b: {
      brilliant: 0,
      great: 0,
      best: 1,
      excellent: 0,
      good: 0,
      book: 1,
      inaccuracy: 0,
      mistake: 0,
      miss: 0,
      blunder: 1,
      forced: 0,
    },
  },
  moves: [
    { ply: 1, san: 'e4', uci: 'e2e4', fen: 'x', eval: { type: 'cp', value: 20 }, best: { uci: 'e2e4', eval: { type: 'cp', value: 20 } }, winPercent: 51.8, accuracy: null, classification: 'book', phase: 'opening' },
    { ply: 2, san: 'e6', uci: 'e7e6', fen: 'x', eval: { type: 'cp', value: 10 }, best: { uci: 'e7e6', eval: { type: 'cp', value: 10 } }, winPercent: 50.9, accuracy: null, classification: 'book', phase: 'opening' },
    { ply: 3, san: 'd4', uci: 'd2d4', fen: 'x', eval: { type: 'cp', value: 30 }, best: { uci: 'd2d4', eval: { type: 'cp', value: 30 } }, winPercent: 52.8, accuracy: 98.0, classification: 'best', phase: 'opening' },
    { ply: 4, san: 'Nf6', uci: 'g8f6', fen: 'x', eval: { type: 'cp', value: 25 }, best: { uci: 'g8f6', eval: { type: 'cp', value: 25 } }, winPercent: 52.3, accuracy: 97.0, classification: 'best', phase: 'opening' },
    { ply: 5, san: 'cxd4', uci: 'c5d4', fen: 'x', eval: { type: 'cp', value: 320 }, best: { uci: 'b8c6', eval: { type: 'cp', value: -10 } }, winPercent: 79.0, accuracy: 12.0, classification: 'blunder', phase: 'middlegame' },
    { ply: 6, san: 'Bxh7+', uci: 'd3h7', fen: 'x', eval: { type: 'cp', value: 340 }, best: { uci: 'd3h7', eval: { type: 'cp', value: 340 } }, winPercent: 80.5, accuracy: 99.0, classification: 'brilliant', phase: 'middlegame' },
  ],
};

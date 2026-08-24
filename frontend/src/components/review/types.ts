/**
 * Frozen result contract from the Flask game-review pipeline
 * (backend/services/game_review.py). See gamereview-phase3-brief.md.
 */
import type { Classification } from './ClassificationIcon';

export type { Classification };

export type Color = 'w' | 'b';

export interface EngineEval {
  type: 'cp' | 'mate';
  value: number;
}

export interface BestMove {
  uci: string;
  eval: EngineEval;
}

export interface ReviewMove {
  ply: number;
  san: string;
  uci: string;
  fen: string;
  eval: EngineEval;
  best: BestMove | null;
  second?: BestMove | null;
  winPercent: number;
  /** null on book plies (excluded from accuracy). */
  accuracy: number | null;
  classification: Classification;
  phase: 'opening' | 'middlegame' | 'endgame';
}

export type Tally = Record<Color, Record<Classification, number>>;

export interface ReviewResult {
  moves: ReviewMove[];
  accuracy: Record<Color, number>;
  tally: Tally;
  estRating: Record<Color, number>;
  phases: {
    opening: Record<Color, number | null>;
    middlegame: Record<Color, number | null>;
    endgame: Record<Color, number | null>;
  };
  keyMoments: number[];
  opening: { eco: string; name: string; lastBookPly: number };
  engine: string;
  plies: number;
  version: number;
}

export type ReviewStatus = 'queued' | 'running' | 'done' | 'error';

export interface ReviewJob {
  status: ReviewStatus;
  progress: number;
  result?: ReviewResult;
  error?: string;
}

export type ReviewSource = 'bot' | 'online' | 'database';

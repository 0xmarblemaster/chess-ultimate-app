/**
 * Move validation using chess.js
 */

import { Chess, Square } from 'chess.js';

export class MoveValidator {
  private chess: Chess;

  constructor(fen: string) {
    this.chess = new Chess(fen);
  }

  /**
   * Check if a move is legal in the current position
   */
  isLegalMove(from: string, to: string): boolean {
    const moves = this.chess.moves({ verbose: true });
    return moves.some((m) => m.from === from && m.to === to);
  }

  /**
   * Check if a move matches the solution
   */
  isSolutionMove(from: string, to: string, solution: string): boolean {
    const moveUci = `${from}${to}`;
    return moveUci === solution || moveUci === solution.substring(0, 4);
  }

  /**
   * Make a move and return the new FEN
   * Returns null if the move is illegal
   */
  makeMove(from: string, to: string, promotion?: string): string | null {
    try {
      const move = this.chess.move({ from, to, promotion });
      if (!move) return null;
      return this.chess.fen();
    } catch {
      return null;
    }
  }

  /**
   * Get all legal moves for a specific square
   */
  getLegalMoves(square: string): string[] {
    const moves = this.chess.moves({ square: square as Square, verbose: true });
    return moves.map((m) => m.to);
  }

  /**
   * Get the current FEN
   */
  getFen(): string {
    return this.chess.fen();
  }

  /**
   * Check if the current position is checkmate
   */
  isCheckmate(): boolean {
    return this.chess.isCheckmate();
  }

  /**
   * Check if the current position is check
   */
  isCheck(): boolean {
    return this.chess.isCheck();
  }

  /**
   * Check if the current position is stalemate
   */
  isStalemate(): boolean {
    return this.chess.isStalemate();
  }

  /**
   * Check if the game is over
   */
  isGameOver(): boolean {
    return this.chess.isGameOver();
  }

  /**
   * Reset the board to a new FEN position
   */
  reset(fen: string): void {
    this.chess.load(fen);
  }

  /**
   * Get the piece on a square
   */
  getPiece(square: string): { type: string; color: string } | null {
    const piece = this.chess.get(square as any);
    return piece || null;
  }
}

/**
 * Validate FEN string format
 */
export function isValidFen(fen: string): boolean {
  try {
    new Chess(fen);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate UCI move format (e.g., "e2e4", "e7e8q")
 */
export function isValidUciMove(move: string): boolean {
  const uciRegex = /^[a-h][1-8][a-h][1-8][qrbn]?$/;
  return uciRegex.test(move);
}

/**
 * Parse UCI move into from/to/promotion
 */
export function parseUciMove(uci: string): {
  from: string;
  to: string;
  promotion?: string;
} | null {
  if (!isValidUciMove(uci)) return null;

  return {
    from: uci.substring(0, 2),
    to: uci.substring(2, 4),
    promotion: uci.length === 5 ? uci[4] : undefined,
  };
}

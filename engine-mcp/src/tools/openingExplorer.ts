/**
 * Lichess opening explorer tool: `opening_explorer`. Uses the public
 * explorer.lichess.ovh API — top moves and game counts for a FEN.
 *
 * Request-building and response-shaping are pure functions so the network can
 * be mocked in tests.
 */
import { z } from "zod";
import { httpGetJson, type FetchLike } from "../http.js";
import { jsonResult, type ToolDefinition, type ToolResult } from "./types.js";

const EXPLORER_BASE = "https://explorer.lichess.ovh/lichess";
const DEFAULT_MOVES = 12;
const MAX_MOVES = 30;

export interface ExplorerDeps {
  fetchImpl?: FetchLike;
  timeoutMs?: number;
}

/** Build the Lichess opening-explorer URL for a FEN, requesting up to N moves. */
export function buildExplorerUrl(fen: string, moves = DEFAULT_MOVES): string {
  const capped = Math.max(1, Math.min(MAX_MOVES, Math.trunc(moves)));
  const params = new URLSearchParams({ fen, moves: String(capped) });
  return `${EXPLORER_BASE}?${params.toString()}`;
}

function gamesFor(node: any): number {
  return (
    (Number(node?.white) || 0) +
    (Number(node?.draws) || 0) +
    (Number(node?.black) || 0)
  );
}

/** Shape a Lichess explorer response into totals + a ranked move list. */
export function shapeExplorer(raw: any): Record<string, unknown> {
  const white = Number(raw?.white) || 0;
  const draws = Number(raw?.draws) || 0;
  const black = Number(raw?.black) || 0;
  const rawMoves = Array.isArray(raw?.moves) ? raw.moves : [];
  const moves = rawMoves.map((m: any) => ({
    uci: m.uci,
    san: m.san,
    games: gamesFor(m),
    white: Number(m?.white) || 0,
    draws: Number(m?.draws) || 0,
    black: Number(m?.black) || 0,
    average_rating: m.averageRating ?? null,
  }));
  return {
    total_games: white + draws + black,
    white,
    draws,
    black,
    opening: raw?.opening ?? null,
    moves,
  };
}

export async function openingExplorer(
  args: Record<string, unknown>,
  deps: ExplorerDeps = {},
): Promise<ToolResult> {
  const fen = typeof args.fen === "string" ? args.fen.trim() : "";
  if (!fen) {
    return jsonResult({ error: "fen is required" }, true);
  }
  const res = await httpGetJson<any>(buildExplorerUrl(fen), {
    timeoutMs: deps.timeoutMs,
    fetchImpl: deps.fetchImpl,
  });
  if (!res.ok) {
    return jsonResult({ error: res.error }, true);
  }
  return jsonResult(shapeExplorer(res.data));
}

export const openingExplorerTool: ToolDefinition = {
  name: "opening_explorer",
  description:
    "Look up a FEN in the Lichess opening explorer: most-played moves with win/draw/loss counts.",
  inputSchema: {
    fen: z.string().describe("FEN of the position to explore"),
  },
  handler: (args) => openingExplorer(args),
};

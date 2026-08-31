/**
 * ChessDB (chessdb.cn) public cloud-eval tools: `chessdb_eval` and
 * `chessdb_pv`. Both query the public `cdb.php` endpoint — no private backend.
 *
 * Response-shaping is factored into pure functions so it can be unit-tested
 * against canned payloads with the network mocked.
 */
import { z } from "zod";
import { httpGetJson, type FetchLike } from "../http.js";
import { jsonResult, type ToolDefinition, type ToolResult } from "./types.js";

const CHESSDB_BASE = "https://www.chessdb.cn/cdb.php";

export interface ChessdbDeps {
  fetchImpl?: FetchLike;
  timeoutMs?: number;
}

/** Build a ChessDB query URL for the given action and FEN. */
export function buildChessdbUrl(action: string, fen: string): string {
  const params = new URLSearchParams({ action, board: fen, json: "1" });
  return `${CHESSDB_BASE}?${params.toString()}`;
}

function toNumber(value: unknown): number | null {
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

/** Shape a `queryall` response into an eval + ranked move list. */
export function shapeChessdbEval(raw: any): Record<string, unknown> {
  const moves = Array.isArray(raw?.moves) ? raw.moves : [];
  if (raw?.status !== "ok" || moves.length === 0) {
    return {
      found: false,
      status: raw?.status ?? "unknown",
      message: "Position not found in ChessDB",
    };
  }
  const shaped = moves.map((m: any) => ({
    uci: m.uci,
    san: m.san,
    score_cp: toNumber(m.score),
    rank: m.rank,
    winrate: m.winrate,
  }));
  const best = shaped[0];
  return {
    found: true,
    eval_cp: best.score_cp,
    best_move: best.uci,
    best_move_san: best.san,
    moves: shaped,
  };
}

/** Shape a `querypv` response into a principal variation. */
export function shapeChessdbPv(raw: any): Record<string, unknown> {
  const pv = Array.isArray(raw?.pv) ? raw.pv : [];
  if (raw?.status !== "ok" || pv.length === 0) {
    return {
      found: false,
      status: raw?.status ?? "unknown",
      message: "No principal variation available for this position",
    };
  }
  return {
    found: true,
    score_cp: toNumber(raw.score),
    depth: toNumber(raw.depth),
    pv,
    pv_san: Array.isArray(raw.pvSAN) ? raw.pvSAN : [],
  };
}

async function runChessdb(
  action: string,
  shape: (raw: any) => Record<string, unknown>,
  args: Record<string, unknown>,
  deps: ChessdbDeps,
): Promise<ToolResult> {
  const fen = typeof args.fen === "string" ? args.fen.trim() : "";
  if (!fen) {
    return jsonResult({ found: false, error: "fen is required" }, true);
  }
  const res = await httpGetJson<any>(buildChessdbUrl(action, fen), {
    timeoutMs: deps.timeoutMs,
    fetchImpl: deps.fetchImpl,
  });
  if (!res.ok) {
    return jsonResult({ found: false, error: res.error }, true);
  }
  return jsonResult(shape(res.data));
}

export function chessdbEval(
  args: Record<string, unknown>,
  deps: ChessdbDeps = {},
): Promise<ToolResult> {
  return runChessdb("queryall", shapeChessdbEval, args, deps);
}

export function chessdbPv(
  args: Record<string, unknown>,
  deps: ChessdbDeps = {},
): Promise<ToolResult> {
  return runChessdb("querypv", shapeChessdbPv, args, deps);
}

const fenSchema = { fen: z.string().describe("FEN of the position to query") };

export const chessdbEvalTool: ToolDefinition = {
  name: "chessdb_eval",
  description:
    "Query the ChessDB public cloud database for a FEN's evaluation and best move.",
  inputSchema: fenSchema,
  handler: (args) => chessdbEval(args),
};

export const chessdbPvTool: ToolDefinition = {
  name: "chessdb_pv",
  description:
    "Query the ChessDB public cloud database for a FEN's principal variation.",
  inputSchema: fenSchema,
  handler: (args) => chessdbPv(args),
};

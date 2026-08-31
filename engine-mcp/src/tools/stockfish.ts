/**
 * Local Stockfish multi-PV analysis tool: `stockfish_multipv`. Spawns the
 * on-box UCI binary (default `/usr/games/stockfish`) with a hard depth cap and
 * per-call timeout, and returns the top-N principal variations.
 *
 * The UCI output parser is a pure function so it is unit-testable without a
 * process; the runner takes an injectable `spawnImpl` so tests can drive it
 * with a fake engine (no real binary or network required).
 */
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { z } from "zod";
import { jsonResult, type ToolDefinition, type ToolResult } from "./types.js";

const DEFAULT_BINARY = process.env.STOCKFISH_PATH ?? "/usr/games/stockfish";
const DEFAULT_DEPTH = 15;
const MAX_DEPTH = 22;
const DEFAULT_MULTIPV = 3;
const MAX_MULTIPV = 5;
const DEFAULT_TIMEOUT_MS = 10000;

export interface PvLine {
  multipv: number;
  depth: number;
  score: { type: "cp" | "mate"; value: number };
  pv: string[];
}

type SpawnLike = (
  command: string,
  args: string[],
  options: { stdio: ["pipe", "pipe", "pipe"] },
) => ChildProcessWithoutNullStreams;

export interface StockfishDeps {
  binaryPath?: string;
  spawnImpl?: SpawnLike;
  timeoutMs?: number;
}

function clampInt(value: unknown, fallback: number, min: number, max: number): number {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, Math.trunc(n)));
}

/** Parse a single UCI `info ... pv ...` line into a PvLine, or null. */
export function parseInfoLine(line: string): PvLine | null {
  const tokens = line.trim().split(/\s+/);
  if (tokens[0] !== "info") return null;
  const pvPos = tokens.indexOf("pv");
  const scorePos = tokens.indexOf("score");
  if (pvPos === -1 || scorePos === -1) return null;
  const scoreType = tokens[scorePos + 1];
  if (scoreType !== "cp" && scoreType !== "mate") return null;
  const scoreValue = Number.parseInt(tokens[scorePos + 2], 10);
  if (!Number.isFinite(scoreValue)) return null;
  const pv = tokens.slice(pvPos + 1).filter(Boolean);
  if (pv.length === 0) return null;
  const mpPos = tokens.indexOf("multipv");
  const depthPos = tokens.indexOf("depth");
  return {
    multipv: mpPos !== -1 ? Number.parseInt(tokens[mpPos + 1], 10) || 1 : 1,
    depth: depthPos !== -1 ? Number.parseInt(tokens[depthPos + 1], 10) || 0 : 0,
    score: { type: scoreType, value: scoreValue },
    pv,
  };
}

/**
 * Reduce a full UCI stdout transcript to the deepest info line per multipv
 * index (last one wins) plus the reported best move.
 */
export function parseMultipvOutput(lines: string[]): {
  lines: PvLine[];
  bestmove: string | null;
} {
  const byIndex = new Map<number, PvLine>();
  let bestmove: string | null = null;
  for (const raw of lines) {
    const trimmed = raw.trim();
    if (trimmed.startsWith("bestmove")) {
      bestmove = trimmed.split(/\s+/)[1] ?? null;
      continue;
    }
    const parsed = parseInfoLine(trimmed);
    if (parsed) byIndex.set(parsed.multipv, parsed);
  }
  return {
    lines: [...byIndex.values()].sort((a, b) => a.multipv - b.multipv),
    bestmove,
  };
}

export async function stockfishMultipv(
  args: Record<string, unknown>,
  deps: StockfishDeps = {},
): Promise<ToolResult> {
  const fen = typeof args.fen === "string" ? args.fen.trim() : "";
  if (!fen) {
    return jsonResult({ error: "fen is required" }, true);
  }
  const depth = clampInt(args.depth, DEFAULT_DEPTH, 1, MAX_DEPTH);
  const multipv = clampInt(args.multipv, DEFAULT_MULTIPV, 1, MAX_MULTIPV);
  const binaryPath = deps.binaryPath ?? DEFAULT_BINARY;
  const spawnImpl = deps.spawnImpl ?? (spawn as unknown as SpawnLike);
  const timeoutMs = deps.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  return new Promise<ToolResult>((resolve) => {
    let child: ChildProcessWithoutNullStreams;
    try {
      child = spawnImpl(binaryPath, [], { stdio: ["pipe", "pipe", "pipe"] });
    } catch (err) {
      resolve(
        jsonResult(
          { error: `Failed to spawn Stockfish: ${(err as Error).message}` },
          true,
        ),
      );
      return;
    }

    const lines: string[] = [];
    let buffer = "";
    let settled = false;

    const finish = (result: ToolResult) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        child.kill();
      } catch {
        /* already gone */
      }
      resolve(result);
    };

    const shape = (timedOut: boolean): ToolResult => {
      const { lines: pv, bestmove } = parseMultipvOutput(lines);
      if (pv.length === 0) {
        return jsonResult(
          {
            error: timedOut
              ? `Stockfish timed out after ${timeoutMs}ms with no output`
              : "Stockfish produced no analysis",
            timed_out: timedOut,
          },
          true,
        );
      }
      return jsonResult({
        fen,
        depth_requested: depth,
        multipv,
        timed_out: timedOut,
        best_move: bestmove,
        lines: pv,
      });
    };

    const timer = setTimeout(() => finish(shape(true)), timeoutMs);

    child.on("error", (err: Error) =>
      finish(jsonResult({ error: `Stockfish error: ${err.message}` }, true)),
    );

    child.stdout.on("data", (chunk: Buffer | string) => {
      buffer += chunk.toString();
      const parts = buffer.split("\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed) continue;
        lines.push(trimmed);
        if (trimmed.startsWith("bestmove")) {
          finish(shape(false));
          return;
        }
      }
    });

    const commands =
      [
        "uci",
        `setoption name MultiPV value ${multipv}`,
        "isready",
        `position fen ${fen}`,
        `go depth ${depth}`,
      ].join("\n") + "\n";
    try {
      child.stdin.write(commands);
    } catch {
      /* the error/close handlers will settle the promise */
    }
  });
}

export const stockfishMultipvTool: ToolDefinition = {
  name: "stockfish_multipv",
  description:
    "Analyse a FEN with the local Stockfish engine, returning the top-N principal variations with scores (side-to-move perspective).",
  inputSchema: {
    fen: z.string().describe("FEN of the position to analyse"),
    depth: z
      .number()
      .int()
      .positive()
      .optional()
      .describe(`Search depth (default ${DEFAULT_DEPTH}, capped at ${MAX_DEPTH})`),
    multipv: z
      .number()
      .int()
      .positive()
      .optional()
      .describe(
        `Number of principal variations (default ${DEFAULT_MULTIPV}, capped at ${MAX_MULTIPV})`,
      ),
  },
  handler: (args) => stockfishMultipv(args),
};

export const STOCKFISH_LIMITS = {
  DEFAULT_DEPTH,
  MAX_DEPTH,
  DEFAULT_MULTIPV,
  MAX_MULTIPV,
} as const;

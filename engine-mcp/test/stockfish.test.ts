import { EventEmitter } from "node:events";
import { existsSync } from "node:fs";
import { describe, it, expect } from "vitest";
import {
  parseInfoLine,
  parseMultipvOutput,
  stockfishMultipv,
  STOCKFISH_LIMITS,
} from "../src/tools/stockfish.js";
import { parseResult } from "./helpers.js";

const START_FEN =
  "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

/**
 * Build a fake `spawn` that replays canned UCI output when the runner sends
 * `go`. Captures the command strings written to stdin so tests can assert
 * clamping. `emitBestmove: false` simulates an engine that never finishes.
 */
function fakeStockfish(
  outputLines: string[],
  { emitBestmove = true }: { emitBestmove?: boolean } = {},
) {
  const writes: string[] = [];
  const spawnImpl = ((_cmd: string) => {
    const child = new EventEmitter() as any;
    child.stdout = new EventEmitter();
    child.stderr = new EventEmitter();
    child.killed = false;
    child.kill = () => {
      child.killed = true;
    };
    child.stdin = {
      write: (s: string) => {
        writes.push(s);
        if (s.includes("go ")) {
          queueMicrotask(() => {
            // Emit info lines as one chunk to exercise line buffering.
            child.stdout.emit("data", outputLines.join("\n") + "\n");
            if (emitBestmove) {
              child.stdout.emit("data", "bestmove e2e4 ponder e7e5\n");
            }
          });
        }
        return true;
      },
      end: () => {},
    };
    return child;
  }) as any;
  return { spawnImpl, writes };
}

describe("UCI info line parsing", () => {
  it("parses a cp score line with pv", () => {
    const line =
      "info depth 20 seldepth 30 multipv 1 score cp 34 nodes 100 pv e2e4 e7e5 g1f3";
    const parsed = parseInfoLine(line)!;
    expect(parsed.multipv).toBe(1);
    expect(parsed.depth).toBe(20);
    expect(parsed.score).toEqual({ type: "cp", value: 34 });
    expect(parsed.pv).toEqual(["e2e4", "e7e5", "g1f3"]);
  });

  it("parses a mate score", () => {
    const parsed = parseInfoLine(
      "info depth 15 multipv 2 score mate -3 pv h5f7",
    )!;
    expect(parsed.score).toEqual({ type: "mate", value: -3 });
    expect(parsed.multipv).toBe(2);
  });

  it("ignores lines without a pv or score", () => {
    expect(parseInfoLine("info depth 1 currmove e2e4")).toBeNull();
    expect(parseInfoLine("readyok")).toBeNull();
  });
});

describe("multipv output reduction", () => {
  it("keeps the deepest line per multipv index and the best move", () => {
    const { lines, bestmove } = parseMultipvOutput([
      "info depth 5 multipv 1 score cp 10 pv e2e4",
      "info depth 5 multipv 2 score cp 5 pv d2d4",
      "info depth 20 multipv 1 score cp 34 pv e2e4 e7e5",
      "info depth 20 multipv 2 score cp 20 pv d2d4 d7d5",
      "bestmove e2e4 ponder e7e5",
    ]);
    expect(bestmove).toBe("e2e4");
    expect(lines).toHaveLength(2);
    expect(lines[0].multipv).toBe(1);
    expect(lines[0].depth).toBe(20);
    expect(lines[1].multipv).toBe(2);
    expect(lines[1].depth).toBe(20);
  });
});

describe("stockfishMultipv runner (fake engine)", () => {
  it("returns shaped lines and best move on bestmove", async () => {
    const { spawnImpl } = fakeStockfish([
      "info depth 18 multipv 1 score cp 30 pv e2e4 e7e5",
      "info depth 18 multipv 2 score cp 18 pv d2d4 d7d5",
    ]);
    const result = await stockfishMultipv(
      { fen: START_FEN, depth: 18, multipv: 2 },
      { spawnImpl, timeoutMs: 2000 },
    );
    const data = parseResult(result);
    expect(data.best_move).toBe("e2e4");
    expect(data.timed_out).toBe(false);
    expect(data.lines).toHaveLength(2);
    expect(data.lines[0].pv[0]).toBe("e2e4");
  });

  it("clamps depth and multipv to the hard caps", async () => {
    const { spawnImpl, writes } = fakeStockfish([
      "info depth 22 multipv 1 score cp 30 pv e2e4",
    ]);
    await stockfishMultipv(
      { fen: START_FEN, depth: 999, multipv: 99 },
      { spawnImpl, timeoutMs: 2000 },
    );
    const sent = writes.join("");
    expect(sent).toContain(`MultiPV value ${STOCKFISH_LIMITS.MAX_MULTIPV}`);
    expect(sent).toContain(`go depth ${STOCKFISH_LIMITS.MAX_DEPTH}`);
  });

  it("times out gracefully, returning partial lines", async () => {
    const { spawnImpl } = fakeStockfish(
      ["info depth 10 multipv 1 score cp 12 pv e2e4"],
      { emitBestmove: false },
    );
    const result = await stockfishMultipv(
      { fen: START_FEN },
      { spawnImpl, timeoutMs: 40 },
    );
    const data = parseResult(result);
    expect(data.timed_out).toBe(true);
    expect(data.lines).toHaveLength(1);
  });

  it("requires a fen", async () => {
    const result = await stockfishMultipv({});
    expect(result.isError).toBe(true);
  });

  it("returns an error when the binary cannot be spawned", async () => {
    const result = await stockfishMultipv(
      { fen: START_FEN },
      {
        spawnImpl: (() => {
          throw new Error("ENOENT");
        }) as any,
      },
    );
    expect(result.isError).toBe(true);
    expect(parseResult(result).error).toContain("Failed to spawn");
  });
});

const BIN = process.env.STOCKFISH_PATH ?? "/usr/games/stockfish";
const realTest = existsSync(BIN) ? it : it.skip;

describe("stockfishMultipv with the real binary", () => {
  realTest(
    "analyses the starting position",
    async () => {
      const result = await stockfishMultipv(
        { fen: START_FEN, depth: 8, multipv: 2 },
        { timeoutMs: 15000 },
      );
      const data = parseResult(result);
      expect(data.best_move).toBeTruthy();
      expect(data.lines.length).toBeGreaterThanOrEqual(1);
      expect(data.lines[0].score.type).toMatch(/cp|mate/);
    },
    20000,
  );
});

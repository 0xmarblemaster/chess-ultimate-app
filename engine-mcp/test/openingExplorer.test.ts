import { describe, it, expect } from "vitest";
import {
  buildExplorerUrl,
  openingExplorer,
  shapeExplorer,
} from "../src/tools/openingExplorer.js";
import { mockFetch, parseResult } from "./helpers.js";

const FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

describe("opening explorer URL building", () => {
  it("includes the fen and a capped moves count", () => {
    const params = new URL(buildExplorerUrl(FEN, 5)).searchParams;
    expect(params.get("fen")).toBe(FEN);
    expect(params.get("moves")).toBe("5");
  });

  it("clamps an oversized moves count", () => {
    const params = new URL(buildExplorerUrl(FEN, 999)).searchParams;
    expect(Number(params.get("moves"))).toBeLessThanOrEqual(30);
  });
});

describe("opening explorer shaping", () => {
  it("computes totals and per-move game counts", () => {
    const shaped = shapeExplorer({
      white: 100,
      draws: 50,
      black: 30,
      opening: { eco: "C20", name: "King's Pawn" },
      moves: [
        { uci: "e7e5", san: "e5", white: 40, draws: 20, black: 10, averageRating: 1800 },
        { uci: "c7c5", san: "c5", white: 30, draws: 15, black: 12 },
      ],
    });
    expect(shaped.total_games).toBe(180);
    expect(shaped.white).toBe(100);
    const moves = shaped.moves as any[];
    expect(moves[0].games).toBe(70);
    expect(moves[0].average_rating).toBe(1800);
    expect(moves[1].average_rating).toBeNull();
  });

  it("handles a response with no moves", () => {
    const shaped = shapeExplorer({ white: 0, draws: 0, black: 0 });
    expect(shaped.total_games).toBe(0);
    expect(shaped.moves).toEqual([]);
  });
});

describe("opening explorer handler (mocked network)", () => {
  it("hits the lichess explorer and returns shaped JSON", async () => {
    const fetchImpl = mockFetch({
      white: 10,
      draws: 5,
      black: 5,
      moves: [{ uci: "e7e5", san: "e5", white: 5, draws: 2, black: 2 }],
    });
    const result = await openingExplorer({ fen: FEN }, { fetchImpl });
    expect(fetchImpl.calls[0]).toContain("explorer.lichess.ovh");
    const data = parseResult(result);
    expect(data.total_games).toBe(20);
    expect(data.moves[0].games).toBe(9);
  });

  it("requires a fen", async () => {
    const result = await openingExplorer({});
    expect(result.isError).toBe(true);
  });

  it("returns a graceful error on network failure", async () => {
    const fetchImpl = mockFetch({}, { ok: false, status: 429 });
    const result = await openingExplorer({ fen: FEN }, { fetchImpl });
    expect(result.isError).toBe(true);
    expect(parseResult(result).error).toContain("HTTP 429");
  });
});

import { describe, it, expect } from "vitest";
import {
  buildChessdbUrl,
  chessdbEval,
  chessdbPv,
  shapeChessdbEval,
  shapeChessdbPv,
} from "../src/tools/chessdb.js";
import { mockFetch, parseResult } from "./helpers.js";

const FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

describe("chessdb URL building", () => {
  it("encodes the FEN and sets action + json params", () => {
    const url = buildChessdbUrl("queryall", FEN);
    expect(url.startsWith("https://www.chessdb.cn/cdb.php?")).toBe(true);
    const params = new URL(url).searchParams;
    expect(params.get("action")).toBe("queryall");
    expect(params.get("board")).toBe(FEN);
    expect(params.get("json")).toBe("1");
  });
});

describe("chessdb eval shaping", () => {
  it("shapes an ok response into eval + best move + ranked moves", () => {
    const shaped = shapeChessdbEval({
      status: "ok",
      moves: [
        { uci: "e2e4", san: "e4", score: 34, rank: 2 },
        { uci: "d2d4", san: "d4", score: 28, rank: 2 },
      ],
    });
    expect(shaped.found).toBe(true);
    expect(shaped.eval_cp).toBe(34);
    expect(shaped.best_move).toBe("e2e4");
    expect(shaped.best_move_san).toBe("e4");
    expect((shaped.moves as unknown[]).length).toBe(2);
  });

  it("treats a non-ok status as not found", () => {
    const shaped = shapeChessdbEval({ status: "unknown" });
    expect(shaped.found).toBe(false);
    expect(shaped.status).toBe("unknown");
  });

  it("treats an empty move list as not found", () => {
    const shaped = shapeChessdbEval({ status: "ok", moves: [] });
    expect(shaped.found).toBe(false);
  });
});

describe("chessdb pv shaping", () => {
  it("shapes an ok response into a principal variation", () => {
    const shaped = shapeChessdbPv({
      status: "ok",
      score: 27,
      depth: 36,
      pv: ["e2e4", "e7e5"],
      pvSAN: ["e4", "e5"],
    });
    expect(shaped.found).toBe(true);
    expect(shaped.score_cp).toBe(27);
    expect(shaped.depth).toBe(36);
    expect(shaped.pv).toEqual(["e2e4", "e7e5"]);
    expect(shaped.pv_san).toEqual(["e4", "e5"]);
  });

  it("treats a missing pv as not found", () => {
    const shaped = shapeChessdbPv({ status: "ok" });
    expect(shaped.found).toBe(false);
  });
});

describe("chessdb handlers (mocked network)", () => {
  it("chessdbEval hits queryall and returns shaped JSON", async () => {
    const fetchImpl = mockFetch({
      status: "ok",
      moves: [{ uci: "e2e4", san: "e4", score: 34, rank: 2 }],
    });
    const result = await chessdbEval({ fen: FEN }, { fetchImpl });
    const data = parseResult(result);
    expect(fetchImpl.calls[0]).toContain("action=queryall");
    expect(data.found).toBe(true);
    expect(data.best_move).toBe("e2e4");
  });

  it("chessdbPv hits querypv", async () => {
    const fetchImpl = mockFetch({
      status: "ok",
      score: 12,
      depth: 30,
      pv: ["d2d4"],
      pvSAN: ["d4"],
    });
    const result = await chessdbPv({ fen: FEN }, { fetchImpl });
    const data = parseResult(result);
    expect(fetchImpl.calls[0]).toContain("action=querypv");
    expect(data.found).toBe(true);
  });

  it("requires a fen", async () => {
    const result = await chessdbEval({});
    expect(result.isError).toBe(true);
    expect(parseResult(result).error).toMatch(/fen is required/);
  });

  it("returns a graceful error on HTTP failure", async () => {
    const fetchImpl = mockFetch({}, { ok: false, status: 500 });
    const result = await chessdbEval({ fen: FEN }, { fetchImpl });
    expect(result.isError).toBe(true);
    const data = parseResult(result);
    expect(data.found).toBe(false);
    expect(data.error).toContain("HTTP 500");
  });
});

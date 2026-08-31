/**
 * ChessDB (chessdb.cn) public cloud-eval tools: `chessdb_eval` and
 * `chessdb_pv`. Both query the public `cdb.php` endpoint — no private backend.
 *
 * Step 1 scaffold: schemas are final; handlers are filled in step 2.
 */
import { z } from "zod";
import { jsonResult, type ToolDefinition } from "./types.js";

const fenSchema = { fen: z.string().describe("FEN of the position to query") };

export const chessdbEvalTool: ToolDefinition = {
  name: "chessdb_eval",
  description:
    "Query the ChessDB public cloud database for a FEN's evaluation and best move.",
  inputSchema: fenSchema,
  handler: async () => jsonResult({ error: "not implemented" }, true),
};

export const chessdbPvTool: ToolDefinition = {
  name: "chessdb_pv",
  description:
    "Query the ChessDB public cloud database for a FEN's principal variation.",
  inputSchema: fenSchema,
  handler: async () => jsonResult({ error: "not implemented" }, true),
};

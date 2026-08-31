/**
 * Local Stockfish multi-PV analysis tool: `stockfish_multipv`. Spawns the
 * on-box UCI binary (default `/usr/games/stockfish`) with a hard depth cap and
 * per-call timeout.
 *
 * Step 1 scaffold: schema is final; handler is filled in step 2.
 */
import { z } from "zod";
import { jsonResult, type ToolDefinition } from "./types.js";

export const stockfishMultipvTool: ToolDefinition = {
  name: "stockfish_multipv",
  description:
    "Analyse a FEN with the local Stockfish engine, returning the top-N principal variations with scores.",
  inputSchema: {
    fen: z.string().describe("FEN of the position to analyse"),
    depth: z
      .number()
      .int()
      .positive()
      .optional()
      .describe("Search depth (capped server-side)"),
    multipv: z
      .number()
      .int()
      .positive()
      .optional()
      .describe("Number of principal variations to return (capped server-side)"),
  },
  handler: async () => jsonResult({ error: "not implemented" }, true),
};

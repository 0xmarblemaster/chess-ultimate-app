/**
 * Lichess opening explorer tool: `opening_explorer`. Uses the public
 * explorer.lichess.ovh API — top moves and game counts for a FEN.
 *
 * Step 1 scaffold: schema is final; handler is filled in step 2.
 */
import { z } from "zod";
import { jsonResult, type ToolDefinition } from "./types.js";

export const openingExplorerTool: ToolDefinition = {
  name: "opening_explorer",
  description:
    "Look up a FEN in the Lichess opening explorer: most-played moves with win/draw/loss counts.",
  inputSchema: {
    fen: z.string().describe("FEN of the position to explore"),
  },
  handler: async () => jsonResult({ error: "not implemented" }, true),
};

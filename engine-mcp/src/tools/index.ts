/** The engine MCP toolset — exactly these four tools are advertised. */
import type { ToolDefinition } from "./types.js";
import { chessdbEvalTool, chessdbPvTool } from "./chessdb.js";
import { openingExplorerTool } from "./openingExplorer.js";
import { stockfishMultipvTool } from "./stockfish.js";

export const TOOLS: ToolDefinition[] = [
  chessdbEvalTool,
  chessdbPvTool,
  openingExplorerTool,
  stockfishMultipvTool,
];

export type { ToolDefinition } from "./types.js";

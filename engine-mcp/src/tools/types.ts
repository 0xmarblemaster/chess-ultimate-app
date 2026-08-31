/** Shared shape for a single engine MCP tool. */
import type { ZodRawShape } from "zod";

export interface ToolResult {
  content: Array<{ type: "text"; text: string }>;
  isError?: boolean;
  // The MCP SDK's CallToolResult carries an open index signature; mirror it so
  // our handlers are assignable to registerTool without a cast.
  [key: string]: unknown;
}

export interface ToolDefinition {
  name: string;
  description: string;
  /** Zod raw shape describing the tool's input arguments. */
  inputSchema: ZodRawShape;
  handler: (args: Record<string, unknown>) => Promise<ToolResult>;
}

/** Wrap an arbitrary JSON-serializable value as an MCP text result. */
export function jsonResult(value: unknown, isError = false): ToolResult {
  return {
    content: [{ type: "text", text: JSON.stringify(value, null, 2) }],
    isError,
  };
}

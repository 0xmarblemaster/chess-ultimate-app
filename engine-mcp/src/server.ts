/** Build the Chesster engine MCP server and register its tools. */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { TOOLS } from "./tools/index.js";

export const SERVER_NAME = "chesster-engine-mcp";
export const SERVER_VERSION = "0.1.0";

/**
 * Construct a fresh `McpServer` with all engine tools registered.
 *
 * A new instance is created per HTTP session so transports never share state.
 */
export function buildServer(): McpServer {
  const server = new McpServer({
    name: SERVER_NAME,
    version: SERVER_VERSION,
  });

  for (const tool of TOOLS) {
    server.registerTool(
      tool.name,
      {
        description: tool.description,
        inputSchema: tool.inputSchema,
      },
      // The MCP SDK validates args against inputSchema before calling us.
      (args: Record<string, unknown>) => tool.handler(args),
    );
  }

  return server;
}

/** Tool names this server advertises, in registration order. */
export const TOOL_NAMES = TOOLS.map((t) => t.name);

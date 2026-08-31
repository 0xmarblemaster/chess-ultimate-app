/**
 * HTTP entry point for the Chesster engine MCP server.
 *
 * Exposes the MCP streamable-HTTP transport at `POST /mcp` on a localhost port
 * (env `PORT`, default 8765). Runs statelessly — a fresh server + transport per
 * request — which is ample for a single-tenant on-box coach and keeps the
 * process free of long-lived session state.
 */
import express, { type Request, type Response } from "express";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { buildServer, SERVER_NAME, SERVER_VERSION, TOOL_NAMES } from "./server.js";

const PORT = Number.parseInt(process.env.PORT ?? "8765", 10);
const HOST = process.env.HOST ?? "127.0.0.1";

const app = express();
app.use(express.json({ limit: "1mb" }));

/** Liveness probe — also lists advertised tools for quick manual checks. */
app.get("/health", (_req: Request, res: Response) => {
  res.json({
    status: "ok",
    service: SERVER_NAME,
    version: SERVER_VERSION,
    tools: TOOL_NAMES,
  });
});

app.post("/mcp", async (req: Request, res: Response) => {
  // Stateless: a new server + transport per request, torn down on close.
  const server = buildServer();
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
  });
  res.on("close", () => {
    void transport.close();
    void server.close();
  });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  } catch (err) {
    console.error("MCP request failed:", err);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: "2.0",
        error: { code: -32603, message: "Internal server error" },
        id: null,
      });
    }
  }
});

// Stateless transport has no session to GET/DELETE against.
const methodNotAllowed = (_req: Request, res: Response) => {
  res.status(405).json({
    jsonrpc: "2.0",
    error: { code: -32000, message: "Method not allowed (stateless server)." },
    id: null,
  });
};
app.get("/mcp", methodNotAllowed);
app.delete("/mcp", methodNotAllowed);

app.listen(PORT, HOST, () => {
  console.error(
    `${SERVER_NAME} v${SERVER_VERSION} listening on http://${HOST}:${PORT}/mcp ` +
      `(tools: ${TOOL_NAMES.join(", ")})`,
  );
});

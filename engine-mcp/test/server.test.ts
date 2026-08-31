/**
 * Smoke test: the server constructs and advertises exactly the four engine
 * tools. Uses an in-memory transport pair so no network or port is involved.
 */
import { describe, it, expect } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { buildServer, TOOL_NAMES } from "../src/server.js";

const EXPECTED_TOOLS = [
  "chessdb_eval",
  "chessdb_pv",
  "opening_explorer",
  "stockfish_multipv",
].sort();

describe("engine MCP server", () => {
  it("advertises exactly the four engine tools", async () => {
    const [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();
    const server = buildServer();
    await server.connect(serverTransport);

    const client = new Client({ name: "smoke-test", version: "1.0.0" });
    await client.connect(clientTransport);

    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual(EXPECTED_TOOLS);

    // Every advertised tool exposes a JSON-Schema input contract.
    for (const tool of tools) {
      expect(tool.inputSchema).toBeTruthy();
      expect(tool.inputSchema.type).toBe("object");
    }

    await client.close();
    await server.close();
  });

  it("TOOL_NAMES matches the advertised set", () => {
    expect([...TOOL_NAMES].sort()).toEqual(EXPECTED_TOOLS);
  });
});

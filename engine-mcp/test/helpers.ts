/** Shared test helpers: a network-free fetch stub and result parsing. */
import type { ToolResult } from "../src/tools/types.js";

export interface MockFetch {
  (input: RequestInfo | URL): Promise<Response>;
  calls: string[];
}

/** Build a fetch stub that returns `body` as JSON for every call. */
export function mockFetch(
  body: unknown,
  { ok = true, status = 200 }: { ok?: boolean; status?: number } = {},
): MockFetch {
  const calls: string[] = [];
  const fn = (async (input: RequestInfo | URL) => {
    calls.push(String(input));
    return {
      ok,
      status,
      json: async () => body,
    } as Response;
  }) as MockFetch;
  fn.calls = calls;
  return fn;
}

/** Parse the JSON text payload out of an MCP tool result. */
export function parseResult(result: ToolResult): any {
  return JSON.parse(result.content[0].text);
}

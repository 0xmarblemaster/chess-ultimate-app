/**
 * Thin HTTP client for the engine MCP tools.
 *
 * Every external call goes through here so timeouts and error handling are
 * uniform: a per-request AbortController timeout, and a Result-style return
 * (`{ ok: true, ... } | { ok: false, error }`) so tool handlers never have to
 * catch a raw throw. The default fetch implementation is injectable to keep the
 * unit tests network-free.
 */

export type FetchLike = typeof fetch;

export interface HttpOptions {
  /** Per-request timeout in milliseconds. */
  timeoutMs?: number;
  /** Extra request headers. */
  headers?: Record<string, string>;
  /** Override the fetch implementation (tests inject a stub). */
  fetchImpl?: FetchLike;
}

export type HttpResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; error: string; status?: number };

const DEFAULT_TIMEOUT_MS = 8000;

/**
 * GET a URL and parse the body as JSON, never throwing.
 *
 * Returns a discriminated result; timeouts, network errors, non-2xx statuses,
 * and JSON-parse failures all collapse into `{ ok: false, error }`.
 */
export async function httpGetJson<T = unknown>(
  url: string,
  options: HttpOptions = {},
): Promise<HttpResult<T>> {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    headers = {},
    fetchImpl = fetch,
  } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const resp = await fetchImpl(url, {
      method: "GET",
      headers: { Accept: "application/json", ...headers },
      signal: controller.signal,
    });
    if (!resp.ok) {
      return { ok: false, status: resp.status, error: `HTTP ${resp.status}` };
    }
    let data: T;
    try {
      data = (await resp.json()) as T;
    } catch {
      return { ok: false, status: resp.status, error: "Invalid JSON response" };
    }
    return { ok: true, status: resp.status, data };
  } catch (err) {
    const name = err instanceof Error ? err.name : "";
    if (name === "AbortError") {
      return { ok: false, error: `Request timed out after ${timeoutMs}ms` };
    }
    const message = err instanceof Error ? err.message : String(err);
    return { ok: false, error: `Request failed: ${message}` };
  } finally {
    clearTimeout(timer);
  }
}

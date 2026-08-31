# Chesster Engine MCP

A lean, self-hosted [Model Context Protocol](https://modelcontextprotocol.io)
server that exposes chess-engine tools to the Chesster AI coach over
**streamable-HTTP**. It depends only on **public APIs** and the **local
Stockfish binary** — no private/paid backends.

Part of Phase 2 of the coach backend upgrade. It is **flag-gated off** on the
Hermes side (`COACH_MCP_ENABLED`), so building and running this server changes
nothing about the live coach until that flag is turned on at deploy time.

## Tools

| Tool | Source | Input | Returns |
| --- | --- | --- | --- |
| `chessdb_eval` | ChessDB public API (`chessdb.cn/cdb.php`) | `{ fen }` | cloud eval (cp) + best move + ranked moves |
| `chessdb_pv` | ChessDB public API | `{ fen }` | principal variation (UCI + SAN) with score/depth |
| `opening_explorer` | Lichess explorer (`explorer.lichess.ovh`) | `{ fen }` | most-played moves + win/draw/loss game counts |
| `stockfish_multipv` | Local `/usr/games/stockfish` (UCI) | `{ fen, depth?, multipv? }` | top-N principal variations with scores |

Unknown positions and upstream failures are returned as graceful
`{ found: false, ... }` / `{ error: ... }` payloads — the tools never throw a
raw error at the caller.

## Build & run

```bash
cd /root/chess-app/engine-mcp
npm ci
npm run build          # tsc -> dist/
npm start              # node dist/index.js
```

For iterating without a build step: `npm run dev` (tsx). Run the tests with
`npm test` (vitest; all external HTTP is mocked, so no network is required — one
Stockfish test uses the real binary if present and is skipped otherwise).

## Environment variables

| Var | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8765` | HTTP port for the `/mcp` endpoint |
| `HOST` | `127.0.0.1` | Bind address (localhost only by default) |
| `STOCKFISH_PATH` | `/usr/games/stockfish` | Path to the UCI engine binary |

Server limits (not env-tunable): Stockfish depth is capped at **22** (default
15) and MultiPV at **5** (default 3), with a per-call timeout.

## Wiring into Hermes (deploy time only)

The Hermes framework already ships a full MCP client. To let the coach reach
these tools, at deploy time:

1. Start this server (`npm start` or `pm2 start ecosystem.config.js`).
2. Merge the block below into the live Hermes config `~/.hermes/config.yaml`
   (a copy lives in [`hermes-mcp-config.example.yaml`](./hermes-mcp-config.example.yaml)).
   **Do not** edit that file as part of Phase 2.
3. Set `COACH_MCP_ENABLED=true` in the Hermes environment. With the flag off,
   the coach's tool declarations are byte-identical to before Phase 2.

```yaml
mcp_servers:
  engine:
    url: "http://127.0.0.1:8765/mcp"
    timeout: 30
    connect_timeout: 15
    sampling:
      enabled: false
```

The framework registers these tools under the toolset `mcp-engine`.

## Quick check — list the tools over HTTP

```bash
# Liveness + advertised tool names:
curl -s http://127.0.0.1:8765/health

# MCP tools/list (streamable-HTTP needs both Accept types). Initialize first:
curl -s -X POST http://127.0.0.1:8765/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}'
```

`/health` returns `{"status":"ok","tools":["chessdb_eval","chessdb_pv","opening_explorer","stockfish_multipv"]}`.

## Deploy

[`ecosystem.config.js`](./ecosystem.config.js) is a PM2 app definition for a
later, deliberate deploy. It is **not** started by Phase 2.

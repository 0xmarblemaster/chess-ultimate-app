// PM2 ecosystem file for the Chesster engine MCP server.
//
// NOT started as part of Phase 2 — this is provided for a later, deliberate
// deploy. To start it at deploy time:
//   cd /root/chess-app/engine-mcp && npm ci && npm run build
//   pm2 start ecosystem.config.js
module.exports = {
  apps: [
    {
      name: "chesster-engine-mcp",
      cwd: "/root/chess-app/engine-mcp",
      script: "dist/index.js",
      interpreter: "node",
      env: {
        HOME: "/root",
        HOST: "127.0.0.1",
        PORT: "8765",
        STOCKFISH_PATH: "/usr/games/stockfish",
      },
      max_restarts: 10,
      restart_delay: 5000,
      watch: false,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
    },
  ],
};

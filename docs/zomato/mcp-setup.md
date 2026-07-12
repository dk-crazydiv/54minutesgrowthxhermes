# Zomato MCP setup

Added to Claude Code local config (2026-07-12):

- `zomato` → `https://mcp-server.zomato.com/mcp` (HTTP transport)

```sh
claude mcp add --transport http zomato https://mcp-server.zomato.com/mcp
```

## Auth

- OAuth; authenticate via `/mcp` → zomato → login.
- Redirect URIs must be whitelisted by Zomato; personal use requested via a form.

## Hermes agent (Telegram) — verified 2026-07-12

- Wired via `scripts/setup-hermes-mcp.sh` → `~/.hermes/config.yaml` (`zomato` entry, `auth: oauth`).
- One-time auth: `hermes mcp login zomato`. Needs a TTY — from a non-TTY shell,
  wrap in a pty: `script -q /dev/null hermes mcp login zomato`. It opens the browser;
  if the browser is already logged into Zomato, consent auto-completes with no clicks
  (localhost redirect via dynamic client registration works despite the whitelist docs).
- Tokens land in `~/.hermes/mcp-tokens/zomato.json` (+ `.client.json`, `.meta.json`).
  Refresh tokens supported, so this should survive restarts. The gateway never does
  interactive OAuth — it only uses these cached tokens, so login must happen before
  (or independent of) the gateway.
- Proven with a real read-only call through the Hermes token: `get_saved_addresses_for_user`
  returned 7 addresses, `success: true`. `hermes mcp list` shows zomato enabled;
  gateway restart picked it up with no zomato errors in `~/.hermes/logs/gateway.log`.
- Streamable HTTP quirk (for direct probes): responses are SSE (`data:` lines); grab
  `mcp-session-id` from the initialize response headers and echo it on later calls.

## Caveats

- Zomato explicitly does NOT allow third-party apps on this MCP yet — testing/personal use only. Treat as comparison/fallback research, not a product dependency.
- Listing source: https://mcpservers.org/servers/github-com-zomato-mcp-server-manifest

# Zomato MCP setup

Added to Claude Code local config (2026-07-12):

- `zomato` → `https://mcp-server.zomato.com/mcp` (HTTP transport)

```sh
claude mcp add --transport http zomato https://mcp-server.zomato.com/mcp
```

## Auth

- OAuth; authenticate via `/mcp` → zomato → login.
- Redirect URIs must be whitelisted by Zomato; personal use requested via a form.

## Caveats

- Zomato explicitly does NOT allow third-party apps on this MCP yet — testing/personal use only. Treat as comparison/fallback research, not a product dependency.
- Listing source: https://mcpservers.org/servers/github-com-zomato-mcp-server-manifest

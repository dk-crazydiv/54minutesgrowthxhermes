# Swiggy MCP setup

Added to Claude Code local config (2026-07-12):

- `swiggy-food` → `https://mcp.swiggy.com/food` (HTTP transport)
- `swiggy-instamart` → `https://mcp.swiggy.com/im` (HTTP transport)
- Also available (not added): `https://mcp.swiggy.com/dineout`

Commands used:

```sh
claude mcp add --transport http swiggy-food https://mcp.swiggy.com/food
claude mcp add --transport http swiggy-instamart https://mcp.swiggy.com/im
```

## Auth

- OAuth 2.1 with PKCE; browser opens for phone + OTP verification.
- Authenticate in Claude Code with `/mcp` → select server → login.
- Dev flow runs against `http://localhost` redirect without production approval; production access requires applying at mcp.swiggy.com/builders/access/.

## Docs

- Developer start: https://mcp.swiggy.com/builders/docs/start/developer/
- Per-framework agent recipes: https://mcp.swiggy.com/builders/docs/start/developer/build-an-agent/
- Docs are agent-friendly (point Claude Code at them directly).

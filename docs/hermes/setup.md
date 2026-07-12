# Hermes Agent setup (Swiggy + Zomato MCP)

Hermes = the [Nous Research Hermes Agent](https://hermes-agent.nousresearch.com/docs/).
It is MCP-native: it reads MCP servers from `~/.hermes/config.yaml` under the
`mcp_servers:` key, discovers their tools at startup, and registers them for tool calling.

## One-shot setup

```sh
./scripts/setup-hermes-mcp.sh
```

Idempotently adds three OAuth HTTP servers to `~/.hermes/config.yaml`
(override path with `HERMES_CONFIG=...`):

```yaml
mcp_servers:
  swiggy-food:
    url: "https://mcp.swiggy.com/food"
    auth: oauth
  swiggy-instamart:
    url: "https://mcp.swiggy.com/im"
    auth: oauth
  zomato:
    url: "https://mcp-server.zomato.com/mcp"
    auth: oauth
```

## Running

```sh
hermes chat
```

- On connect, Hermes prints an authorize URL per server, opens the browser, and
  waits for the OAuth callback on a local loopback port.
  Swiggy auth is phone + OTP; Zomato is OAuth (redirect URIs must be whitelisted —
  see `docs/zomato/mcp-setup.md`).
- After editing the config in a running session, use `/reload-mcp`.

## Notes

- Auth caveats, rate limits, and endpoint details live in
  `docs/swiggy/mcp-setup.md`, `docs/swiggy/mcp-limits.md`,
  `docs/zomato/mcp-setup.md`, `docs/zomato/mcp-limits.md`.
- Unverified: whether Hermes token storage survives Swiggy's 5-day access-token
  expiry gracefully, and Hermes tool-call timeout vs the ~50 s Zomato history
  export (both tracked in `ai_backlog.md`).

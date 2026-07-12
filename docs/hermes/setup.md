# Hermes Agent setup (Swiggy + Zomato MCP)

Hermes = the [Nous Research Hermes Agent](https://hermes-agent.nousresearch.com/docs/).
It is MCP-native: it reads MCP servers from `~/.hermes/config.yaml` under the
`mcp_servers:` key, discovers their tools at startup, and registers them for tool calling.

## Setup — repo-local, no machine-specific state

`bash setup.sh` now runs `scripts/setup-hermes-mcp.sh` automatically as its last
step, so a fresh `git clone && bash setup.sh` gets the MCP servers wired into
`~/.hermes/config.yaml` with no extra step and no dependency on anything
already configured on the machine that built this doc (not Claude Code's own
`claude mcp` config, not a hand-edited `~/.hermes/config.yaml` — those don't
travel with `git clone`). The server list (name, URL, transport) is the only
thing that's repo-carried; it's a plain array at the top of
`scripts/setup-hermes-mcp.sh`, not a generated file, so editing it is a
one-line diff.

You can still run it standalone (e.g. to pick up a new server without a full
reinstall):

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

## What's repo-carried vs. what each teammate does once

Repo-carried (works after `git clone && bash setup.sh`, no manual step):
- Server names, URLs, transport (`scripts/setup-hermes-mcp.sh`, wired into
  `setup.sh`).
- Everything else `setup.sh` already installs into `~/.hermes` from this repo:
  `.env` → `~/.hermes/.env`, `config/SOUL.md` → `~/.hermes/SOUL.md`.

Not repo-carried, by design (auth is per-user, never committed):
- OAuth/OTP login for each server. Tokens land in Hermes's own auth store
  under `~/.hermes` (per-user, per-machine) — nothing to copy from a
  teammate's setup. Each person authenticates themselves the first time by
  running `hermes chat` and completing the printed authorize URL(s): Swiggy
  is phone + OTP, Zomato is OAuth (redirect URI must be pre-whitelisted by
  Zomato — see `docs/zomato/mcp-setup.md`). If Hermes is already running,
  reload with `/reload-mcp` instead of restarting.

Verified 2026-07-12: on a machine whose `~/.hermes/config.yaml` had drifted
(missing `zomato`, an extra hand-added `swiggy-dineout` from an earlier
experiment), re-running `scripts/setup-hermes-mcp.sh` added the missing
`zomato` entry and left the others untouched (idempotent skip). Also
clean-room tested against an empty `HERMES_CONFIG` path with no pre-existing
file — produced the full three-server block, and a second run was a no-op.

## Notes

- Auth caveats, rate limits, and endpoint details live in
  `docs/swiggy/mcp-setup.md`, `docs/swiggy/mcp-limits.md`,
  `docs/zomato/mcp-setup.md`, `docs/zomato/mcp-limits.md`.
- Unverified: whether Hermes token storage survives Swiggy's 5-day access-token
  expiry gracefully, and Hermes tool-call timeout vs the ~50 s Zomato history
  export (both tracked in `ai_backlog.md`).
- Separately, this repo (opened in Claude Code) also has `swiggy-food`,
  `swiggy-instamart`, and `zomato` registered as Claude Code MCP servers —
  but that registration lives in `~/.claude.json` under this machine's
  absolute repo path, is not in git, and does not travel with a clone. That's
  a Claude Code convenience for whoever is driving these sessions, not part
  of the Hermes/Telegram product path documented above; it isn't reproduced
  by `setup.sh`. If a teammate wants the same convenience in their own Claude
  Code session, they'd add a `.mcp.json` at the repo root — not done here to
  keep hackathon scope to the actual product (Hermes on Telegram).

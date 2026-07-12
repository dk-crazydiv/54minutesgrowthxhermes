# Hermes Agent setup (Zomato MCP)

> Swiggy MCP wiring (swiggy-food, swiggy-instamart) was removed 12 Jul after the
> platform decision (`docs/idea.md`): Zomato is the build target, food-only.
> Swiggy research stays in `docs/swiggy/` as reference.

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

Idempotently adds one OAuth HTTP server to `~/.hermes/config.yaml`
(override path with `HERMES_CONFIG=...`):

```yaml
mcp_servers:
  zomato:
    url: "https://mcp-server.zomato.com/mcp"
    auth: oauth
```

## Running

```sh
hermes chat
```

- On connect, Hermes prints an authorize URL for Zomato, opens the browser, and
  waits for the OAuth callback on a local loopback port (redirect URIs must be
  whitelisted — see `docs/zomato/mcp-setup.md`).
- After editing the config in a running session, use `/reload-mcp`.

## Verified live (12 Jul, Jatin's machine)

- `hermes mcp login zomato` is the clean way to do first-time auth (browser OAuth);
  `hermes mcp test zomato` then shows ✓ Connected, 11 tools. Tokens live in Hermes's
  own store — a Claude Code login for the same server does NOT carry over.
- One-shot mode (`hermes -z ... -t zomato`) accepts the toolset name but does not
  actually attach the MCP server ("not connected to this profile") — MCP tools attach
  in real sessions (gateway/chat), not `-z`. Don't use `-z` as an MCP smoke test.
- Gateway startup logs mention MCP not at all; servers connect lazily per session.
  After config or auth changes, restart the gateway
  (`launchctl kickstart -k gui/$UID/ai.hermes.gateway`) or `/reload-mcp` in a session.

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
  running `hermes chat` and completing the printed authorize URL: Zomato is
  OAuth (redirect URI must be pre-whitelisted by Zomato — see
  `docs/zomato/mcp-setup.md`). If Hermes is already running, reload with
  `/reload-mcp` instead of restarting.

Verified 2026-07-12: on a machine whose `~/.hermes/config.yaml` had drifted
(missing `zomato`, an extra hand-added `swiggy-dineout` from an earlier
experiment), re-running `scripts/setup-hermes-mcp.sh` added the missing
`zomato` entry and left the others untouched (idempotent skip). Also
clean-room tested against an empty `HERMES_CONFIG` path with no pre-existing
file — produced the full three-server block, and a second run was a no-op.
(Historical: the script carried three servers at the time. Since 12 Jul it adds
`zomato` only, and the Swiggy entries — including the hand-added
`swiggy-dineout` — were removed from `~/.hermes/config.yaml`.)

## Fresh chat from Telegram (verified 2026-07-12)

Built in — no config needed. `/new` (alias `/reset`) is a native gateway slash
command: it rotates the session ID, clears history/queued messages/approval state,
and starts clean. `/new <title>` names the new session. It's registered in the
Telegram bot command menu automatically (`set_my_commands`). `/compress` manually
compacts a long session without losing it.

## Context limits (defaults inspected 2026-07-12, vendor/hermes-agent/hermes_cli/config.py)

Defaults are sensible for our flows — nothing overridden in `~/.hermes/config.yaml`:

- `compression.enabled: true`, `threshold: 0.50` — auto-compacts history at 50% of the
  model's context window, keeping the last 20 messages (`protect_last_n`) verbatim.
- `tool_output.max_bytes: 50_000` — caps terminal/read_file output. **MCP tool results
  are NOT capped by this** — no config knob exists for MCP result size, so a full
  Zomato history export (39 pages) must be paginated by the agent, never dumped in one call.
- `agent.max_turns` 90 per message (gateway log: "Agent budget: max_iterations=90").
- OAuth note: the gateway runs non-interactive — MCP servers without cached tokens in
  `~/.hermes/mcp-tokens/` are skipped with a warning at startup. Run
  `hermes mcp login <server>` (in a real TTY, or `script -q /dev/null hermes mcp login <server>`)
  once per server, then restart the gateway (`scripts/telegram.sh stop && start-bg`).

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

## Driving the agent from the CLI like a Telegram user (verified 2026-07-12)

`hermes chat -q "<msg>" -Q --pass-session-id` = one non-interactive user turn;
`--resume <session_id>` continues the same conversation (the id is printed on
stdout as `session_id: ...`). This is what `tests/run.sh` uses.

- MCP tools DO attach on this path (unlike `-z` one-shot) — but attach was
  observed flaky once with no `-t` flag; pass `-t hermes-cli,zomato` to get the
  full core toolset (incl. cronjob, memory) plus the Zomato MCP deterministically.
- CLI sessions are separate from Telegram sessions: same `~/.hermes/state.db`,
  different `source` — Telegram `/new` doesn't touch them and vice versa.
- Ground truth for what the agent actually did lives in state.db:
  `messages` (role, tool_name per call) and `sessions`
  (message_count, tool_call_count, model). Grep tool_name there, not transcripts.
- 400 "Unknown Model" trap: config default model can drift (a teammate set
  `openai-codex:gpt-5.5`, which 400s). Pin `-m glm-5.2 --provider zai` for
  reproducible runs.

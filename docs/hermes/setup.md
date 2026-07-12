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

## Telegram end-to-end flow

The supported demo path is Telegram → Hermes gateway → Zomato MCP. It runs in **single-user safe mode**: the Telegram allowlist contains one trusted user and the Zomato token namespace is shared by the default Hermes profile. Do not enable public access until OAuth tokens and live MCP clients are isolated per Telegram user.

### 1. Start the stack

```sh
./run.sh
```

`run.sh` installs/wires Hermes, configures Zomato MCP, runs the brain smoke test, ensures one git watcher is running, and checks or starts the launchd-supervised Telegram gateway. A red smoke test is reported and becomes the final non-zero exit status, but it does not prevent the watcher or gateway from starting.

### 2. First private Zomato request

The user sends a message such as:

```text
What is my last Zomato order?
```

Before any private account action, the bot runs:

```sh
python3 scripts/zomato_chat_oauth.py status
```

If `token_present` is true, it calls the relevant Zomato tools. If false, it must not call account tools or answer from old transcript data; it runs `start` and sends the returned authorization link.

### 3. Login from Telegram

```sh
python3 scripts/zomato_chat_oauth.py start
```

This starts `hermes mcp login zomato` in a detached pseudo-terminal with browser auto-open suppressed, captures the authorization URL, and keeps the localhost callback listener alive.

The bot sends that link with four instructions:

1. Open it and finish Zomato login.
2. The final localhost page may fail on a phone because `127.0.0.1` points to the phone.
3. Copy the full callback URL from the address bar.
4. Paste it only into the originating Telegram chat.

The callback is a short-lived secret. Never echo it, put it in shell arguments, or commit it.

### 4. Relay the callback

When the callback is pasted, the bot runs one foreground command:

```sh
python3 scripts/zomato_chat_oauth.py relay-latest
```

The helper reads the newest callback only from the Telegram session and numeric user ID bound to the pending OAuth transaction, then validates:

- scheme is `http`;
- host is exactly `127.0.0.1`;
- path is exactly `/callback`;
- port matches the active listener;
- `state` matches the pending OAuth transaction;
- `code` is present.

It relays the URL to the host listener, waits a bounded time for token creation, and returns authenticated status. This replaces the old background PTY `submit` + `wait 120` flow; focused verification completes the relay in under three seconds locally. Normal Telegram/model latency may still add several seconds.

Hermes stores credentials under:

```text
~/.hermes/mcp-tokens/zomato.json
~/.hermes/mcp-tokens/zomato.client.json
~/.hermes/mcp-tokens/zomato.meta.json
```

Tokens and client credentials are mode `0600` and never committed.

### 5. Fulfil the original request

After authentication, the bot re-runs auth status, resolves a saved address when required, calls Zomato MCP, and replies in Telegram. Zomato currently exposes 11 tools for addresses, restaurant search, menus, history, tracking, carts, offers, and checkout.

For large history requests, paginate selectively. Do not pull or paste the full account history into a chat turn.

### 6. Logout and prove isolation

The user sends `logout zomato`. The bot runs:

```sh
python3 scripts/zomato_logout.py --json --restart-gateway
```

This removes the Zomato access token and OAuth client file, terminates the verified OAuth worker process group (worker plus its `hermes mcp login` child), clears pending chat OAuth state, preserves provider discovery metadata, and schedules a gateway restart to invalidate any authenticated MCP transport still held in memory. Logout reports failure if the process group cannot be stopped or the gateway restart cannot be scheduled.

A real logout check is:

```sh
python3 scripts/zomato_chat_oauth.py status
hermes mcp test zomato
```

Expected: `token_present` is false and the MCP test requires authentication. Deleting token files alone is not proof of logout; the live gateway connection must also be recycled.

### 7. Money boundary

Tests and autonomous flows must never call `checkout_cart`. In a real order:

1. Build one restaurant cart.
2. Ask the user to choose UPI or cash on delivery.
3. Show the authoritative final bill and delivery details.
4. Warn that Zomato MCP has no cancel/refund tool.
5. Wait for explicit confirmation.
6. Call checkout once. On ambiguity, check tracking/order status before any retry.

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

Not repo-carried, by design (auth is operator/machine-local and never committed):
- OAuth login for Zomato. Tokens land in the default Hermes profile under
  `~/.hermes`; they are **not** isolated per Telegram user. The current gateway
  therefore enforces exactly one numeric `TELEGRAM_ALLOWED_USERS` entry. The
  gateway wrapper validates only the same canonical `~/.hermes/.env` that Hermes
  loads; a divergent repo-local `.env` cannot weaken the runtime allowlist. Each
  teammate authenticates their own single-user instance through the Telegram flow
  above or with `hermes mcp login zomato`.

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

## Web search + voice notes

Wired by `scripts/setup-hermes-search-voice.sh` (runs from `setup.sh`):
Linkup web search with ddgs fallback, and keyless local-whisper STT for
Telegram voice notes. Details and verification: `docs/hermes/search-and-voice.md`.

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

# Agent test harness

Drives the Hermes agent exactly like a Telegram user, but from the CLI, against
the real Zomato MCP (11 tools, OAuth'd).

## The harness

One user turn = one CLI call:

```
hermes chat -q "<message>" -Q --pass-session-id        # fresh conversation
hermes chat -q "<message>" -Q --resume <session_id>    # follow-up turn
```

- `-Q` suppresses the TUI; the reply plus a `session_id: ...` line come out on stdout.
- No `-t` flag: the default session gets the same toolsets the gateway uses,
  including the Zomato MCP (connects lazily, uses tokens in `~/.hermes/mcp-tokens/`)
  and the cron tool. (`hermes -z` one-shot mode does NOT attach MCP — don't use it.)
- Turn counts and tool calls are verified after each run straight from
  `~/.hermes/state.db` (`sessions` / `messages` tables), not from the transcript.

**CLI sessions are separate from Telegram sessions.** Both land in the same
`state.db`, but a Telegram `/new` or ongoing chat never sees or disturbs these
test sessions, and the tests never touch the running gateway. Confirmed: the
smoke session created by this harness appears in state.db with its own id while
the gateway keeps its own.

## Running

```
bash tests/run.sh        # all 6 cases
bash tests/run.sh 3      # just case 3
bash tests/run.sh 1 4 6  # a subset
```

Transcripts land in `tests/out/` (gitignored raw output), results append to
`tests/results.md`.

## Cases

1. Saved addresses (smoke, fresh conv)
2. 3 recommendations mined from order history (must paginate, never all 39 pages)
3. Multi-turn: #2 then "order the first one" — cart + final bill, then STOP.
   **HARD RULE: checkout_cart must never be called. The harness checks the DB
   and fails loudly if it ever fires — that's real money.**
4. Lifetime + monthly stats from history
5. Monthly stats email via Hermes cron (discovery — FAIL documents what's missing)
6. Preference memory: set "no hot drinks when sunny", then list preferences

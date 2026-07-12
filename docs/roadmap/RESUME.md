# Resume

Start every session here. Read OBJECTIVE.md once if you're new. Then run the watcher.

## First move, every session

```
bash bootstrap/watch_git.sh once        # exit 0 up to date, 3 new commits, 2 no remote
```

If it exits 3, read the reported branches with `git log origin/<branch>` before anything
else. Workers talk through pushes. Deciding whether to pull is the manager's job, and it
happens before new work starts.

Keep it running while you work:

```
bash bootstrap/watch_git.sh start-bg    # poll every 60s (-i 30 to change)
bash bootstrap/watch_git.sh status|stop|logs
```

## New teammate? Do this once

You need three things this repo can't carry: the `.env` secrets (get them from Kartik),
a Claude Code session, and ten minutes.

**Shortcut: `./run.sh` does all of it** — setup, codex as default brain, zomato MCP,
smoke, watcher, gateway — and prints the standard instructions. Steps below are the
manual version.

1. Clone, then `bash setup.sh`. It vendors Hermes v2026.7.7.2 and wires `~/.hermes`.
2. Drop the `.env` Kartik gives you in the repo root, run setup again, then
   `bash scripts/smoke.sh`. Both brains must say PONG.
3. Start Claude Code in the repo. It reads `CLAUDE.md`, which points back here.
   Project permissions are already committed in `.claude/settings.json`, so you won't
   be prompted for every command.
4. Your Fable is a manager too: it runs the watcher, publishes its own mission-control
   page from `docs/roadmap/mission-control.html` (its own URL, rewritten not appended),
   and appends its session ID to `docs/roadmap/CHANGELOG.md` with every push.
5. Coordination is git only: pull before push, small commits, commit messages say
   what changed and what's proven.

## Where things stand

- This repo is stood up: `setup.sh` ran, all three brains (glm, minimax, codex) answer
  PONG from `smoke.sh`, and the gateway is running in the background
  (bot: @swiggy_mcp_buildathon_bot).
- The build target is the Zomato Companion Agent (food only) — `docs/idea.md`.
  **Zomato MCP is wired and proven**: OAuth'd, 11 tools, real read-only call returned
  Kartik's saved addresses. Notes in `docs/zomato/`.
- Landing page is live at https://zomato-companion.pages.dev (`site/`), signups stored
  in Convex (`backend/`, prod deployment cheerful-crow-656). Power-ups earning:
  Cloudflare + Convex.
- Debug dashboard: `python3 scripts/debug-dashboard.py` → http://127.0.0.1:8787 —
  shows Telegram queries, brain used, tool calls, errors, live from Hermes state.db.
- Fresh chat from Telegram is native: `/new` resets the session, `/compress` compacts.
  MCP tool results have NO size cap — paginate big pulls (docs/hermes/setup.md).
- **The whole team is on one thing now: prove the use cases live over Telegram.**
  The list is the Now section of BACKLOG.md.
- **North star: `docs/roadmap/SCORE.md`** — honest Revenue-track self-score (74 right
  now) and the ranked points-per-hour moves. Optimize against it.
- In flight (subagents, will land on main): a runnable test suite in `tests/` that
  drives the agent as a mock Telegram user (CLI sessions are separate from Kartik's
  Telegram thread — tests never touch his context, and NEVER call checkout_cart);
  a per-user memory store in `users/<id>/` (Kartik's full Zomato history as CSV so
  history queries stop re-pulling 39 pages); a session-grouped debug dashboard +
  refreshed mission-control.html.
- Priyam is building per-Telegram-user Zomato auth separately; the users/ folder
  naming expects a telegram user id. Pick it up when his push lands (watcher will say).
- **Everyone works on the `3pmdemo` branch now** — commit and push there, not main. The remote is
  `github.com/dk-crazydiv/54minutesgrowthxhermes`. The watcher runs clean against it.
- Every push updates `docs/roadmap/CHANGELOG.md`: what happened, the proof, and the
  session ID of the Fable that did it.

## Hard facts

- Hermes pinned at `v2026.7.7.2`, vendored in `vendor/hermes-agent` by `setup.sh`.
- Gateway control: `scripts/telegram.sh start|start-bg|stop|status|logs`.
  Log at `~/.hermes/logs/gateway.log`.
- Brains smoke test: `scripts/smoke.sh` (glm + minimax must answer PONG).
- Secrets: `.env` (gitignored), copied to `~/.hermes/.env` by setup.sh. Source keys live
  in the opencode auth store at `~/.local/share/opencode/auth.json`.
- Persona: `config/SOUL.md`, installed to `~/.hermes/SOUL.md`.
- Work queue: `docs/roadmap/BACKLOG.md`. Runbook: `docs/roadmap/ORCHESTRATION.md`.
  Voice: `docs/roadmap/TONE.md`.

## Rules that keep biting

- The gateway must run on the host, never in a task sandbox.
- Never retry anything that spends money. Never commit a secret.
- Same failure twice means stop and fix the cause, then note it here.

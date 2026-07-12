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

- This repo is stood up: `setup.sh` ran, both brains answer PONG from `smoke.sh`,
  and the gateway is running in the background. One live phone check still pending.
- The gateway is a background process, not a service. It dies with a reboot. Top ops gap.
- The bot token leaked once in a board comment and still needs rotating.
- Codex is not enabled yet, but Hermes ships the provider. It reads `~/.codex/auth.json`
  from the Codex CLI. One login plus a smoke case turns it on.
- Everyone works on main, no branches. The remote is
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

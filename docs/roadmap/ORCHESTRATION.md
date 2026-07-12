# Orchestration: how work runs here

## The loop

1. Manager picks the next items from BACKLOG.md and writes a short brief per task.
2. Each task goes to a worker Fable in its own session. Everyone works on main.
   No branch ceremony. Speed over process. Workers on nearby code coordinate by
   splitting files, not branches.
3. Workers commit small and push often. The commit message is the status update:
   what changed, what's proven, what's blocked.
4. The manager's git watcher (`bootstrap/watch_git.sh`) reports new pushes. The manager
   pulls at the next clean moment, reads the diff, and files problems as new tasks.
5. Work gets verified live (smoke script, real Telegram message) before its backlog
   line is deleted. Git remembers finished work; the docs don't.

## Channels

Everything flows through git and these docs. No side files, no chat-only decisions.
If an instruction will apply again, it gets written into the right doc the same turn.

- Current state → RESUME.md (rewritten, never appended)
- Work → BACKLOG.md
- How-to → this file
- Manager ↔ Kartik → the mission-control artifact, rewritten at every meaningful
  transition, same URL every time
- **Update mission control before every git push.** No exceptions. A push without a
  fresh mission-control page means Kartik reads stale state. Kartik's rule, standing.

## Worker rules

- Work on main. Small commits with plain-spoken messages. Pull before you push.
- Every "done" claim ships with proof in the commit: a command run and its real output,
  a log line, a screenshot path. No proof, no done.
- Blocked? Commit what you have with `BLOCKED:` leading the message and say exactly
  what you need. The manager watches for it.
- Never touch `~/.hermes` live config in a way you can't roll back. `.env` and
  `auth.json` values never go in a commit.

## Standing choices

- Hermes stays pinned at `v2026.7.7.2`, vendored by `setup.sh`. Upgrades are their own
  task with a smoke run as the gate.
- Cheap brain first: MiniMax for chatty turns, GLM for thinking. Codex joins for
  code-heavy work once verified. Escalate on a real failure, not in advance.
- The gateway runs on the host, not in a sandbox, and gets restarted through
  `scripts/telegram.sh` only.
- Repeated a command twice? It becomes a script in `bootstrap/`.
- Same failure twice? Stop and fix the cause, and note it in RESUME.md's gotchas.

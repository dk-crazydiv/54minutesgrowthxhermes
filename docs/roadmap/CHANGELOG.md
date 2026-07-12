# Changelog

Newest first. One entry per meaningful event: what happened, why it matters, and where
the evidence lives. Session IDs let you find the full transcript later. Every manager
session appends here before pushing.

## July 12 — Codex brain live, all three brains green

Manager session: Claude Code `8de96528-6adc-4f8b-920c-67a8b031cf3c` (Fable, manager).

- Codex works through Hermes on Kartik's ChatGPT subscription. Proof: `PONG` from
  `hermes -z ... --provider openai-codex --model gpt-5.5`, and `scripts/smoke.sh`
  now reports "Smoke OK: all three brains answered."
- The route that works is importing Codex CLI tokens directly (documented in
  `docs/setup_docs/codex_setup.md`). `hermes auth add openai-codex` forces a fresh
  device login and got rate-limited (429) — avoid it when `~/.codex/auth.json` exists.
- Added the codex case to `scripts/smoke.sh`. It skips with a note when no Codex
  tokens are set up, so teammates without a ChatGPT subscription still get green.
- Wrote `docs/setup_docs/`: `codex_setup.md`, `glm_setup.md`, `telegram_setup.md` —
  the proven steps, gotchas included.
- Added root `ACTIVE_AGENTS.md`: which brains and surfaces run on this machine.
  Committed once as a template, then gitignored, so each teammate keeps their own.
- New standing rule from Kartik in ORCHESTRATION.md: update mission control before
  every git push.

## July 12 — repo stood up, planning done

Manager session: Claude Code `8de96528-6adc-4f8b-920c-67a8b031cf3c` (Fable, manager).
Mission control: https://claude.ai/code/artifact/f75cb413-03c9-40bb-989b-2da2e0028078

- Moved the project home from the scratch repo (`~/work/tmp/buildathon`) to this repo.
  Copied over: `setup.sh`, `scripts/telegram.sh`, `scripts/smoke.sh`, `config/SOUL.md`,
  `.env.example`, `docs/PROJECT_NOTES.md`, `docs/UNDERSTANDING.md`, and the `.env`
  (gitignored, never committed).
- Wrote the living docs in `docs/roadmap/`: RESUME (entrypoint), BACKLOG,
  ORCHESTRATION, OBJECTIVE, TONE, and this changelog.
- Built and tested `bootstrap/watch_git.sh`. It fetches and reports pushes, never
  pulls. Proven against a temp remote (detected 2 pushed commits, exit 3) and clean
  against the real remote (exit 0).
- Ran `setup.sh` here: Hermes v2026.7.7.2 vendored, deps hash-verified, installed at
  `~/.local/bin/hermes`. Proof: setup exit 0.
- Smoke test green in this repo: GLM and MiniMax both answered PONG via
  `scripts/smoke.sh`.
- Started the Telegram gateway from this repo (`scripts/telegram.sh start-bg`).
  Still a background process, not a service. Live phone check pending.
- Committed project permissions in `.claude/settings.json` so teammates aren't
  prompted for commands inside this repo. Denies stay on sudo, force-push, and
  reading secrets files.
- Wrote the teammate onboarding path into RESUME.md: clone, setup, secrets from
  Kartik, own mission-control page per manager Fable, session ID in this changelog
  on every push.
- Decision: everyone works on main, no branches, pull before push. Kartik's call,
  logged in ORCHESTRATION.md.
- Find: Hermes already ships the `openai-codex` provider
  (`vendor/hermes-agent/plugins/model-providers/openai-codex/`), reading Codex CLI
  creds from `~/.codex/auth.json`. Codex needs a login and a smoke case, not a build.

## Before this repo (from the scratch-repo notes)

History from `~/work/tmp/buildathon` and taskit board 7 (`localhost:9100`), kept in
`docs/PROJECT_NOTES.md`:

- Telegram gateway proven live on GLM, first reply ~13s (operator-verified).
- `scripts/smoke.sh` green on GLM + MiniMax, proof recorded at `.proof/task-349/`.
- Hermes install pinned to tag `v2026.7.7.2`, hash-verified, vendored (task 348-352
  era on board 7).
- Known problem carried forward: the bot token leaked in a board comment. Rotation is
  on the backlog.

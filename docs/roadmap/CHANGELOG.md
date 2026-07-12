# Changelog

Newest first. One entry per meaningful event: what happened, why it matters, and where
the evidence lives. Session IDs let you find the full transcript later. Every manager
session appends here before pushing.

## July 12 — GrowthX handbook saved to the repo

Worker session: Claude Code (Opus), pushed as priyam307. Not a manager session, so no
mission-control page went with it.

- Saved the full GrowthX x Hermes Builder Handbook offline under `growthx-handbook/`, so
  the rubric and rules don't need the live site mid-build. 16 markdown files: an index,
  the 12 sections, and the scoring rubric split one file per track under
  `scoring-tracks/`. Pushed in commit `e5bc086`.
- The source page is a JavaScript app. A plain fetch got only the shell. What worked:
  pull the server-rendered HTML with curl (998 KB) and strip the tags to text, then
  hand-write the markdown from that.
- Gap: the 93-idea library is loaded by JavaScript and isn't in the HTML, so it's not
  captured. `growthx-handbook/07-idea-library.md` says so and links back to the live page.
- Added a `/changelog` command at `.claude/commands/changelog.md`. It appends to this
  file, in this format, from git history. Removed a stray root `CHANGELOG.md` I had
  started before this one existed — this is the only changelog.
- Left alone: an untracked `docs/hermes/telegram-setup.md` I didn't write. Looks like an
  old copy of `docs/setup_docs/telegram_setup.md`. Flagging, not touching.

## July 12 — Swiggy/Zomato MCP research done, Hermes wired to both

Commits: `8758870` (rate-limit research), `c99a536` (Hermes MCP setup).

- Researched the Swiggy MCP's real capabilities and limits — no rate limit today
  (planned: 120 req/min/user), Food history is last 5 orders only, Instamart 15 days,
  order cap < ₹1,000, COD only, checkout is NOT idempotent. All in
  `docs/swiggy/mcp-limits.md` with a quick-answers table.
- Same for Zomato, measured empirically against the live server — no rate limit hit
  at ~125 req/min, lifetime order history (777 orders back to 2017 exported), UPI QR
  or COD only. `docs/zomato/mcp-limits.md`, full tool dump in
  `docs/zomato/tools/tools.json`, order history export in `docs/zomato/data/`.
- Wrote `scripts/setup-hermes-mcp.sh`: idempotently adds swiggy-food,
  swiggy-instamart, and zomato as OAuth HTTP servers to `~/.hermes/config.yaml`.
  Steps and gotchas in `docs/hermes/setup.md`.

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

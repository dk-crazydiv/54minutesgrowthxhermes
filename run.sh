#!/usr/bin/env bash
# Team starter. One command, standard setup for everyone: ./run.sh
# Idempotent — safe to re-run anytime.
set -e
cd "$(dirname "$0")"

echo "== 1/6 base setup (vendors hermes, wires ~/.hermes)"
bash setup.sh

echo "== 2/6 default brain: codex (gpt-5.4-mini) — fast, no GLM struggles"
hermes config set model.provider openai-codex >/dev/null
hermes config set model.default gpt-5.4-mini >/dev/null

echo "== 3/6 zomato MCP"
bash scripts/setup-hermes-mcp.sh

echo "== 4/6 smoke (all brains must PONG)"
smoke_rc=0
bash scripts/smoke.sh || smoke_rc=$?
if [ "$smoke_rc" -ne 0 ]; then
  echo "WARN: brain smoke is red; continuing so watcher and Telegram gateway still start." >&2
fi

echo "== 5/6 git watcher"
bash bootstrap/watch_git.sh start-bg || true

echo "== 6/6 telegram gateway"
bash scripts/telegram.sh status || bash scripts/telegram.sh start-bg

cat <<'EOF'

Ready. Standard instructions for everyone:
  1. Read docs/roadmap/RESUME.md — state of play, then BACKLOG.md — the work.
  2. North star: docs/roadmap/SCORE.md. Everything serves the four Telegram proofs.
  3. Debug what the bot did: python3 scripts/debug-dashboard.py → http://127.0.0.1:8787
  4. Git: main only. Pull --rebase before push. Small commits. Push often.
  5. Never call checkout_cart in tests — real money. Kartik gives the final yes.
EOF

exit "$smoke_rc"

#!/usr/bin/env bash
# ============================================================================
# scripts/telegram.sh — start/stop/status the hermes telegram gateway.
# ----------------------------------------------------------------------------
# The telegram gateway is the front door of the food copilot: it is the
# process that polls Telegram for the human's messages, routes them through
# the hermes agent (glm thinks, minimax replies), and sends the answer back.
#
# This script is a thin wrapper around `hermes gateway` so the human has one
# memorable command for the whole lifecycle. It expects `bash setup.sh` to
# have run (hermes installed + keys in .env + persona in ~/.hermes/SOUL.md).
#
# Usage:
#   bash scripts/telegram.sh start     # launch the gateway (foreground, logs to tty + file)
#   bash scripts/telegram.sh stop      # stop a running gateway
#   bash scripts/telegram.sh restart   # stop, then start
#   bash scripts/telegram.sh status    # is the gateway up? shows the pid if so
#   bash scripts/telegram.sh logs      # tail the gateway log (Ctrl-C to exit)
#
# Logs:
#   The gateway writes a structured log at ~/.hermes/logs/gateway.log
#   (profile-aware: $HERMES_HOME/logs/gateway.log). `logs` tails it. A
#   round-trip shows up as an inbound [telegram] message line followed by an
#   agent turn and the outbound reply.
#
# Required in .env (see .env.example + README "Telegram gateway"):
#   TELEGRAM_BOT_TOKEN   — from @BotFather (/newbot)
#   TELEGRAM_ALLOWED_USERS — your numeric Telegram user ID
# ============================================================================
set -euo pipefail

GATEWAY_LOG="${HERMES_HOME:-$HOME/.hermes}/logs/gateway.log"

cd "$(dirname "$0")/.."

# Put hermes + uv on PATH (setup.sh symlinks hermes into ~/.local/bin).
export PATH="${HERMES_HOME:-$HOME/.hermes}/venv/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

log()  { printf "\033[1;36m⚕\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }
die()  { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; exit 1; }

command -v hermes >/dev/null 2>&1 || die "hermes not on PATH. Run: bash setup.sh"

# Read a value out of .env without sourcing it (keep secrets out of the shell).
get_env_value() {
    local key="$1"
    grep -E "^${key}=" .env 2>/dev/null | head -1 | cut -d= -f2- || true
}

preflight() {
    [ -f .env ] || die "no .env at $(pwd)/.env. Run: cp .env.example .env and fill in (see README)."
    local token user_id
    token="$(get_env_value TELEGRAM_BOT_TOKEN)"
    user_id="$(get_env_value TELEGRAM_ALLOWED_USERS)"
    if [ -z "${token// /}" ]; then
        die "TELEGRAM_BOT_TOKEN is empty in .env. Get one from @BotFather (/newbot) and paste it. See README."
    fi
    if [ -z "${user_id// /}" ]; then
        warn "TELEGRAM_ALLOWED_USERS is empty — nobody will be authorized to talk to the bot."
        warn "Find your numeric user ID with @userinfobot and set TELEGRAM_ALLOWED_USERS in .env."
    fi
}

case "${1:-status}" in
    start)
        preflight
        log "Starting hermes telegram gateway (logs: $GATEWAY_LOG)..."
        # Foreground is the reliable shape in a non-systemd container/WSL box:
        # the gateway is the process; Ctrl-C stops it cleanly. `--force` lets a
        # second dispatcher replace a stale one if a prior run didn't exit.
        exec hermes gateway run --force
        ;;
    start-bg|daemon)
        preflight
        mkdir -p "$(dirname "$GATEWAY_LOG")"
        log "Starting hermes telegram gateway in the background (logs: $GATEWAY_LOG)..."
        nohup hermes gateway run --force >>"$GATEWAY_LOG" 2>&1 &
        echo $! > "${HERMES_HOME:-$HOME/.hermes}/gateway.pid"
        ok "Gateway launched (pid $!). Tail with: bash scripts/telegram.sh logs"
        ;;
    stop)
        log "Stopping hermes telegram gateway..."
        hermes gateway stop 2>/dev/null || true
        # Also reap a background dispatcher this script may have launched.
        local_pid_file="${HERMES_HOME:-$HOME/.hermes}/gateway.pid"
        if [ -f "$local_pid_file" ]; then
            pid="$(cat "$local_pid_file" 2>/dev/null || true)"
            if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
            rm -f "$local_pid_file"
        fi
        ok "Stop requested."
        ;;
    restart)
        "$0" stop || true
        sleep 2
        "$0" start
        ;;
    status)
        hermes gateway status
        if [ -f "$GATEWAY_LOG" ]; then
            echo "  log: $GATEWAY_LOG"
        fi
        ;;
    logs)
        [ -f "$GATEWAY_LOG" ] || die "no gateway log yet at $GATEWAY_LOG (start the gateway first)."
        log "Tailing $GATEWAY_LOG (Ctrl-C to exit)..."
        tail -n 100 -f "$GATEWAY_LOG"
        ;;
    *)
        die "unknown command: ${1:-}. Use: start | start-bg | stop | restart | status | logs"
        ;;
esac

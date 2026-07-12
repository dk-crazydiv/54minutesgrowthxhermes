#!/usr/bin/env bash
# Manage the launchd/systemd-supervised Hermes Telegram gateway.
#
# Usage:
#   bash scripts/telegram.sh start|start-bg|restart|stop|status|logs
set -euo pipefail

cd "$(dirname "$0")/.."
export PATH="${HERMES_HOME:-$HOME/.hermes}/venv/bin:/usr/local/bin:$HOME/.local/bin:$PATH"

HERMES_DIR="${HERMES_HOME:-$HOME/.hermes}"
GATEWAY_LOG="$HERMES_DIR/logs/gateway.log"
ENV_FILE="$HERMES_DIR/.env"

log()  { printf "\033[1;36m⚕\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }
die()  { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; exit 1; }

command -v hermes >/dev/null 2>&1 || die "hermes not on PATH. Run: bash setup.sh"

preflight() {
    [ -f "$ENV_FILE" ] || die "no canonical $ENV_FILE. Run setup and add Telegram credentials."
    python3 scripts/zomato_runtime_safety.py validate-telegram-env --env "$ENV_FILE" >/dev/null \
        || die "unsafe Telegram environment in $ENV_FILE"
}

case "${1:-status}" in
    start|start-bg|daemon)
        preflight
        log "Installing/starting the supervised Hermes gateway..."
        status_out="$(hermes gateway status 2>&1 || true)"
        if [[ "$status_out" != *"Service definition matches"* ]]; then
            hermes gateway stop >/dev/null 2>&1 || true
            hermes gateway install --force --no-start-now
        fi
        hermes gateway start
        hermes gateway status
        ;;
    stop)
        log "Stopping the supervised Hermes gateway..."
        hermes gateway stop
        ok "Gateway stopped."
        ;;
    restart)
        preflight
        log "Restarting the supervised Hermes gateway..."
        hermes gateway restart
        hermes gateway status
        ;;
    status)
        hermes gateway status
        [ ! -f "$GATEWAY_LOG" ] || echo "  log: $GATEWAY_LOG"
        ;;
    logs)
        [ -f "$GATEWAY_LOG" ] || die "no gateway log at $GATEWAY_LOG"
        log "Tailing $GATEWAY_LOG (Ctrl-C to exit)..."
        tail -n 100 -f "$GATEWAY_LOG"
        ;;
    *)
        die "unknown command: ${1:-}. Use: start | restart | stop | status | logs"
        ;;
esac

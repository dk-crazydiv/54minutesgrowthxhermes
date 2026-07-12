#!/usr/bin/env bash
# Wire web search (Linkup, ddgs fallback) + voice-note STT into Hermes.
# Idempotent — safe to re-run. See docs/hermes/search-and-voice.md.
#
#   1. Installs the web-linkup plugin (config/hermes-plugins/web-linkup)
#      into ~/.hermes/plugins/ and enables it in config.yaml.
#   2. Sets web.search_backend: linkup (provider falls back to ddgs until
#      LINKUP_API_KEY appears in ~/.hermes/.env, so search never breaks).
#   3. Installs faster-whisper into the Hermes venv so the built-in local
#      STT provider (stt.enabled: true, already default) can transcribe
#      Telegram voice notes with no API key.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME_DIR:-$HOME/.hermes}"
HERMES_CONFIG="${HERMES_CONFIG:-$HERMES_HOME/config.yaml}"
HERMES_VENV_PY="$HERMES_HOME/hermes-agent/venv/bin/python"

log() { printf '\033[1;34m[search-voice]\033[0m %s\n' "$*"; }

# ---- 1. install plugin -------------------------------------------------------
mkdir -p "$HERMES_HOME/plugins"
rsync -a --delete --exclude '__pycache__' \
    "$REPO_ROOT/config/hermes-plugins/web-linkup/" \
    "$HERMES_HOME/plugins/web-linkup/"
log "plugin synced -> $HERMES_HOME/plugins/web-linkup"

# ---- 2. config.yaml: enable plugin + select search backend -------------------
"$HERMES_VENV_PY" - "$HERMES_CONFIG" <<'PY'
import sys, yaml

path = sys.argv[1]
with open(path) as f:
    cfg = yaml.safe_load(f) or {}

changed = False

plugins = cfg.setdefault("plugins", {})
enabled = plugins.setdefault("enabled", [])
if "web-linkup" not in enabled:
    enabled.append("web-linkup")
    changed = True

web = cfg.setdefault("web", {})
if web.get("search_backend") != "linkup":
    web["search_backend"] = "linkup"
    changed = True

stt = cfg.setdefault("stt", {})
if stt.get("enabled") is not True:
    stt["enabled"] = True
    changed = True

if changed:
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False,
                       allow_unicode=True)
    print("[search-voice] config.yaml updated (plugins.enabled, web.search_backend, stt.enabled)")
else:
    print("[search-voice] config.yaml already wired (no-op)")
PY

# ---- 3. faster-whisper for keyless local STT ---------------------------------
if "$HERMES_VENV_PY" -c 'import faster_whisper' 2>/dev/null; then
    log "faster-whisper already installed (no-op)"
else
    log "installing faster-whisper into the Hermes venv (one-time, ~100MB)..."
    "$HERMES_VENV_PY" -m pip install --quiet faster-whisper
    log "faster-whisper installed"
fi

log "done. Restart the gateway to pick this up:"
log "  launchctl kickstart -k gui/\$(id -u)/ai.hermes.gateway"

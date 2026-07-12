#!/usr/bin/env bash
# ============================================================================
# scripts/smoke.sh — ask each brain one question through hermes.
# ----------------------------------------------------------------------------
# For each model endpoint configured in .env (glm, minimax), invoke
# `hermes -z "<prompt>" --provider <p> --model <m>` and capture whatever the
# model emits. Transcripts go to stdout; a brain passes only when its complete
# trimmed response is exactly PONG.
#
# Required:
#   - bash setup.sh           (installs hermes + symlinks to ~/.local/bin)
#   - .env with GLM_API_KEY and MINIMAX_API_KEY (see README for how to fill)
#
# This is a smoke test, not a benchmark. The prompt is deliberately small so
# the run finishes in seconds. Use it to confirm keys, wiring, and reachability
# before exercising the agent loop end-to-end.
# ============================================================================
set -uo pipefail

PROMPT="${SMOKE_PROMPT:-Reply with exactly one word: PONG}"
GLM_MODEL="${GLM_MODEL:-glm-5}"
MINIMAX_MODEL="${MINIMAX_MODEL:-MiniMax-M3}"
CODEX_MODEL="${CODEX_MODEL:-gpt-5.5}"

cd "$(dirname "$0")/.."

# Prefer a teammate's repo-local .env, but use Hermes' canonical env when this
# checkout intentionally carries no secrets.
ENV_FILE=".env"
[ -f "$ENV_FILE" ] || ENV_FILE="${HERMES_HOME:-$HOME/.hermes}/.env"

# Pull keys from .env without sourcing it (we don't want to leak values into
# the caller's shell).
get_env_value() {
    local key="$1"
    grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- || true
}

if [ ! -f "$ENV_FILE" ]; then
    echo "ERR: no repo .env and no ${HERMES_HOME:-$HOME/.hermes}/.env. Run setup and add credentials." >&2
    exit 1
fi

GLM_KEY="$(get_env_value GLM_API_KEY)"
MINIMAX_KEY="$(get_env_value MINIMAX_API_KEY)"

if [ -z "${GLM_KEY// /}" ]; then
    echo "WARN: GLM_API_KEY is empty in $ENV_FILE; GLM will be recorded as failed." >&2
fi
if [ -z "${MINIMAX_KEY// /}" ]; then
    echo "WARN: MINIMAX_API_KEY is empty in $ENV_FILE; MiniMax will be recorded as failed." >&2
fi

command -v hermes >/dev/null 2>&1 || {
    echo "ERR: hermes not on PATH. Run: bash setup.sh" >&2
    exit 1
}

is_exact_pong() {
    local normalized
    normalized="$(printf '%s' "$1" | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ "$normalized" = "PONG" ]
}

run_brain() {
    local label="$1"
    local provider="$2"
    local model="$3"
    local api_key="$4"
    local env_var="$5"

    echo
    echo "============================================================"
    echo "  brain: $label  (provider=$provider, model=$model)"
    echo "============================================================"

    local out="" rc=0
    if out=$(HERMES_YOLO_MODE=1 env "$env_var=$api_key" \
        hermes -z "$PROMPT" --provider "$provider" --model "$model" 2>&1); then
        rc=0
    else
        rc=$?
    fi

    if [ $rc -ne 0 ] || ! is_exact_pong "$out"; then
        echo "(expected an exact PONG line; rc=$rc, output below)"
        echo "$out" | sed 's/^/    /'
        return 1
    fi

    echo "$out" | sed 's/^/    /'
    return 0
}

# Codex rides on OAuth tokens in the hermes auth store, not an .env key.
# Optional: skipped with a warning if not set up (see docs/setup_docs/codex_setup.md).
run_codex() {
    echo
    echo "============================================================"
    echo "  brain: codex   (OpenAI via ChatGPT subscription, model=$CODEX_MODEL)"
    echo "============================================================"
    local out="" rc=0
    if out=$(HERMES_YOLO_MODE=1 \
        hermes -z "$PROMPT" --provider openai-codex --model "$CODEX_MODEL" 2>&1); then
        rc=0
    else
        rc=$?
    fi
    if [ $rc -ne 0 ] || ! is_exact_pong "$out"; then
        if echo "$out" | grep -q "No Codex credentials"; then
            echo "    (skipped: no Codex credentials. See docs/setup_docs/codex_setup.md)"
            return 2
        fi
        echo "(expected an exact PONG line; rc=$rc, output below)"
        echo "$out" | sed 's/^/    /'
        return 1
    fi
    echo "$out" | sed 's/^/    /'
    return 0
}

run_brain "glm     (Z.AI thinking brain)" zai     "$GLM_MODEL"     "$GLM_KEY"    "GLM_API_KEY"
rc1=$?
run_brain "minimax (MiniMax chatty brain)" minimax "$MINIMAX_MODEL" "$MINIMAX_KEY" "MINIMAX_API_KEY"
rc2=$?
run_codex
rc3=$?

echo
if [ $rc1 -eq 0 ] && [ $rc2 -eq 0 ] && [ $rc3 -ne 1 ]; then
    if [ $rc3 -eq 2 ]; then
        echo "Smoke OK: glm + minimax answered (codex skipped, not set up)."
    else
        echo "Smoke OK: all three brains answered."
    fi
    exit 0
fi
echo "Smoke FAIL: a brain did not answer (glm=$rc1, minimax=$rc2, codex=$rc3)."
exit 1

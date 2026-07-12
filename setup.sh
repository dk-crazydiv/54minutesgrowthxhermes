#!/usr/bin/env bash
# ============================================================================
# setup.sh — install Hermes Agent for the food-buildathon, pinned to a tag.
# ----------------------------------------------------------------------------
# Why this shape (vs. `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`):
#   - Reproducible. The curl installer is a moving target — the script behind
#     the URL changes whenever upstream edits it. We pin to a git tag so
#     `setup.sh twice` produces the same install every time.
#   - Hash-verified. `setup-hermes.sh` runs `uv sync --extra all --locked`,
#     which checks every transitive against uv.lock's SHA256 hashes. A
#     compromised PyPI release is REJECTED at install time.
#   - Self-contained. Clone lives under vendor/hermes-agent in this repo so
#     one `rm -rf vendor && bash setup.sh` rebuilds the same tree from a
#     fresh clone.
#
# Idempotent. `bash setup.sh` twice is a no-op the second time around, provided
# the pinned tag and uv.lock are unchanged. Re-running rebuilds the venv from
# the lockfile (uv's fast path is hash-verified; identical lockfile → identical
# tree).
#
# Required: bash, git, python3 (>= 3.11, < 3.14). uv is fetched automatically.
# ============================================================================
set -euo pipefail

# ---- configuration ---------------------------------------------------------
HERMES_REPO_URL="https://github.com/NousResearch/hermes-agent.git"
HERMES_PIN="${HERMES_PIN:-v2026.7.7.2}"

# Project root, resolved from this script's own location so it stays correct
# regardless of where setup.sh is invoked from (it cd's into the vendored
# checkout below). Falls back to the invoking cwd if BASH_SOURCE is unavailable.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# Install under ./vendor/ so the toolchain lives with this repo. Override with
# HERMES_VENDOR_DIR if you want a different layout (e.g. for shared machines).
HERMES_VENDOR_DIR="${HERMES_VENDOR_DIR:-$PROJECT_ROOT/vendor/hermes-agent}"

# uv picks the highest available Python. Cap at <3.14 because Rust-backed
# transitives (pydantic-core, etc.) don't have cp314 wheels yet and a fresh
# distro auto-picker would otherwise fall back to a maturin source build
# that fails.
PYTHON_VERSION="3.11"

# ---- logging ---------------------------------------------------------------
log()  { printf "\033[1;36m⚕\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }
die()  { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; exit 1; }

# ---- preflight -------------------------------------------------------------
command -v git     >/dev/null 2>&1 || die "git is required"
command -v python3 >/dev/null 2>&1 || die "python3 is required"

PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PY_MAJOR" -ne 3 ] || [ "$PY_MINOR" -lt 11 ] || [ "$PY_MINOR" -ge 14 ]; then
    die "Python 3.11 or 3.12 required (got $(python3 --version 2>&1)); uv will provision one automatically."
fi

# ---- locate or install uv --------------------------------------------------
# uv picks its install dir from XDG_BIN_HOME, fallback to ~/.local/bin, with
# XDG_DATA_HOME/../bin as another fallback. Search the common spots.
UV_CMD=""
if command -v uv >/dev/null 2>&1; then
    UV_CMD="uv"
else
    for candidate in \
        "$HOME/.local/bin/uv" \
        "$HOME/.cargo/bin/uv" \
        "${XDG_BIN_HOME:-}/uv" \
        "$(dirname "${XDG_DATA_HOME:-/usr/share}" 2>/dev/null)/bin/uv" \
        /opt/uv/bin/uv
    do
        if [ -x "$candidate" ]; then
            UV_CMD="$candidate"
            break
        fi
    done
fi

if [ -z "$UV_CMD" ]; then
    log "Installing uv (Python package manager, no root needed)..."
    UV_INSTALLER="$(mktemp)"
    if ! command -v curl >/dev/null 2>&1; then
        die "curl is required to bootstrap uv. Install it or set HERMES_UV=/path/to/uv."
    fi
    curl -fsSL https://astral.sh/uv/install.sh -o "$UV_INSTALLER"
    sh "$UV_INSTALLER"
    rm -f "$UV_INSTALLER"
    # The installer picks XDG_BIN_HOME / ~/.local/bin / XDG_DATA_HOME/../bin
    # depending on environment. Search again.
    for candidate in \
        "$HOME/.local/bin/uv" \
        "$HOME/.cargo/bin/uv" \
        "${XDG_BIN_HOME:-}/uv" \
        "$(dirname "${XDG_DATA_HOME:-/usr/share}" 2>/dev/null)/bin/uv"
    do
        if [ -x "$candidate" ]; then
            UV_CMD="$candidate"
            break
        fi
    done
fi

if [ -z "$UV_CMD" ] || ! command -v "$UV_CMD" >/dev/null 2>&1; then
    die "uv not found on PATH after install. Add \$HOME/.local/bin to PATH and retry."
fi
ok "uv $($UV_CMD --version)"

# ---- ensure ~/.local/bin and uv's bin dir are on PATH ----------------------
# hermes' in-repo setup-hermes.sh uses `command -v uv` to detect uv; we must
# put uv's actual install path on PATH before invoking it. The upstream
# installer chose /mnt/bin here because XDG_DATA_HOME=/mnt/odin-xdg-data,
# but on a normal host it'll be ~/.local/bin or ~/.cargo/bin.
mkdir -p "$HOME/.local/bin"
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH";;
esac
_UV_BIN_DIR="$(dirname "$UV_CMD")"
case ":$PATH:" in
    *":${_UV_BIN_DIR}:"*) ;;
    *) export PATH="${_UV_BIN_DIR}:$PATH";;
esac
log "PATH primed: uv at $UV_CMD"

# ---- clone (or update) the pinned hermes checkout ---------------------------
log "Ensuring hermes checkout at $HERMES_VENDOR_DIR (pinned to $HERMES_PIN)..."
mkdir -p "$(dirname "$HERMES_VENDOR_DIR")"

if [ -d "$HERMES_VENDOR_DIR/.git" ]; then
    # Existing checkout. Make sure it's pinned to the right commit.
    cd "$HERMES_VENDOR_DIR"
    # Avoid touching dirty work-trees.
    if ! git diff --quiet HEAD 2>/dev/null; then
        warn "Existing hermes checkout at $HERMES_VENDOR_DIR has uncommitted changes."
        warn "Skipping checkout update; install will use the current HEAD."
    else
        # Fetch enough to find the tag even if our depth=1 clone missed it.
        git fetch --depth=64 origin "refs/tags/${HERMES_PIN}:refs/tags/${HERMES_PIN}" 2>/dev/null || true
        if git rev-parse -q --verify "refs/tags/${HERMES_PIN}^{}" >/dev/null; then
            git checkout --quiet --detach "refs/tags/${HERMES_PIN}^{}" 2>/dev/null \
                || git checkout --quiet --detach "$HERMES_PIN" 2>/dev/null \
                || warn "Could not move existing checkout to $HERMES_PIN; using current HEAD."
        elif git rev-parse -q --verify "$HERMES_PIN" >/dev/null; then
            git checkout --quiet --detach "$HERMES_PIN" 2>/dev/null \
                || warn "Could not move existing checkout to $HERMES_PIN; using current HEAD."
        else
            warn "Tag $HERMES_PIN not found in existing checkout; using current HEAD."
        fi
    fi
    cd - >/dev/null
else
    log "Cloning hermes-agent (depth=1, pinned to $HERMES_PIN)..."
    if ! git clone --depth=1 --branch "$HERMES_PIN" "$HERMES_REPO_URL" "$HERMES_VENDOR_DIR"; then
        # Some refs/tags aren't usable as --branch (annotated tags don't always
        # work). Fall back to depth-clone then checkout.
        git clone --depth=1 "$HERMES_REPO_URL" "$HERMES_VENDOR_DIR"
        git -C "$HERMES_VENDOR_DIR" fetch --depth=64 origin "refs/tags/${HERMES_PIN}:refs/tags/${HERMES_PIN}" 2>/dev/null || true
        git -C "$HERMES_VENDOR_DIR" checkout --quiet --detach "$HERMES_PIN" 2>/dev/null \
            || die "Could not pin to $HERMES_PIN; check that the tag exists."
    fi
fi

PINNED_SHA=$(git -C "$HERMES_VENDOR_DIR" rev-parse HEAD)
ok "Hermes source ready: $PINNED_SHA ($HERMES_PIN)"

# ---- non-interactive install via setup-hermes.sh ----------------------------
# setup-hermes.sh has two interactive `read -p` prompts (one for ripgrep,
# one for the setup wizard). Closing stdin makes it exit silently on those
# without breaking the rest of the script — each `read` is guarded by
# `[[ ! -t 0 ]]` style fallthroughs only at the very end, and the upstream
# script is already built to handle non-TTY environments.
cd "$HERMES_VENDOR_DIR"
chmod +x setup-hermes.sh

# Pull our project's .env into hermes's expected location. Hermes reads
# $HERMES_HOME/.env (default ~/.hermes/.env) — see hermes_cli/env_loader.py
# `load_hermes_dotenv`: the user env (~/.hermes/.env) is loaded with
# override=True, so it is the canonical home for the gateway's bot token and
# the model keys. Project .env wins over hermes's defaults via dotenv
# precedence. We write there directly (absolute path), not into the vendored
# checkout, so `hermes gateway` and `hermes` CLI both see the same secrets.
#
# $PROJECT_ROOT was resolved from setup.sh's own location at the top of the
# file — it survives the `cd "$HERMES_VENDOR_DIR"` above.
HERMES_HOME_DIR="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$HERMES_HOME_DIR"
if [ -n "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/.env" ]; then
    log "Sourcing keys from $PROJECT_ROOT/.env into $HERMES_HOME_DIR/.env"
    umask 077
    {
        echo "# Generated by $(basename "$0") on $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "# Local dev keys from $PROJECT_ROOT/.env — do not commit this file."
        cat "$PROJECT_ROOT/.env"
    } > "$HERMES_HOME_DIR/.env"
    chmod 600 "$HERMES_HOME_DIR/.env"
elif [ -n "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/.env.example" ]; then
    log "No project .env found; copying $PROJECT_ROOT/.env.example as a placeholder"
    cp "$PROJECT_ROOT/.env.example" "$HERMES_HOME_DIR/.env"
    chmod 600 "$HERMES_HOME_DIR/.env"
fi

# Install the project persona (config/SOUL.md) into $HERMES_HOME so the
# food-copilot identity + the three-nevers / read-only-era guardrails land in
# the hermes system prompt for every surface (CLI + telegram gateway). Hermes
# auto-injects SOUL.md into the system prompt unless --ignore-rules is passed,
# so this is the seam where the UNDERSTANDING.md guardrails become runtime
# behavior. Only overwrite when our project copy is present and differs from
# what's installed, so a hand-edited SOUL.md is not clobbered byte-for-byte.
if [ -n "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/config/SOUL.md" ]; then
    if [ ! -f "$HERMES_HOME_DIR/SOUL.md" ] \
       || ! cmp -s "$PROJECT_ROOT/config/SOUL.md" "$HERMES_HOME_DIR/SOUL.md"; then
        log "Installing food-copilot persona into $HERMES_HOME_DIR/SOUL.md"
        umask 077
        cp "$PROJECT_ROOT/config/SOUL.md" "$HERMES_HOME_DIR/SOUL.md"
        chmod 600 "$HERMES_HOME_DIR/SOUL.md"
    fi
fi

log "Running setup-hermes.sh (locked, hash-verified uv sync)..."
# Pipe `n\nn\n` to answer ripgrep prompt and setup-wizard prompt with "no".
printf "n\nn\n" | ./setup-hermes.sh </dev/null || {
    rc=$?
    # setup-hermes.sh exits non-zero if the user declines the wizard. That's
    # fine — the install completed; only the wizard was skipped.
    if [ -x "$HERMES_VENDOR_DIR/venv/bin/hermes" ]; then
        warn "setup-hermes.sh exited $rc after the install completed (interactive prompts declined). Continuing."
    else
        die "setup-hermes.sh failed without producing a hermes binary."
    fi
}
cd - >/dev/null

# ---- final wiring ----------------------------------------------------------
HERMES_BIN="$HERMES_VENDOR_DIR/venv/bin/hermes"
[ -x "$HERMES_BIN" ] || die "Hermes CLI not found at $HERMES_BIN after install"

# Symlink the vendored hermes into ~/.local/bin so it's on PATH.
if [ "$(readlink -f "$HOME/.local/bin/hermes" 2>/dev/null || true)" != "$(readlink -f "$HERMES_BIN" 2>/dev/null || true)" ]; then
    ln -sf "$HERMES_BIN" "$HOME/.local/bin/hermes"
fi

ok "Hermes installed: $(command -v hermes || echo "$HOME/.local/bin/hermes")"
echo
log "Smoke test:"
echo "    bash scripts/smoke.sh"
echo

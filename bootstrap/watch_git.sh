#!/usr/bin/env bash
# ============================================================================
# bootstrap/watch_git.sh — polling git watcher for the manager session.
# ----------------------------------------------------------------------------
# Every N seconds (default 60) it runs `git fetch --all --quiet` and compares
# each remote-tracking branch against the last SHA it saw (state lives in
# .git/watch_git_state). When a branch moved, it prints one plain line per
# branch and appends the same line to bootstrap/git_watch.log.
#
# It NEVER pulls and NEVER merges — it only reports. The manager decides
# when to pull.
#
# Usage:
#   bash bootstrap/watch_git.sh once [repo]        # single check: exit 0 = up to date, 3 = new commits, 2 = no remote
#   bash bootstrap/watch_git.sh start [repo]       # watch loop in the foreground (Ctrl-C to stop)
#   bash bootstrap/watch_git.sh start-bg [repo]    # watch loop via nohup, pid in .git/watch_git.pid
#   bash bootstrap/watch_git.sh stop [repo]        # stop a background watcher
#   bash bootstrap/watch_git.sh status [repo]      # is the watcher up? shows pid + log path
#   bash bootstrap/watch_git.sh logs [repo]        # tail the watch log (Ctrl-C to exit)
#
# Interval: -i SECONDS flag or WATCH_INTERVAL env var (flag wins), default 60.
#   bash bootstrap/watch_git.sh -i 30 start
#
# Repo path is the optional last argument; default is this script's repo root.
# ============================================================================
set -euo pipefail

INTERVAL="${WATCH_INTERVAL:-60}"

log()  { printf "\033[1;36m⚕\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }
die()  { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; exit 1; }

# ---- args: [-i SECONDS] <command> [repo] -----------------------------------
while [ "${1:-}" = "-i" ]; do
    shift
    INTERVAL="${1:?-i needs a number of seconds}"
    shift
done
CMD="${1:-status}"
REPO="${2:-}"

# Default repo = the repo this script lives in.
if [ -z "$REPO" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    REPO="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || true)"
fi
[ -n "$REPO" ] && [ -d "$REPO" ] || die "not a git repo: '${REPO:-?}'"

GIT_DIR="$(git -C "$REPO" rev-parse --git-dir)"
case "$GIT_DIR" in /*) : ;; *) GIT_DIR="$REPO/$GIT_DIR" ;; esac

STATE_FILE="$GIT_DIR/watch_git_state"
PID_FILE="$GIT_DIR/watch_git.pid"
WATCH_LOG="$REPO/bootstrap/git_watch.log"

preflight() {
    # No remote means nothing to watch — say so clearly and bow out.
    if [ -z "$(git -C "$REPO" remote)" ]; then
        warn "repo at $REPO has no remote configured — nothing to watch."
        warn "add one with: git -C $REPO remote add origin <url>"
        exit 2
    fi
}

# List "sha refname" for every remote-tracking branch (skip symbolic HEADs).
remote_branches() {
    git -C "$REPO" for-each-ref --format='%(objectname) %(refname:short)' refs/remotes \
        | grep -v '/HEAD$' || true
}

# One fetch-and-compare pass. Prints a line per moved branch (stdout + log).
# Returns 0 if up to date, 3 if anything moved.
check_once() {
    git -C "$REPO" fetch --all --quiet || warn "git fetch failed (offline?); comparing what we have."
    touch "$STATE_FILE"
    local changed=0 now sha ref old line
    now="$(date '+%Y-%m-%d %H:%M')"
    while read -r sha ref; do
        [ -n "$sha" ] || continue
        old="$(grep -F " $ref" "$STATE_FILE" | awk -v r="$ref" '$2==r {print $1}' | head -1 || true)"
        if [ -z "$old" ]; then
            # First sighting: record it silently, no noise on a fresh state file.
            printf '%s %s\n' "$sha" "$ref" >> "$STATE_FILE"
        elif [ "$old" != "$sha" ]; then
            changed=1
            local count subject
            count="$(git -C "$REPO" rev-list --count "$old..$sha" 2>/dev/null || echo '?')"
            subject="$(git -C "$REPO" log -1 --format=%s "$sha" 2>/dev/null || echo '?')"
            line="[$now] $ref: $count new commits ($(echo "$old" | cut -c1-7)..$(echo "$sha" | cut -c1-7)) — \"$subject\""
            echo "$line"
            mkdir -p "$(dirname "$WATCH_LOG")"
            echo "$line" >> "$WATCH_LOG"
        fi
    done <<EOF
$(remote_branches)
EOF
    # Rewrite state to current SHAs (also drops deleted branches).
    remote_branches > "$STATE_FILE"
    [ "$changed" -eq 0 ] && return 0 || return 3
}

watch_loop() {
    log "Watching $REPO every ${INTERVAL}s (log: $WATCH_LOG). Never pulls — reports only."
    while :; do
        check_once || true
        sleep "$INTERVAL"
    done
}

case "$CMD" in
    once)
        preflight
        if check_once; then
            ok "up to date"
            exit 0
        else
            exit 3
        fi
        ;;
    start)
        preflight
        watch_loop
        ;;
    start-bg|daemon)
        preflight
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            die "watcher already running (pid $(cat "$PID_FILE")). Use: stop"
        fi
        mkdir -p "$(dirname "$WATCH_LOG")"
        nohup "$0" -i "$INTERVAL" start "$REPO" >>"$WATCH_LOG" 2>&1 &
        echo $! > "$PID_FILE"
        ok "Watcher launched (pid $!). Tail with: bash bootstrap/watch_git.sh logs"
        ;;
    stop)
        if [ -f "$PID_FILE" ]; then
            pid="$(cat "$PID_FILE" 2>/dev/null || true)"
            if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
                ok "Stopped watcher (pid $pid)."
            else
                warn "pid file was stale."
            fi
            rm -f "$PID_FILE"
        else
            warn "no watcher pid file — nothing to stop."
        fi
        ;;
    status)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            ok "watcher running (pid $(cat "$PID_FILE"))"
        else
            log "watcher not running"
        fi
        echo "  repo:  $REPO"
        echo "  state: $STATE_FILE"
        [ -f "$WATCH_LOG" ] && echo "  log:   $WATCH_LOG"
        ;;
    logs)
        [ -f "$WATCH_LOG" ] || die "no watch log yet at $WATCH_LOG (nothing has changed, or watcher never ran)."
        log "Tailing $WATCH_LOG (Ctrl-C to exit)..."
        tail -n 100 -f "$WATCH_LOG"
        ;;
    *)
        die "unknown command: $CMD. Use: once | start | start-bg | stop | status | logs"
        ;;
esac

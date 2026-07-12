#!/usr/bin/env python3
"""Shared Telegram/Zomato runtime safety checks.

Keeps dotenv interpretation and OAuth process-group teardown identical across the
shell gateway wrapper, OAuth bridge, and logout helper.
"""
from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

SECURITY_ENV_KEYS = {
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_USERS",
    "TELEGRAM_ALLOW_ALL_USERS",
}
TRUTHY = {"1", "true", "yes", "on"}


def parse_dotenv(path: Path) -> tuple[dict[str, str], set[str]]:
    """Parse the dotenv subset Hermes uses and flag duplicate security keys."""
    values: dict[str, str] = {}
    seen: set[str] = set()
    duplicates: set[str] = set()
    if not path.exists():
        raise ValueError(f"environment file not found: {path}")
    for raw_line in path.read_text(errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        lexer = shlex.shlex(raw_value, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = "#"
        parsed = list(lexer)
        value = parsed[0].strip() if parsed else ""
        if key in SECURITY_ENV_KEYS and key in seen:
            duplicates.add(key)
        seen.add(key)
        values[key] = value
    return values, duplicates


def validate_telegram_env(path: Path) -> str:
    values, duplicates = parse_dotenv(path)
    if duplicates:
        names = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate security-sensitive dotenv entries: {names}")
    token = values.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is empty")
    raw_users = values.get("TELEGRAM_ALLOWED_USERS", "")
    users = [value.strip() for value in raw_users.replace(" ", ",").split(",") if value.strip()]
    allow_all = values.get("TELEGRAM_ALLOW_ALL_USERS", "").strip().lower() in TRUTHY
    if allow_all:
        # OPEN MODE — explicitly opted into ALL Telegram users. This is UNSAFE
        # while the Zomato MCP uses a single shared token: every user shares that
        # one Zomato account (data + payment) until per-user isolation lands.
        # Permitted deliberately; return the owner id (first numeric allowlist
        # entry) for OAuth session binding, or "*" when no owner is pinned. Only
        # an explicit truthy value opens the door — a typo never silently does.
        owner = next((user for user in users if user.isdigit()), "")
        return owner or "*"
    if len(users) != 1 or not users[0].isdigit():
        raise ValueError("single-user Zomato mode requires exactly one numeric TELEGRAM_ALLOWED_USERS entry")
    return users[0]


def pid_running(pid: object) -> bool:
    try:
        os.kill(int(str(pid)), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def is_oauth_worker(pid: object) -> bool:
    if not pid_running(pid):
        return False
    try:
        command = subprocess.run(
            ["ps", "-p", str(int(str(pid))), "-o", "command="],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return False
    return "zomato_chat_oauth.py" in command and "_worker" in command


def process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def wait_for_group_exit(process_group_id: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while process_group_exists(process_group_id) and time.monotonic() < deadline:
        time.sleep(0.05)
    return not process_group_exists(process_group_id)


def terminate_oauth_worker_group(pid: object, grace_seconds: float = 2.0) -> bool:
    if not is_oauth_worker(pid):
        return not pid_running(pid)
    worker_pid = int(str(pid))
    try:
        process_group_id = os.getpgid(worker_pid)
        if process_group_id != worker_pid:
            return False
        os.killpg(process_group_id, signal.SIGTERM)
        if wait_for_group_exit(process_group_id, grace_seconds):
            return True
        os.killpg(process_group_id, signal.SIGKILL)
        return wait_for_group_exit(process_group_id, grace_seconds)
    except OSError:
        return not process_group_exists(worker_pid)


def main() -> int:
    parser = argparse.ArgumentParser(description="Shared Telegram/Zomato safety checks")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate-telegram-env")
    validate.add_argument("--env", required=True)
    args = parser.parse_args()
    try:
        user_id = validate_telegram_env(Path(args.env).expanduser())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(user_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

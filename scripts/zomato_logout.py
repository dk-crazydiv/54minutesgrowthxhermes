#!/usr/bin/env python3
"""Logout helper for the hackathon Zomato MCP OAuth demo.

Clears only local Hermes Zomato OAuth credentials/state:
- ~/.hermes/mcp-tokens/zomato.json
- ~/.hermes/mcp-tokens/zomato.client.json
- ~/.hermes/zomato-oauth-broker/pending.json

It intentionally keeps zomato.meta.json because that is provider discovery
metadata, not a user login/session token.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from zomato_runtime_safety import pid_running, terminate_oauth_worker_group


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()


def logout(home: Path) -> dict[str, object]:
    chat_state = home / "zomato-chat-oauth" / "state.json"
    oauth_process_stopped = not chat_state.exists()
    if chat_state.exists():
        try:
            worker_pid = json.loads(chat_state.read_text()).get("worker_pid")
            oauth_process_stopped = not pid_running(worker_pid) or terminate_oauth_worker_group(worker_pid)
        except (OSError, ValueError, TypeError, json.JSONDecodeError, subprocess.SubprocessError):
            oauth_process_stopped = False

    targets = [
        home / "mcp-tokens" / "zomato.json",
        home / "mcp-tokens" / "zomato.client.json",
        home / "zomato-oauth-broker" / "pending.json",
    ]
    if oauth_process_stopped:
        targets.append(chat_state)
    removed: list[str] = []
    absent: list[str] = []
    for path in targets:
        if path.exists():
            path.unlink()
            removed.append(str(path))
        else:
            absent.append(str(path))

    token_absent = not (home / "mcp-tokens" / "zomato.json").exists()
    client_absent = not (home / "mcp-tokens" / "zomato.client.json").exists()
    pending_absent = not (home / "zomato-oauth-broker" / "pending.json").exists()
    chat_oauth_absent = not (home / "zomato-chat-oauth" / "state.json").exists()
    return {
        "ok": token_absent and client_absent and pending_absent and chat_oauth_absent and oauth_process_stopped,
        "removed": removed,
        "already_absent": absent,
        "metadata_kept": str(home / "mcp-tokens" / "zomato.meta.json"),
        "token_absent": token_absent,
        "client_absent": client_absent,
        "pending_absent": pending_absent,
        "chat_oauth_absent": chat_oauth_absent,
        "oauth_process_stopped": oauth_process_stopped,
    }


def schedule_gateway_restart(delay_seconds: int = 2) -> bool:
    """Restart the gateway after this command has returned its chat response."""
    hermes = shutil.which("hermes")
    if not hermes:
        return False
    subprocess.Popen(
        ["/bin/sh", "-c", 'sleep "$1"; exec "$2" gateway restart', "zomato-logout", str(delay_seconds), hermes],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear local Zomato MCP OAuth session state.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--restart-gateway",
        action="store_true",
        help="Schedule a gateway restart so an in-memory authenticated MCP connection is invalidated.",
    )
    args = parser.parse_args()

    result = logout(hermes_home())
    if args.restart_gateway:
        restart_scheduled = schedule_gateway_restart()
        result["gateway_restart_scheduled"] = restart_scheduled
        result["ok"] = bool(result.get("ok")) and restart_scheduled
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("ok"):
            print("Zomato logged out ✅")
            print("Cleared the local Zomato OAuth token/client and pending broker state.")
        else:
            print("Zomato logout incomplete; inspect the JSON status and gateway state.")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

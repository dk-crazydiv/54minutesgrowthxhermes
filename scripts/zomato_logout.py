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
import signal
import subprocess
from pathlib import Path


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()


def logout(home: Path) -> dict[str, object]:
    chat_state = home / "zomato-chat-oauth" / "state.json"
    if chat_state.exists():
        try:
            worker_pid = json.loads(chat_state.read_text()).get("worker_pid")
            if worker_pid:
                os.kill(int(worker_pid), signal.SIGTERM)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    targets = [
        home / "mcp-tokens" / "zomato.json",
        home / "mcp-tokens" / "zomato.client.json",
        home / "zomato-oauth-broker" / "pending.json",
        home / "zomato-chat-oauth" / "state.json",
    ]
    removed: list[str] = []
    absent: list[str] = []
    for path in targets:
        if path.exists():
            path.unlink()
            removed.append(str(path))
        else:
            absent.append(str(path))

    return {
        "ok": True,
        "removed": removed,
        "already_absent": absent,
        "metadata_kept": str(home / "mcp-tokens" / "zomato.meta.json"),
        "token_absent": not (home / "mcp-tokens" / "zomato.json").exists(),
        "client_absent": not (home / "mcp-tokens" / "zomato.client.json").exists(),
        "pending_absent": not (home / "zomato-oauth-broker" / "pending.json").exists(),
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
        result["gateway_restart_scheduled"] = schedule_gateway_restart()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Zomato logged out ✅")
        print("Cleared the local Zomato OAuth token/client and pending broker state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

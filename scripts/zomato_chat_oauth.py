#!/usr/bin/env python3
"""Launch and relay Zomato localhost OAuth from a Telegram conversation.

`start` launches `hermes mcp login zomato` in a detached pseudo-terminal,
prevents automatic browser opening, and returns the authorization URL. The user
opens it from Telegram. On a phone, the localhost redirect fails as expected;
the user pastes that full redirect URL back to the bot. `relay` validates and
forwards it to the waiting listener on this Mac.

Authorization URLs and callback URLs contain one-time secrets. JSON output from
`start` intentionally includes the authorization URL so the bot can send it;
`relay` never prints the supplied callback URL or authorization code.
"""
from __future__ import annotations

import argparse
import json
import os
import pty
import re
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

AUTH_URL_RE = re.compile(r"https://mcp-server\.zomato\.com/authorize\?[^\s\x1b]+")
SERVER_NAME = "zomato"


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()


def state_dir(home: Path) -> Path:
    return home / "zomato-chat-oauth"


def state_path(home: Path) -> Path:
    return state_dir(home) / "state.json"


def log_path(home: Path) -> Path:
    return state_dir(home) / "oauth.log"


def token_path(home: Path) -> Path:
    return home / "mcp-tokens" / f"{SERVER_NAME}.json"


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    tmp.chmod(0o600)
    os.replace(tmp, path)


def read_state(home: Path) -> dict:
    path = state_path(home)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def pid_running(pid: object) -> bool:
    try:
        os.kill(int(str(pid)), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def stop_existing(home: Path) -> None:
    state = read_state(home)
    pid = state.get("worker_pid")
    if pid_running(pid):
        try:
            os.kill(int(str(pid)), signal.SIGTERM)
        except OSError:
            pass
    state_path(home).unlink(missing_ok=True)


def worker(home_arg: str) -> int:
    home = Path(home_arg).expanduser()
    directory = state_dir(home)
    directory.mkdir(parents=True, exist_ok=True)
    output_path = log_path(home)
    output_path.write_text("")
    output_path.chmod(0o600)

    master_fd, slave_fd = pty.openpty()
    env = dict(os.environ, HERMES_HOME=str(home), SSH_TTY="telegram-oauth")
    child = subprocess.Popen(
        ["hermes", "mcp", "login", SERVER_NAME],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        close_fds=True,
    )
    os.close(slave_fd)
    atomic_write_json(
        state_path(home),
        {"worker_pid": os.getpid(), "child_pid": child.pid, "status": "starting", "created_at": time.time()},
    )

    buffer = ""
    try:
        with output_path.open("a", encoding="utf-8") as log:
            while True:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                log.write(text)
                log.flush()
                buffer += text
                match = AUTH_URL_RE.search(buffer)
                if match:
                    auth_url = match.group(0).rstrip("\r")
                    parsed = urlparse(auth_url)
                    query = parse_qs(parsed.query)
                    redirect_uri = (query.get("redirect_uri") or [""])[0]
                    oauth_state = (query.get("state") or [""])[0]
                    callback = urlparse(redirect_uri)
                    atomic_write_json(
                        state_path(home),
                        {
                            "worker_pid": os.getpid(),
                            "child_pid": child.pid,
                            "status": "waiting_for_callback",
                            "created_at": time.time(),
                            "auth_url": auth_url,
                            "callback_port": callback.port,
                            "oauth_state": oauth_state,
                        },
                    )
                    buffer = buffer[-8192:]
    finally:
        os.close(master_fd)
        return_code = child.wait()
        state = read_state(home)
        state.update(
            {
                "status": "authenticated" if return_code == 0 and token_path(home).exists() else "exited",
                "return_code": return_code,
                "finished_at": time.time(),
            }
        )
        # Do not retain the one-time authorization URL/state after completion.
        state.pop("auth_url", None)
        state.pop("oauth_state", None)
        atomic_write_json(state_path(home), state)
    return 0


def start(home: Path, timeout: float = 15.0) -> dict[str, object]:
    if token_path(home).exists():
        return {"ok": True, "status": "already_authenticated"}

    state = read_state(home)
    if state.get("status") == "waiting_for_callback" and pid_running(state.get("worker_pid")):
        return {
            "ok": True,
            "status": "waiting_for_callback",
            "authorization_url": state.get("auth_url"),
            "callback_port": state.get("callback_port"),
        }

    stop_existing(home)
    state_dir(home).mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "_worker", "--home", str(home)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )

    deadline = time.time() + timeout
    while time.time() < deadline:
        state = read_state(home)
        if state.get("status") == "waiting_for_callback" and state.get("auth_url"):
            return {
                "ok": True,
                "status": "waiting_for_callback",
                "authorization_url": state["auth_url"],
                "callback_port": state.get("callback_port"),
            }
        if state.get("status") == "authenticated" or token_path(home).exists():
            return {"ok": True, "status": "authenticated"}
        time.sleep(0.2)
    return {"ok": False, "status": "start_timeout", "message": "OAuth listener did not produce a link."}


def relay(raw_url: str, home: Path) -> dict[str, object]:
    value = raw_url.strip()
    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.path != "/callback":
        raise ValueError("callback must be http://127.0.0.1:<port>/callback")
    if not parsed.port or not (query.get("code") and query.get("state")):
        raise ValueError("callback must include a port, code, and state")

    state = read_state(home)
    if state.get("status") != "waiting_for_callback" or not pid_running(state.get("worker_pid")):
        raise ValueError("no active Zomato OAuth listener; start login again")
    if int(state.get("callback_port") or 0) != parsed.port:
        raise ValueError("callback port does not match the active listener")
    if str(state.get("oauth_state") or "") != query["state"][0]:
        raise ValueError("callback state does not match the active login")

    response = requests.get(value, timeout=15)
    deadline = time.time() + 15
    while time.time() < deadline and not token_path(home).exists():
        time.sleep(0.25)
    return {
        "ok": response.ok and token_path(home).exists(),
        "status": "authenticated" if token_path(home).exists() else "callback_relayed",
        "http_status": response.status_code,
        "token_present": token_path(home).exists(),
    }


def latest_callback_from_session(home: Path) -> str:
    """Read the latest localhost OAuth callback pasted by a user.

    This avoids a background PTY + submit + wait tool loop in Telegram. The
    callback still passes through relay(), which validates host, path, port,
    and OAuth state against the active listener before making a local request.
    """
    database = home / "state.db"
    if not database.exists():
        raise ValueError("Hermes session database not found")
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT content
            FROM messages
            WHERE role = 'user'
              AND content LIKE 'http://127.0.0.1:%/callback?%'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    if not row or not row[0]:
        raise ValueError("no pasted localhost callback found")
    return str(row[0]).strip()


def status(home: Path) -> dict[str, object]:
    state = read_state(home)
    return {
        "ok": True,
        "status": "authenticated" if token_path(home).exists() else state.get("status", "disconnected"),
        "token_present": token_path(home).exists(),
        "listener_running": pid_running(state.get("worker_pid")),
        "callback_port": state.get("callback_port"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram-friendly Zomato localhost OAuth bridge.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("start")
    relay_parser = sub.add_parser("relay")
    relay_parser.add_argument("--url", help="Full localhost callback URL. If omitted, read one stdin line.")
    sub.add_parser("relay-latest", help="Relay the latest callback pasted into a Hermes chat.")
    sub.add_parser("status")
    worker_parser = sub.add_parser("_worker")
    worker_parser.add_argument("--home", required=True)
    args = parser.parse_args()

    if args.command == "_worker":
        return worker(args.home)

    home = hermes_home()
    try:
        if args.command == "start":
            result = start(home)
        elif args.command == "relay":
            # Read one callback URL line. Using read() waits for EOF, which makes
            # Telegram's PTY submit path hang until its process wait timeout.
            raw = args.url if args.url is not None else sys.stdin.readline()
            result = relay(raw, home)
        elif args.command == "relay-latest":
            result = relay(latest_callback_from_session(home), home)
        else:
            result = status(home)
    except (ValueError, requests.RequestException) as exc:
        result = {"ok": False, "status": "error", "message": str(exc)}
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

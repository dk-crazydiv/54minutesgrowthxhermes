import importlib.util
import json
import os
import signal
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import call, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(module_name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_telegram_session(
    home: Path,
    callback: str,
    *,
    user_id: str = "12345",
    session_id: str = "telegram-session",
    other_callback: str | None = None,
) -> None:
    (home / ".env").write_text(
        f"TELEGRAM_BOT_TOKEN=dummy-token\nTELEGRAM_ALLOWED_USERS={user_id}\n"
    )
    with closing(sqlite3.connect(home / "state.db")) as database:
        database.execute(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, user_id TEXT, archived INTEGER, started_at REAL)"
        )
        database.execute(
            "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT)"
        )
        database.execute(
            "INSERT INTO sessions VALUES (?, 'telegram', ?, 0, 1)",
            (session_id, user_id),
        )
        database.execute(
            "INSERT INTO messages(session_id, role, content) VALUES (?, 'user', ?)",
            (session_id, callback),
        )
        if other_callback:
            database.execute("INSERT INTO sessions VALUES ('other-session', 'telegram', '99999', 0, 2)")
            database.execute(
                "INSERT INTO messages(session_id, role, content) VALUES ('other-session', 'user', ?)",
                (other_callback,),
            )
        database.commit()


safety = load_script("zomato_runtime_safety_test", "scripts/zomato_runtime_safety.py")
chat_oauth = load_script("zomato_chat_oauth_test", "scripts/zomato_chat_oauth.py")
logout_helper = load_script("zomato_logout_test", "scripts/zomato_logout.py")


class CallbackHandler(BaseHTTPRequestHandler):
    token_path: Path

    def log_message(self, format: str, *args):
        return

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text("{}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")


class ZomatoChatOAuthTests(unittest.TestCase):
    def test_duplicate_security_env_entries_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".env").write_text(
                "TELEGRAM_BOT_TOKEN=one\n"
                "TELEGRAM_ALLOWED_USERS=123\n"
                "TELEGRAM_ALLOWED_USERS=456\n"
            )
            with self.assertRaisesRegex(ValueError, "duplicate security-sensitive"):
                chat_oauth.configured_telegram_user(home)

    def test_allowlist_requires_exactly_one_numeric_user(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".env").write_text(
                "TELEGRAM_BOT_TOKEN=dummy-token\nTELEGRAM_ALLOWED_USERS=123,456\n"
            )
            with self.assertRaisesRegex(ValueError, "exactly one"):
                chat_oauth.configured_telegram_user(home)

    def test_latest_callback_is_scoped_to_bound_session_and_user(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            expected = "http://127.0.0.1:1002/callback?code=expected&state=expected"
            prepare_telegram_session(
                home,
                expected,
                other_callback="http://127.0.0.1:9999/callback?code=other&state=other",
            )
            state_path = home / "zomato-chat-oauth" / "state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(
                json.dumps(
                    {
                        "telegram_session_id": "telegram-session",
                        "telegram_user_id": "12345",
                    }
                )
            )
            self.assertEqual(chat_oauth.latest_callback_from_session(home), expected)

    def test_relay_latest_completes_without_pty_wait(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            token_path = home / "mcp-tokens" / "zomato.json"
            handler = type("Handler", (CallbackHandler,), {"token_path": token_path})
            server = HTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=server.handle_request, daemon=True).start()
            callback = (
                f"http://127.0.0.1:{server.server_port}/callback"
                "?code=one-time&state=expected-state"
            )
            prepare_telegram_session(home, callback)
            state_path = home / "zomato-chat-oauth" / "state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(
                json.dumps(
                    {
                        "status": "waiting_for_callback",
                        "worker_pid": os.getpid(),
                        "callback_port": server.server_port,
                        "oauth_state": "expected-state",
                        "telegram_session_id": "telegram-session",
                        "telegram_user_id": "12345",
                    }
                )
            )

            started = time.monotonic()
            result = chat_oauth.relay(chat_oauth.latest_callback_from_session(home), home)
            server.server_close()
            self.assertLess(time.monotonic() - started, 3)
            self.assertTrue(result["ok"])
            self.assertTrue(result["token_present"])

    def test_relay_rejects_external_callback(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "127.0.0.1"):
                chat_oauth.relay(
                    "https://evil.example/callback?code=x&state=y",
                    Path(directory),
                )

    def test_relay_rejects_wrong_port_and_state(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state_path = home / "zomato-chat-oauth" / "state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(
                json.dumps(
                    {
                        "status": "waiting_for_callback",
                        "worker_pid": os.getpid(),
                        "callback_port": 1234,
                        "oauth_state": "right-state",
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "port"):
                chat_oauth.relay(
                    "http://127.0.0.1:4321/callback?code=x&state=right-state",
                    home,
                )
            with self.assertRaisesRegex(ValueError, "state"):
                chat_oauth.relay(
                    "http://127.0.0.1:1234/callback?code=x&state=wrong-state",
                    home,
                )


class ZomatoLogoutTests(unittest.TestCase):
    def test_logout_removes_credentials_but_keeps_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            tokens = home / "mcp-tokens"
            tokens.mkdir(parents=True)
            (tokens / "zomato.json").write_text("{}")
            (tokens / "zomato.client.json").write_text("{}")
            (tokens / "zomato.meta.json").write_text("{}")
            pending = home / "zomato-chat-oauth" / "state.json"
            pending.parent.mkdir(parents=True)
            pending.write_text("{}")

            result = logout_helper.logout(home)

            self.assertTrue(result["ok"])
            self.assertTrue(result["token_absent"])
            self.assertTrue(result["client_absent"])
            self.assertTrue(result["oauth_process_stopped"])
            self.assertFalse(pending.exists())
            self.assertTrue((tokens / "zomato.meta.json").exists())

    def test_logout_retains_state_when_process_group_survives(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "zomato-chat-oauth" / "state.json"
            state.parent.mkdir(parents=True)
            state.write_text(json.dumps({"worker_pid": 321}))
            with patch.object(logout_helper, "pid_running", return_value=True), patch.object(
                logout_helper, "terminate_oauth_worker_group", return_value=False
            ):
                result = logout_helper.logout(home)
            self.assertFalse(result["ok"])
            self.assertFalse(result["oauth_process_stopped"])
            self.assertTrue(state.exists())

    def test_worker_teardown_targets_entire_verified_process_group(self):
        with patch.object(safety, "is_oauth_worker", return_value=True), patch.object(
            safety.os, "getpgid", return_value=321
        ), patch.object(safety, "wait_for_group_exit", return_value=True), patch.object(
            safety.os, "killpg"
        ) as killpg:
            self.assertTrue(safety.terminate_oauth_worker_group(321, grace_seconds=0))
            killpg.assert_called_once_with(321, signal.SIGTERM)

    def test_worker_teardown_verifies_group_after_sigkill(self):
        with patch.object(safety, "is_oauth_worker", return_value=True), patch.object(
            safety.os, "getpgid", return_value=321
        ), patch.object(safety, "wait_for_group_exit", side_effect=[False, True]) as wait, patch.object(
            safety.os, "killpg"
        ) as killpg:
            self.assertTrue(safety.terminate_oauth_worker_group(321, grace_seconds=0))
            self.assertEqual(
                killpg.call_args_list,
                [
                    call(321, signal.SIGTERM),
                    call(321, signal.SIGKILL),
                ],
            )
            self.assertEqual(wait.call_count, 2)

    def test_worker_teardown_fails_when_group_survives_sigkill(self):
        with patch.object(safety, "is_oauth_worker", return_value=True), patch.object(
            safety.os, "getpgid", return_value=321
        ), patch.object(safety, "wait_for_group_exit", return_value=False), patch.object(
            safety.os, "killpg"
        ):
            self.assertFalse(safety.terminate_oauth_worker_group(321, grace_seconds=0))

    def test_gateway_restart_is_detached_and_bounded(self):
        with patch.object(logout_helper.shutil, "which", return_value="/mock/hermes"), patch.object(
            logout_helper.subprocess, "Popen"
        ) as popen:
            self.assertTrue(logout_helper.schedule_gateway_restart(2))
            argv = popen.call_args.args[0]
            self.assertEqual(argv[-2:], ["2", "/mock/hermes"])
            self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_gateway_restart_unavailable_returns_false(self):
        with patch.object(logout_helper.shutil, "which", return_value=None):
            self.assertFalse(logout_helper.schedule_gateway_restart())

    def test_logout_cli_fails_when_gateway_restart_cannot_be_scheduled(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            env = dict(os.environ, HERMES_HOME=str(home), PATH=directory)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/zomato_logout.py"),
                    "--json",
                    "--restart-gateway",
                ],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
            )
            payload = json.loads(result.stdout)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(payload["ok"])
            self.assertFalse(payload["gateway_restart_scheduled"])


class ShellSafetyTests(unittest.TestCase):
    def test_smoke_rejects_pong_followed_by_error_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            bin_dir = root / "bin"
            home.mkdir()
            bin_dir.mkdir()
            (home / ".env").write_text("GLM_API_KEY=x\nMINIMAX_API_KEY=y\n")
            fake_hermes = bin_dir / "hermes"
            fake_hermes.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \" $* \" == *\" openai-codex \"* ]]; then printf 'PONG\\nHTTP 429\\n'; else printf 'PONG\\n'; fi\n"
            )
            fake_hermes.chmod(0o755)
            env = dict(os.environ, HERMES_HOME=str(home), PATH=f"{bin_dir}:{os.environ['PATH']}")
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/smoke.sh")],
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("codex=1", result.stdout)

    def test_run_starts_gateway_even_when_smoke_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "bootstrap").mkdir()
            shutil.copy(ROOT / "run.sh", root / "run.sh")
            marker = root / "telegram-started"
            scripts = {
                "setup.sh": "#!/usr/bin/env bash\nexit 0\n",
                "scripts/setup-hermes-mcp.sh": "#!/usr/bin/env bash\nexit 0\n",
                "scripts/smoke.sh": "#!/usr/bin/env bash\nexit 7\n",
                "bootstrap/watch_git.sh": "#!/usr/bin/env bash\nexit 0\n",
                "scripts/telegram.sh": f"#!/usr/bin/env bash\ntouch {marker!s}\nexit 0\n",
            }
            for relative, content in scripts.items():
                path = root / relative
                path.write_text(content)
                path.chmod(0o755)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            fake_hermes = bin_dir / "hermes"
            fake_hermes.write_text("#!/usr/bin/env bash\nexit 0\n")
            fake_hermes.chmod(0o755)
            env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
            result = subprocess.run(
                ["bash", str(root / "run.sh")],
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 7)
            self.assertTrue(marker.exists())
            self.assertIn("Ready", result.stdout)

    def test_telegram_preflight_accepts_one_user_and_false_allow_all(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            bin_dir = root / "bin"
            home.mkdir()
            bin_dir.mkdir()
            (home / ".env").write_text(
                "TELEGRAM_BOT_TOKEN=dummy-token\n"
                "TELEGRAM_ALLOWED_USERS=123\n"
                "TELEGRAM_ALLOW_ALL_USERS=false\n"
            )
            fake_hermes = bin_dir / "hermes"
            fake_hermes.write_text("#!/usr/bin/env bash\nexit 0\n")
            fake_hermes.chmod(0o755)
            env = dict(os.environ, HERMES_HOME=str(home), PATH=f"{bin_dir}:{os.environ['PATH']}")
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/telegram.sh"), "start"],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_telegram_preflight_rejects_multiple_users(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            bin_dir = root / "bin"
            home.mkdir()
            bin_dir.mkdir()
            (home / ".env").write_text(
                "TELEGRAM_BOT_TOKEN=dummy-token\nTELEGRAM_ALLOWED_USERS=123,456\n"
            )
            fake_hermes = bin_dir / "hermes"
            fake_hermes.write_text("#!/usr/bin/env bash\nexit 0\n")
            fake_hermes.chmod(0o755)
            env = dict(os.environ, HERMES_HOME=str(home), PATH=f"{bin_dir}:{os.environ['PATH']}")
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/telegram.sh"), "start"],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exactly one numeric", result.stderr)

    def test_telegram_preflight_rejects_quoted_space_padded_allow_all(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            bin_dir = root / "bin"
            home.mkdir()
            bin_dir.mkdir()
            (home / ".env").write_text(
                'TELEGRAM_BOT_TOKEN=dummy-token\n'
                'TELEGRAM_ALLOWED_USERS=123\n'
                'TELEGRAM_ALLOW_ALL_USERS=" true " # dotenv comment\n'
            )
            fake_hermes = bin_dir / "hermes"
            fake_hermes.write_text("#!/usr/bin/env bash\nexit 0\n")
            fake_hermes.chmod(0o755)
            env = dict(os.environ, HERMES_HOME=str(home), PATH=f"{bin_dir}:{os.environ['PATH']}")
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/telegram.sh"), "start"],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ALLOW_ALL_USERS is enabled", result.stderr)

    def test_telegram_preflight_ignores_divergent_repo_env(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            bin_dir = root / "bin"
            scripts_dir = root / "scripts"
            home.mkdir()
            bin_dir.mkdir()
            scripts_dir.mkdir()
            shutil.copy(ROOT / "scripts/telegram.sh", scripts_dir / "telegram.sh")
            shutil.copy(ROOT / "scripts/zomato_runtime_safety.py", scripts_dir / "zomato_runtime_safety.py")
            (root / ".env").write_text(
                "TELEGRAM_BOT_TOKEN=wrong\n"
                "TELEGRAM_ALLOWED_USERS=1,2\n"
                "TELEGRAM_ALLOW_ALL_USERS=true\n"
            )
            (home / ".env").write_text(
                "TELEGRAM_BOT_TOKEN=canonical\n"
                "TELEGRAM_ALLOWED_USERS=123\n"
                "TELEGRAM_ALLOW_ALL_USERS=false\n"
            )
            fake_hermes = bin_dir / "hermes"
            fake_hermes.write_text("#!/usr/bin/env bash\nexit 0\n")
            fake_hermes.chmod(0o755)
            env = dict(os.environ, HERMES_HOME=str(home), PATH=f"{bin_dir}:{os.environ['PATH']}")
            result = subprocess.run(
                ["bash", str(scripts_dir / "telegram.sh"), "start"],
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

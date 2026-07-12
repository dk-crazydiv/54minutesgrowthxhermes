"""Unit tests for per-Telegram-user Zomato MCP isolation.

These cover the three vendored-Hermes fork seams that make two Telegram users
transact on their OWN Zomato accounts concurrently (see
docs/hermes/per-user-isolation.md):

  Seam 1  HermesTokenStorage scoped vs unscoped token path
  Seam 2  scope-keyed MCP client registry (distinct sessions per scope)
  Seam 3  scope threading -- credential scope resolution from the gateway
          session user id / the explicit override contextvar

They import the *vendored* Hermes tree directly (``vendor/hermes-agent``) and
NEVER touch a running gateway, real network, or ``~/.hermes``. All token
directories are temporary. Run with ``python3 -m unittest``.
"""

import asyncio
import importlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "hermes-agent"
# Prepend the vendored Hermes tree so ``tools.*`` and ``hermes_constants`` and
# ``gateway.*`` resolve to the in-repo (patched) copies.
sys.path.insert(0, str(VENDOR))


def _load_session_context():
    """Load ``gateway.session_context`` by file path.

    ``gateway/__init__.py`` eagerly imports the full gateway stack (pyyaml,
    etc.) which may be absent in a bare test env. ``session_context`` itself
    only needs ``contextvars``, so we load the module file directly and
    register it under its real dotted name so ``mcp_tool`` finds the SAME
    module object (a second copy would have independent ContextVars and the
    scope wouldn't be visible across the boundary).
    """
    name = "gateway.session_context"
    if name in sys.modules:
        return sys.modules[name]
    # Ensure a minimal ``gateway`` package placeholder exists so the submodule
    # can be attached without running the heavy package __init__.
    if "gateway" not in sys.modules:
        import types

        pkg = types.ModuleType("gateway")
        pkg.__path__ = [str(VENDOR / "gateway")]
        sys.modules["gateway"] = pkg
    path = VENDOR / "gateway" / "session_context.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _reload_token_dir_bound(home: Path):
    """Return a HermesTokenStorage class bound to ``home`` as HERMES_HOME.

    ``_get_token_dir`` reads HERMES_HOME lazily on each call, so simply setting
    the env var before constructing the storage is sufficient -- no reload
    needed. Returns the class for convenience.
    """
    os.environ["HERMES_HOME"] = str(home)
    from tools.mcp_oauth import HermesTokenStorage

    return HermesTokenStorage


class TokenPathScopingTests(unittest.TestCase):
    """Seam 1: scoped vs unscoped on-disk token layout."""

    def test_unscoped_path_is_unchanged_flat_layout(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            Storage = _reload_token_dir_bound(home)
            s = Storage("zomato")
            self.assertEqual(
                s._tokens_path(), home / "mcp-tokens" / "zomato.json"
            )
            self.assertEqual(
                s._client_info_path(),
                home / "mcp-tokens" / "zomato.client.json",
            )
            self.assertEqual(
                s._meta_path(), home / "mcp-tokens" / "zomato.meta.json"
            )

    def test_none_scope_is_identical_to_no_scope(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            Storage = _reload_token_dir_bound(home)
            self.assertEqual(
                Storage("zomato")._tokens_path(),
                Storage("zomato", scope=None)._tokens_path(),
            )

    def test_scoped_path_is_per_scope_subdirectory(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            Storage = _reload_token_dir_bound(home)
            s = Storage("zomato", scope="111")
            self.assertEqual(
                s._tokens_path(), home / "mcp-tokens" / "zomato" / "111.json"
            )
            self.assertEqual(
                s._client_info_path(),
                home / "mcp-tokens" / "zomato" / "111.client.json",
            )
            self.assertEqual(
                s._meta_path(),
                home / "mcp-tokens" / "zomato" / "111.meta.json",
            )

    def test_two_scopes_resolve_to_two_distinct_token_paths(self):
        """The critical proof: user 111 and user 222 never share a token file."""
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            Storage = _reload_token_dir_bound(home)
            p_none = Storage("zomato")._tokens_path()
            p111 = Storage("zomato", scope="111")._tokens_path()
            p222 = Storage("zomato", scope="222")._tokens_path()
            self.assertEqual(len({p_none, p111, p222}), 3)
            # And a scoped path never collides with the flat global path.
            self.assertNotEqual(p111.parent, p_none.parent)

    def test_scope_is_sanitized_no_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            Storage = _reload_token_dir_bound(home)
            s = Storage("zomato", scope="../../etc/passwd")
            # Sanitized: no separators escape the mcp-tokens/zomato subdir.
            token_dir = (home / "mcp-tokens" / "zomato").resolve()
            self.assertTrue(
                str(s._tokens_path().resolve()).startswith(str(token_dir))
            )

    def test_scoped_roundtrip_writes_and_reads_only_its_own_file(self):
        """Persisting user 111's tokens must not appear under user 222."""
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            Storage = _reload_token_dir_bound(home)

            class _Tok:
                # Minimal object with model_dump so set_tokens can persist it
                # without importing the MCP SDK's OAuthToken.
                def model_dump(self, *a, **k):
                    return {"access_token": "tok-111", "token_type": "bearer"}

            s111 = Storage("zomato", scope="111")
            asyncio.run(s111.set_tokens(_Tok()))

            self.assertTrue(
                (home / "mcp-tokens" / "zomato" / "111.json").exists()
            )
            # User 222's file must not exist.
            self.assertFalse(
                (home / "mcp-tokens" / "zomato" / "222.json").exists()
            )
            # The flat global file must not exist either.
            self.assertFalse((home / "mcp-tokens" / "zomato.json").exists())


class OAuthManagerCacheKeyTests(unittest.TestCase):
    """Seam 2 (provider layer): scope-keyed OAuth provider cache."""

    def test_cache_key_unscoped_is_bare_server_name(self):
        from tools.mcp_oauth_manager import MCPOAuthManager

        self.assertEqual(MCPOAuthManager._cache_key("zomato", None), "zomato")
        self.assertEqual(MCPOAuthManager._cache_key("zomato", ""), "zomato")

    def test_cache_key_scoped_is_distinct_per_scope(self):
        from tools.mcp_oauth_manager import MCPOAuthManager

        k1 = MCPOAuthManager._cache_key("zomato", "111")
        k2 = MCPOAuthManager._cache_key("zomato", "222")
        self.assertNotEqual(k1, k2)
        self.assertNotEqual(k1, MCPOAuthManager._cache_key("zomato", None))


class RegistryKeyTests(unittest.TestCase):
    """Seam 2 (session registry): scope-keyed ``_servers`` registry key."""

    def _mcp_tool(self):
        return importlib.import_module("tools.mcp_tool")

    def test_unscoped_registry_key_is_bare_name(self):
        m = self._mcp_tool()
        self.assertEqual(m._server_registry_key("zomato", None), "zomato")
        self.assertEqual(m._server_registry_key("zomato", ""), "zomato")

    def test_scoped_zomato_key_is_distinct_per_scope(self):
        m = self._mcp_tool()
        k1 = m._server_registry_key("zomato", "111")
        k2 = m._server_registry_key("zomato", "222")
        self.assertNotEqual(k1, k2)
        self.assertNotEqual(k1, m._server_registry_key("zomato", None))
        # NUL sentinel separates name from scope.
        self.assertIn("\x00", k1)

    def test_non_scoped_server_ignores_scope(self):
        """Only ``zomato`` participates; every other server stays global."""
        m = self._mcp_tool()
        self.assertEqual(m._server_registry_key("github", "111"), "github")
        self.assertEqual(m._server_registry_key("github", "222"), "github")
        self.assertEqual(m._server_registry_key("filesystem", "111"), "filesystem")

    def test_scoped_servers_set_contains_only_zomato(self):
        m = self._mcp_tool()
        self.assertIn("zomato", m._SCOPED_MCP_SERVERS)
        # Guardrail: keep the blast radius to Zomato until explicitly widened.
        self.assertEqual(set(m._SCOPED_MCP_SERVERS), {"zomato"})

    def test_mcp_server_task_can_store_oauth_scope(self):
        """A scoped task must construct cleanly before login can start."""
        m = self._mcp_tool()
        task = m.MCPServerTask("zomato")
        task._oauth_scope = "111"
        self.assertEqual(task._oauth_scope, "111")


class ScopeThreadingTests(unittest.TestCase):
    """Seam 3: credential-scope resolution at tool-call time."""

    def setUp(self):
        # Ensure no ambient scope/session leaks between tests.
        import hermes_constants

        self._hc = hermes_constants
        try:
            self._sc = _load_session_context()
        except Exception:
            self._sc = None

    def _clear(self):
        # Clear any explicit override and gateway session user id.
        tok = self._hc.set_credential_scope(None)
        self._hc.reset_credential_scope(tok)
        if self._sc is not None:
            self._sc.reset_session_vars()

    def test_no_scope_active_resolves_to_none(self):
        m = importlib.import_module("tools.mcp_tool")
        self._clear()
        self.assertIsNone(m._active_scope_for("zomato"))

    def test_explicit_override_wins(self):
        m = importlib.import_module("tools.mcp_tool")
        self._clear()
        token = self._hc.set_credential_scope("override-777")
        try:
            self.assertEqual(m._active_scope_for("zomato"), "override-777")
        finally:
            self._hc.reset_credential_scope(token)

    def test_gateway_session_user_id_is_used_as_scope(self):
        if self._sc is None:
            self.skipTest("gateway.session_context unavailable")
        m = importlib.import_module("tools.mcp_tool")
        self._clear()
        tokens = self._sc.set_session_vars(
            platform="telegram", user_id="555", chat_id="c1"
        )
        try:
            self.assertEqual(m._active_scope_for("zomato"), "555")
        finally:
            self._sc.clear_session_vars(tokens)

    def test_two_users_resolve_to_two_distinct_scopes_and_keys(self):
        """End-to-end proof for seam 2+3: distinct users → distinct registry keys."""
        if self._sc is None:
            self.skipTest("gateway.session_context unavailable")
        m = importlib.import_module("tools.mcp_tool")

        def scope_and_key(uid):
            self._clear()
            tokens = self._sc.set_session_vars(
                platform="telegram", user_id=uid, chat_id="c"
            )
            try:
                scope = m._active_scope_for("zomato")
                return scope, m._server_registry_key("zomato", scope)
            finally:
                self._sc.clear_session_vars(tokens)

        s_a, k_a = scope_and_key("111")
        s_b, k_b = scope_and_key("222")
        self.assertEqual((s_a, s_b), ("111", "222"))
        self.assertNotEqual(k_a, k_b)

    def test_non_scoped_server_never_gets_a_scope(self):
        if self._sc is None:
            self.skipTest("gateway.session_context unavailable")
        m = importlib.import_module("tools.mcp_tool")
        self._clear()
        tokens = self._sc.set_session_vars(
            platform="telegram", user_id="555", chat_id="c1"
        )
        try:
            self.assertIsNone(m._active_scope_for("github"))
        finally:
            self._sc.clear_session_vars(tokens)


def _load_onboarding_script(home: Path, repo_users: Path):
    """Load scripts/zomato_user_auth.py bound to temp HERMES_HOME + users dir.

    The module computes its token/users directories at import time, so we set
    HERMES_HOME first, then override the derived module-level paths to point at
    the temp dirs. Returns the loaded module.
    """
    os.environ["HERMES_HOME"] = str(home)
    path = ROOT / "scripts" / "zomato_user_auth.py"
    spec = importlib.util.spec_from_file_location("zomato_user_auth_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Re-point derived paths at the temp sandbox.
    module.HERMES = str(home)
    module.TOKDIR = str(home / "mcp-tokens")
    module.SCOPED_TOKDIR = str(home / "mcp-tokens" / module.SERVER)
    module.USERS = str(repo_users)
    return module


class OnboardingScriptTokenLayoutTests(unittest.TestCase):
    """Seam 4: onboarding writes tokens to the scoped MCP path per user."""

    def _drive_start_finish(self, mod, tid):
        """Run start then finish for ``tid`` with all network calls mocked."""
        fake_client = {"client_id": "client-" + tid}
        fake_tokens = {
            "access_token": "secret-do-not-store-plaintext-" + tid,
            "refresh_token": "refresh-" + tid,
            "token_type": "bearer",
            "expires_in": 3600,
        }

        captured = {}

        def fake_post_json(url, payload, form=False):
            if url == mod.REGISTER:
                return fake_client
            if url == mod.TOKEN:
                captured["token_form"] = payload
                return dict(fake_tokens)
            raise AssertionError("unexpected POST to " + url)

        # start: capture the authorize URL to extract the state param.
        printed = []
        with unittest.mock.patch.object(mod, "post_json", fake_post_json), \
                unittest.mock.patch("builtins.print", lambda *a, **k: printed.append(" ".join(map(str, a)))):
            mod.cmd_start(tid)
        authorize_line = next(p for p in printed if p.startswith("AUTHORIZE_URL:"))
        from urllib.parse import parse_qs, urlsplit

        url = authorize_line.split("AUTHORIZE_URL: ", 1)[1]
        state = parse_qs(urlsplit(url).query)["state"][0]

        redirect = "%s?code=authcode-%s&state=%s" % (mod.REDIRECT_URI, tid, state)
        printed.clear()
        with unittest.mock.patch.object(mod, "post_json", fake_post_json), \
                unittest.mock.patch("builtins.print", lambda *a, **k: printed.append(" ".join(map(str, a)))):
            mod.cmd_finish(tid, redirect)
        return captured, printed

    def test_finish_writes_tokens_to_scoped_path(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            users = Path(d) / "users"
            mod = _load_onboarding_script(home, users)
            self._drive_start_finish(mod, "111")

            tok = home / "mcp-tokens" / "zomato" / "111.json"
            client = home / "mcp-tokens" / "zomato" / "111.client.json"
            self.assertTrue(tok.exists(), "scoped token file must exist")
            self.assertTrue(client.exists(), "scoped client file must exist")
            # The flat global path must NOT be written (no active-user swap).
            self.assertFalse((home / "mcp-tokens" / "zomato.json").exists())

    def test_two_users_write_two_distinct_scoped_files(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            users = Path(d) / "users"
            mod = _load_onboarding_script(home, users)
            self._drive_start_finish(mod, "111")
            self._drive_start_finish(mod, "222")

            t1 = home / "mcp-tokens" / "zomato" / "111.json"
            t2 = home / "mcp-tokens" / "zomato" / "222.json"
            self.assertTrue(t1.exists() and t2.exists())
            # Each holds that user's own access token -- never shared/swapped.
            self.assertIn("111", json.loads(t1.read_text())["access_token"])
            self.assertIn("222", json.loads(t2.read_text())["access_token"])

    def test_onboarding_path_matches_hermes_token_storage_path(self):
        """The onboarding write path must equal HermesTokenStorage's read path."""
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            users = Path(d) / "users"
            mod = _load_onboarding_script(home, users)
            self._drive_start_finish(mod, "111")

            os.environ["HERMES_HOME"] = str(home)
            from tools.mcp_oauth import HermesTokenStorage

            storage_path = HermesTokenStorage("zomato", scope="111")._tokens_path()
            onboarding_path = Path(mod.scoped_token_path("111", ".json"))
            self.assertEqual(storage_path.resolve(), onboarding_path.resolve())
            self.assertTrue(storage_path.exists())

    def test_token_files_are_chmod_600(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            users = Path(d) / "users"
            mod = _load_onboarding_script(home, users)
            self._drive_start_finish(mod, "111")
            tok = home / "mcp-tokens" / "zomato" / "111.json"
            mode = tok.stat().st_mode & 0o777
            self.assertEqual(mode, 0o600)

    def test_pending_state_cleared_after_finish(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            users = Path(d) / "users"
            mod = _load_onboarding_script(home, users)
            self._drive_start_finish(mod, "111")
            self.assertFalse((users / "111" / ".oauth-pending.json").exists())
            # Preferences skeleton created.
            self.assertTrue((users / "111" / "preferences.md").exists())

    def test_finish_never_prints_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            users = Path(d) / "users"
            mod = _load_onboarding_script(home, users)
            _captured, printed = self._drive_start_finish(mod, "111")
            joined = "\n".join(printed)
            self.assertNotIn("secret-do-not-store-plaintext", joined)
            self.assertNotIn("refresh-111", joined)


def _seed_telegram_sessions(home: Path, rows):
    """Create a minimal ~/.hermes/state.db with the given session rows.

    ``rows`` is a list of ``(session_id, user_id, archived, started_at)``.
    """
    import sqlite3
    from contextlib import closing

    with closing(sqlite3.connect(home / "state.db")) as conn:
        conn.execute(
            "CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT, "
            "user_id TEXT, archived INTEGER, started_at REAL)"
        )
        for sid, uid, archived, started in rows:
            conn.execute(
                "INSERT INTO sessions VALUES (?, 'telegram', ?, ?, ?)",
                (sid, uid, archived, started),
            )
        conn.commit()


class OptionalIdResolutionTests(unittest.TestCase):
    """Seam 4 (id resolution): an omitted telegram id resolves to the current
    user via HERMES_SESSION_USER_ID, then falls back to the most-recent
    Telegram session user_id in state.db."""

    def setUp(self):
        # Ensure a clean env: no ambient session id leaking in from the host.
        self._saved_env = os.environ.get("HERMES_SESSION_USER_ID")
        os.environ.pop("HERMES_SESSION_USER_ID", None)

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop("HERMES_SESSION_USER_ID", None)
        else:
            os.environ["HERMES_SESSION_USER_ID"] = self._saved_env

    def test_explicit_arg_wins_over_env_and_db(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            home.mkdir()
            mod = _load_onboarding_script(home, Path(d) / "users")
            _seed_telegram_sessions(home, [("s1", "888", 0, 2.0)])
            os.environ["HERMES_SESSION_USER_ID"] = "555"
            self.assertEqual(mod.resolve_telegram_id("111"), "111")

    def test_env_session_user_id_used_when_no_arg(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            home.mkdir()
            mod = _load_onboarding_script(home, Path(d) / "users")
            _seed_telegram_sessions(home, [("s1", "888", 0, 2.0)])
            os.environ["HERMES_SESSION_USER_ID"] = "555"
            # Env beats the db fallback.
            self.assertEqual(mod.resolve_telegram_id(), "555")
            self.assertEqual(mod.resolve_telegram_id(None), "555")

    def test_db_fallback_picks_most_recent_non_archived_session(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            home.mkdir()
            mod = _load_onboarding_script(home, Path(d) / "users")
            os.environ.pop("HERMES_SESSION_USER_ID", None)
            _seed_telegram_sessions(
                home,
                [
                    ("s1", "777", 0, 1.0),  # older
                    ("s2", "888", 0, 2.0),  # newest non-archived -> expected
                    ("s3", "999", 1, 3.0),  # newer but archived -> ignored
                ],
            )
            self.assertEqual(mod.resolve_telegram_id(), "888")

    def test_no_id_no_env_no_db_dies(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            home.mkdir()  # no state.db
            mod = _load_onboarding_script(home, Path(d) / "users")
            os.environ.pop("HERMES_SESSION_USER_ID", None)
            with unittest.mock.patch("builtins.print", lambda *a, **k: None):
                with self.assertRaises(SystemExit):
                    mod.resolve_telegram_id()

    def test_non_numeric_resolved_id_dies(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            home.mkdir()
            mod = _load_onboarding_script(home, Path(d) / "users")
            os.environ["HERMES_SESSION_USER_ID"] = "not-a-number"
            with unittest.mock.patch("builtins.print", lambda *a, **k: None):
                with self.assertRaises(SystemExit):
                    mod.resolve_telegram_id()

    def test_env_resolution_writes_tokens_to_that_users_scoped_path(self):
        """End-to-end: no id passed + env set -> tokens land at env user's scoped path."""
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            home.mkdir()
            users = Path(d) / "users"
            mod = _load_onboarding_script(home, users)
            os.environ["HERMES_SESSION_USER_ID"] = "424242"

            fake_client = {"client_id": "client-x"}
            fake_tokens = {"access_token": "tok", "token_type": "bearer",
                           "expires_in": 3600}

            def fake_post_json(url, payload, form=False):
                return fake_client if url == mod.REGISTER else dict(fake_tokens)

            printed = []

            def cap_print(*a, **k):
                printed.append(" ".join(map(str, a)))

            with unittest.mock.patch.object(mod, "post_json", fake_post_json), \
                    unittest.mock.patch("builtins.print", cap_print):
                mod.cmd_start()  # no id -> resolves to 424242
            state = json.loads(
                (users / "424242" / ".oauth-pending.json").read_text()
            )["state"]
            redirect = "%s?code=c&state=%s" % (mod.REDIRECT_URI, state)
            with unittest.mock.patch.object(mod, "post_json", fake_post_json), \
                    unittest.mock.patch("builtins.print", cap_print):
                mod.cmd_finish(redirect)  # no id, url-only form

            self.assertTrue(
                (home / "mcp-tokens" / "zomato" / "424242.json").exists()
            )

    def test_logout_removes_only_the_requesting_users_scoped_tokens(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            home.mkdir()
            users = Path(d) / "users"
            mod = _load_onboarding_script(home, users)
            zdir = home / "mcp-tokens" / "zomato"
            zdir.mkdir(parents=True)
            # Two users onboarded; logging out user 111 must not touch 222.
            (zdir / "111.json").write_text("{}")
            (zdir / "111.client.json").write_text("{}")
            (zdir / "111.meta.json").write_text("{}")  # metadata kept
            (zdir / "222.json").write_text("{}")
            os.environ["HERMES_SESSION_USER_ID"] = "111"
            with unittest.mock.patch("builtins.print", lambda *a, **k: None):
                mod.cmd_logout()
            self.assertFalse((zdir / "111.json").exists())
            self.assertFalse((zdir / "111.client.json").exists())
            self.assertTrue((zdir / "111.meta.json").exists(), "metadata kept")
            self.assertTrue((zdir / "222.json").exists(), "other user untouched")
            # The flat global token path must never be created/removed here.
            self.assertFalse((home / "mcp-tokens" / "zomato.json").exists())

    def test_finish_url_only_form_resolves_id(self):
        """`finish <redirect_url>` (no id) resolves the user and completes."""
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "hermes"
            home.mkdir()
            users = Path(d) / "users"
            mod = _load_onboarding_script(home, users)
            os.environ["HERMES_SESSION_USER_ID"] = "313131"

            fake_client = {"client_id": "client-x"}

            def fake_post_json(url, payload, form=False):
                return fake_client if url == mod.REGISTER else {
                    "access_token": "tok", "token_type": "bearer",
                    "expires_in": 3600,
                }

            with unittest.mock.patch.object(mod, "post_json", fake_post_json), \
                    unittest.mock.patch("builtins.print", lambda *a, **k: None):
                mod.cmd_start()
            state = json.loads(
                (users / "313131" / ".oauth-pending.json").read_text()
            )["state"]
            redirect = "%s?code=c&state=%s" % (mod.REDIRECT_URI, state)
            with unittest.mock.patch.object(mod, "post_json", fake_post_json), \
                    unittest.mock.patch("builtins.print", lambda *a, **k: None):
                # Single positional that is the URL -> id resolved from env.
                mod.cmd_finish(redirect)
            self.assertTrue(
                (home / "mcp-tokens" / "zomato" / "313131.json").exists()
            )


if __name__ == "__main__":
    unittest.main()

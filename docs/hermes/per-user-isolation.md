# Per-Telegram-user Zomato MCP isolation

## Goal

Two different Telegram users messaging `@Orderingbuddy_bot` at the same time must
each transact on **their own** Zomato account. Independent live Zomato MCP
sessions coexist in one gateway process — **no global token swap, no single
"active" user.**

Before this work Hermes used one shared Zomato MCP client for the whole process:
the OAuth token lived at `~/.hermes/mcp-tokens/zomato.json`, keyed only by server
name, and whichever user authenticated last owned the process.

After this work the Zomato server (only) is keyed by `(server, scope)` where
`scope` is the requesting Telegram user id. Each user gets:

- their own OAuth token store at `mcp-tokens/zomato/<telegram-id>.json`
  (+ `.client.json`, `.meta.json`), and
- their own live `MCPServerTask` session, lazily connected on first use and
  cached for reuse.

Every **other** MCP server keeps its exact previous global behavior.

## The three seams (file:line)

All edits are in the **gitignored** `vendor/hermes-agent` tree (the live gateway
runs from there). They are captured as a patch — see *Re-applying the patch*.

### Seam 1 — scoped token path
`vendor/hermes-agent/tools/mcp_oauth.py` — `HermesTokenStorage`

- `__init__(self, server_name, scope=None)` (~L299): added optional `scope`.
- `_base_dir()` / `_stem()` helpers + `_tokens_path()` / `_client_info_path()` /
  `_meta_path()` (~L302–L342): when `scope` is set, the layout becomes
  `mcp-tokens/<server>/<scope>.json`; when `scope is None` it is **byte-for-byte
  the historical flat** `mcp-tokens/<server>.json`.
- `restore()` (~L459): writes snapshots back into `_base_dir()` (scoped subdir)
  instead of the flat token dir.

`_write_json` already does `path.parent.mkdir(parents=True, exist_ok=True)`, so
the per-server subdirectory is created automatically with 0o600 files / 0o700
parent.

### Seam 2 — scope-keyed client registry
`vendor/hermes-agent/tools/mcp_tool.py` and `tools/mcp_oauth_manager.py`

- `_servers: Dict[str, MCPServerTask]` (~L2967) is now keyed by a **registry
  key**: a bare server name for the global session, or a composite
  `"<server>\x00<scope>"` for a per-user session.
- `_SCOPED_MCP_SERVERS = frozenset({"zomato"})` and `_server_registry_key()`
  (~L2976): only `zomato` participates; every other server returns its bare
  name so its key/behavior is unchanged.
- `_lazy_connect_scoped_session()` (~L3951): first time a scoped session is
  needed, it clones the **global** zomato server's connection config
  (transport/url/oauth), overrides only the OAuth scope, connects a fresh
  `MCPServerTask`, and caches it under the composite key (double-checked to be
  race-safe).
- `_get_connected_server_for_call()` (~L4010): resolves the active scope,
  computes the registry key, lazy-connects the per-user session if absent, and
  returns it. The circuit breaker + `_check` fn stay keyed by the logical
  server name (the global session gates tool *availability*; per-user sessions
  are created on demand).
- `MCPServerTask.__init__` gains `self._oauth_scope` (~L1550); `_connect_server`
  accepts `oauth_scope` and sets it (~L3890); the OAuth-provider build passes
  `oauth_scope=getattr(self, "_oauth_scope", None)` (~L2368).
- `MCPOAuthManager` (`tools/mcp_oauth_manager.py`): `_cache_key(server, scope)`
  keys the provider cache by `(server, scope)`; `get_or_build_provider(...,
  oauth_scope=None)` and `_build_provider(..., oauth_scope=None)` thread the
  scope into `HermesTokenStorage(server_name, scope=oauth_scope)`. `None`
  preserves the historical single-provider path exactly.

### Seam 3 — scope threading (Telegram user id → tool call)
`vendor/hermes-agent/hermes_constants.py` and `tools/mcp_tool.py`

The inbound Telegram user id is already available at MCP-tool-call time via the
gateway's per-message session context var **`HERMES_SESSION_USER_ID`**
(`gateway/session_context.py`, bound per message by `set_session_vars(user_id=…)`
and propagated onto agent/executor threads). The MCP tool handler `_handler`
runs on the agent thread where this is set.

- `_active_scope_for(server_name)` (`mcp_tool.py` ~L2976) resolves the scope for
  a scoped server, first-non-empty-wins:
  1. an explicit override via `hermes_constants.get_credential_scope()` (used by
     tests / any caller wanting to force a scope), then
  2. `get_session_env("HERMES_SESSION_USER_ID")` — the requesting Telegram user.
  Returns `None` for non-scoped servers (fully unaffected) and when nothing is
  resolvable (falls back to the global shared session — historical behavior).
- `hermes_constants.py` adds a `_CREDENTIAL_SCOPE` ContextVar with
  `set_credential_scope` / `reset_credential_scope` / `get_credential_scope`,
  mirroring the existing `HERMES_HOME` override channel.
- `_wrap_with_home_override` (`mcp_tool.py` ~L3660) now also carries the
  credential scope onto the MCP background loop task (belt-and-suspenders; scope
  *selection* happens on the agent thread before scheduling, so this is only
  needed by any future contextvar-reading code on the loop).

**No new gateway hook was required** — the existing session context var already
carries the user id to the agent thread. That is the key finding that made
seam 3 a read rather than a plumbing change.

## App-side onboarding (seam 4)

`scripts/zomato_user_auth.py` — revived from reverted commit `804a1f9` and
adapted to write straight to the **scoped** path from seam 1, so a user's
onboarding writes exactly where the scoped MCP client reads:

The `telegram_id` is **optional** for `start` / `status` / `finish` / `logout`:
when omitted the script resolves the current user via `resolve_telegram_id()` —
`HERMES_SESSION_USER_ID` (the gateway binds this per inbound message and the
terminal tool runs inside that user's session), else the most-recent
non-archived Telegram session `user_id` in `~/.hermes/state.db` (same source as
`zomato_chat_oauth.py`'s `latest_telegram_session`). This lets the bot run the
script from chat with **no id** and still scope to whoever sent the current
message.

- `start [telegram_id]` — dynamically register a PKCE client (stored at
  `mcp-tokens/zomato/<id>.client.json`) and print `AUTHORIZE_URL: <url>`.
- `finish [telegram_id] <redirect_url>` — exchange the code and write tokens to
  `mcp-tokens/zomato/<id>.json` (with an absolute `expires_at`, matching
  `HermesTokenStorage.set_tokens`). The id-less `finish <redirect_url>` form is
  disambiguated by the URL-shaped positional. **No active-user swap** — the
  running gateway opens this user's isolated session on their next Zomato
  request (no restart, no /reload).
- `status [telegram_id]` — prints `token_present: true|false` (the flag the
  persona keys on) plus AUTHED / PENDING / NOT_AUTHED.
- `logout [telegram_id]` — removes ONLY this user's own scoped `.json` +
  `.client.json` (keeps `.meta.json`); never touches another user or the flat
  global token, and never restarts the gateway.
- `whoami <display_name>` — map a Telegram DM display name → numeric id.

Stdlib only, PKCE, files chmod 600. Never prints token values.

## Persona (seam 5)

`config/SOUL.md` — the Account boundary / First contact / Login / Logout command
blocks now call `python3 scripts/zomato_user_auth.py {status|start|finish|logout}`
(with no id — current-user resolution), replacing the old single-account
`zomato_chat_oauth.py` / `zomato_logout.py` (global-swap + gateway-restart) flow.
The sections state that **every Telegram user transacts on their own Zomato
account** (no shared/active account); connection state is checked per requesting
user; one user's data is never revealed to another; and a new user must complete
their own login first. The **Login** block is wired end-to-end: `start` prints
`AUTHORIZE_URL:` and the bot MUST send that clickable link plus the 4 numbered
paste-the-callback steps in the same reply (it must never say "finish the login"
without the link); when the user pastes the callback, `finish '<url>'` completes
the exchange and writes the scoped tokens. A **First contact — auto-prompt
login** section makes the bot proactively run that Login flow when a user's first
message arrives and `token_present: false` for them — while a user who already
has a valid token proceeds normally with no prompt.

## Re-applying the patch

The vendored tree is gitignored and rebuilt by `setup.sh` (fresh clone at a
pinned tag). The edits are captured at `patches/hermes-per-user-mcp.patch` in
standard `git diff` form (relative to the vendored repo root). After a
re-vendor, re-apply with:

```bash
cd vendor/hermes-agent
git apply ../../patches/hermes-per-user-mcp.patch
# verify it took:
git apply --reverse --check ../../patches/hermes-per-user-mcp.patch && echo "applied"
```

The patch touches four files: `hermes_constants.py`, `tools/mcp_oauth.py`,
`tools/mcp_oauth_manager.py`, `tools/mcp_tool.py`. The edits are also currently
left applied in-place.

> Restarting the gateway (or the config watcher reloading) is what makes the
> in-place edits take effect — the live process does not hot-reload `.py`.

## Validating two concurrent users (manual — requires a gateway restart)

This must be run by a human; it needs a real gateway restart and real Zomato
OAuth, which this change does **not** perform.

1. **Onboard two users to distinct scoped tokens** (no gateway needed). Pass the
   ids explicitly out-of-band, or run each from that user's own chat session
   (where the id resolves automatically from `HERMES_SESSION_USER_ID`):
   ```bash
   python3 scripts/zomato_user_auth.py start  <USER_A_ID>
   # open the printed AUTHORIZE_URL as user A, finish login, copy the callback URL
   python3 scripts/zomato_user_auth.py finish <USER_A_ID> '<callback-url-A>'
   python3 scripts/zomato_user_auth.py start  <USER_B_ID>
   python3 scripts/zomato_user_auth.py finish <USER_B_ID> '<callback-url-B>'
   ```
   From chat the bot runs these with **no id** (e.g. `... start`,
   `... finish '<url>'`) and each scopes to the sending user automatically.
   Confirm the on-disk layout:
   ```bash
   ls ~/.hermes/mcp-tokens/zomato/
   # expect: <USER_A_ID>.json  <USER_A_ID>.client.json  <USER_B_ID>.json  ...
   test -f ~/.hermes/mcp-tokens/zomato.json && echo "UNEXPECTED flat token" || echo "no flat token (good)"
   ```

2. **Restart the gateway** so the patched vendor code loads (operator action —
   not performed here).

3. **Concurrent transaction test:** from user A and user B, at the same time,
   ask each for something private (e.g. "what are my saved addresses?" /
   "my recent orders"). Verify A only ever sees A's addresses/orders and B only
   B's — never crossed.

4. **Session isolation check** (server-side): while both users are mid-session,
   confirm two live registry entries exist — one keyed `zomato`-plus-A, one
   `zomato`-plus-B — e.g. via the debug dashboard (`scripts/debug-dashboard.py`)
   or by logging `tools.mcp_tool._servers.keys()`. Expect a composite key per
   active user.

5. **Regression check:** confirm every *other* MCP server still works and still
   reads its single global token (its key is the bare server name; no
   subdirectory is created under `mcp-tokens/` for it).

## Automated tests (no gateway)

`tests/test_hermes_per_user_mcp.py` (run: `python3 -m unittest`):

- **Seam 1**: scoped vs unscoped/`None` token path; two scopes → two distinct
  token paths (the critical proof); path-traversal sanitization; scoped
  round-trip write isolation; 0o600.
- **Seam 2**: `MCPOAuthManager._cache_key` and `_server_registry_key` produce
  distinct keys per scope for zomato and ignore scope for other servers;
  `_SCOPED_MCP_SERVERS == {"zomato"}` guardrail.
- **Seam 3**: `_active_scope_for` resolves the explicit override first, then the
  gateway `HERMES_SESSION_USER_ID`; two users → two distinct scopes → two
  distinct registry keys; non-scoped servers never receive a scope.
- **Seam 4**: onboarding writes to the scoped path; the write path equals
  `HermesTokenStorage(server, scope)._tokens_path()`; two users → two distinct
  files each holding their own token; pending state cleared; secrets never
  printed.

## Known limitations (honest scope)

- **Per-scope 401 / session-expired recovery** in `mcp_tool.py`
  (`_handle_auth_failure` ~L3306 and the session-expired retry ~L3437) still
  looks up the **global** server record by bare name. Normal token refresh is
  handled by each scoped provider via the MCP SDK, so this only matters for the
  hard-401 forced-reconnect path on a scoped session; it degrades to a retry
  rather than a crash. Widening those two lookups to be scope-aware is a
  follow-up.
- Everything except the token-path / registry-key / scope-resolution logic was
  verified by unit tests and byte-compilation only. The end-to-end concurrent
  behavior (two live sessions in one process) cannot be verified without a
  gateway restart, which was intentionally not performed here.

#!/usr/bin/env python3
"""Per-Telegram-user Zomato MCP OAuth (PKCE) onboarding for the Hermes bot.

Each Telegram user authenticates their OWN Zomato account. Tokens are written
directly to the SCOPED MCP token path that the patched Hermes zomato MCP client
reads per user (see docs/hermes/per-user-isolation.md), so onboarding writes
exactly where the running gateway looks it up -- NO global "active user" swap,
NO /reload-mcp dance. Two users can be onboarded and transact concurrently.

Scoped token layout (all chmod 600, under HERMES_HOME, gitignored):
  mcp-tokens/zomato/<telegram_id>.json         the user's Zomato OAuth tokens
  mcp-tokens/zomato/<telegram_id>.client.json  their dynamically-registered
                                               OAuth client (needed for refresh)
  mcp-tokens/zomato/<telegram_id>.meta.json    (written lazily by Hermes)

A per-user preferences skeleton is also created under the repo at
  users/<telegram_id>/preferences.md
and the in-flight PKCE state lives at
  users/<telegram_id>/.oauth-pending.json  (deleted once finished)

Subcommands (all print plain text, NEVER secrets). The telegram_id is OPTIONAL
for start/status/finish -- when omitted the current user is resolved from
HERMES_SESSION_USER_ID (the gateway binds this per inbound message; the terminal
tool runs in that user's session), else from the most-recent Telegram session
user_id in ~/.hermes/state.db. This lets the bot run the script with no id and
still scope to whoever sent the current message.

  start  [telegram_id]                 register client + print authorize URL
  finish [telegram_id] <redirect_url>  exchange code, store tokens at scoped path
  status [telegram_id]                 authed / pending / not-authed
  logout [telegram_id]                 remove THIS user's scoped tokens only
  whoami <display_name>                map a Telegram display name -> numeric id

Stdlib only. Never prints token values.
"""

import base64
import hashlib
import json
import os
import secrets
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS = os.path.join(REPO, "users")
HERMES = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))
TOKDIR = os.path.join(HERMES, "mcp-tokens")
# Scoped per-user token directory: matches HermesTokenStorage(server, scope)
# in vendor/hermes-agent/tools/mcp_oauth.py -> mcp-tokens/<server>/<scope>.*
SERVER = "zomato"
SCOPED_TOKDIR = os.path.join(TOKDIR, SERVER)

ISSUER = "https://mcp-server.zomato.com"
AUTHORIZE = ISSUER + "/authorize"
TOKEN = ISSUER + "/token"
REGISTER = ISSUER + "/register"
SCOPE = "offline openid"
# No server ever listens here -- the user pastes the redirect URL back.
REDIRECT_URI = "http://127.0.0.1:8976/callback"


def die(msg):
    print("ERROR: " + msg)
    sys.exit(1)


def udir(tid):
    if not tid.isdigit():
        die("telegram id must be numeric, got %r" % tid)
    return os.path.join(USERS, tid)


def _latest_telegram_user_from_db():
    """Return the user_id of the most-recent non-archived Telegram session.

    Mirrors zomato_chat_oauth.py's ``latest_telegram_session`` query but selects
    the session's ``user_id`` (not its id), so the script can scope to whoever
    most recently messaged the bot. Returns None if the DB or a row is absent.
    """
    database = os.path.join(HERMES, "state.db")
    if not os.path.exists(database):
        return None
    try:
        with closing(sqlite3.connect(database)) as connection:
            row = connection.execute(
                """
                SELECT user_id
                FROM sessions
                WHERE source = 'telegram' AND user_id IS NOT NULL AND archived = 0
                ORDER BY started_at DESC
                LIMIT 1
                """
            ).fetchone()
    except sqlite3.Error:
        return None
    if not row or not row[0]:
        return None
    return str(row[0])


def resolve_telegram_id(tid=None):
    """Resolve the Telegram user id to scope this operation to.

    Resolution order:
      1. An explicit ``tid`` argument (when the caller passes one).
      2. ``HERMES_SESSION_USER_ID`` -- the gateway binds this per inbound
         message and the terminal tool runs inside that user's session, so an
         id-less invocation from chat scopes to whoever sent the current
         message.
      3. The most-recent non-archived Telegram session user_id in
         ``~/.hermes/state.db`` (same source as zomato_chat_oauth.py).

    Dies with a clear message if none resolves. The returned id is validated
    numeric so it is safe to use as the scoped token filename.
    """
    candidate = tid or os.environ.get("HERMES_SESSION_USER_ID") or _latest_telegram_user_from_db()
    if not candidate:
        die("could not determine the Telegram user id (no argument, no "
            "HERMES_SESSION_USER_ID, and no recent Telegram session in "
            "state.db). Pass the numeric id explicitly.")
    candidate = str(candidate).strip()
    if not candidate.isdigit():
        die("resolved Telegram id is not numeric: %r" % candidate)
    return candidate


def scoped_token_path(tid, suffix):
    """Return the scoped MCP token file path for this user.

    ``suffix`` is one of ``".json"`` (tokens), ``".client.json"`` (client info)
    -- mirroring HermesTokenStorage's per-scope layout.
    """
    return os.path.join(SCOPED_TOKDIR, tid + suffix)


def write_private(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2)
    os.chmod(path, 0o600)


def read_json(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def post_json(url, payload, form=False):
    if form:
        body = urllib.parse.urlencode(payload).encode()
        ctype = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(payload).encode()
        ctype = "application/json"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        die("%s returned HTTP %s: %s" % (url, exc.code, detail))


def cmd_start(tid=None):
    tid = resolve_telegram_id(tid)
    d = udir(tid)
    os.makedirs(d, exist_ok=True)
    os.chmod(d, 0o700)

    # Reuse the user's registered client if one exists (the scoped client file
    # is the source of truth; refresh needs it). Register otherwise.
    client = read_json(scoped_token_path(tid, ".client.json"))
    if not client or "client_id" not in client:
        client = post_json(REGISTER, {
            "redirect_uris": [REDIRECT_URI],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "client_name": "Hermes Zomato Companion (tg %s)" % tid,
        })
        write_private(scoped_token_path(tid, ".client.json"), client)

    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    write_private(os.path.join(d, ".oauth-pending.json"), {
        "code_verifier": verifier, "state": state, "created_at": time.time(),
    })

    url = AUTHORIZE + "?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client["client_id"],
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    print("AUTHORIZE_URL: " + url)


def cmd_finish(tid, redirect_url=None):
    # The id is optional: `finish <redirect_url>` (id resolved from session/db)
    # or `finish <telegram_id> <redirect_url>` (explicit id). Disambiguate by
    # whether the first positional looks like a URL.
    if redirect_url is None:
        redirect_url = tid
        tid = None
    tid = resolve_telegram_id(tid)
    d = udir(tid)
    pending = read_json(os.path.join(d, ".oauth-pending.json"))
    if not pending:
        die("no pending auth for %s; run `start %s` first" % (tid, tid))

    q = urllib.parse.parse_qs(urllib.parse.urlsplit(redirect_url.strip()).query)
    code = (q.get("code") or [None])[0]
    state = (q.get("state") or [None])[0]
    if not code:
        die("no ?code= in that URL - paste the FULL final redirect URL")
    if state != pending["state"]:
        die("state mismatch - stale login attempt; run start again")

    client = read_json(scoped_token_path(tid, ".client.json"))
    if not client or "client_id" not in client:
        die("missing client registration for %s; run start again" % tid)
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client["client_id"],
        "code_verifier": pending["code_verifier"],
    }
    if client.get("client_secret"):
        form["client_secret"] = client["client_secret"]
    tokens = post_json(TOKEN, form, form=True)
    if "access_token" not in tokens:
        die("token endpoint response had no access_token (keys: %s)"
            % ", ".join(sorted(tokens)))
    # Hermes persists an absolute expires_at next to expires_in so a process
    # restart reconstructs the right TTL (see HermesTokenStorage.set_tokens).
    if isinstance(tokens.get("expires_in"), (int, float)):
        tokens["expires_at"] = time.time() + int(tokens["expires_in"])

    # Write straight to the SCOPED path the zomato MCP client reads for this
    # user. No active-user swap -- the running gateway picks these up when it
    # lazily opens this user's scoped session on their next Zomato tool call.
    write_private(scoped_token_path(tid, ".json"), tokens)
    os.remove(os.path.join(d, ".oauth-pending.json"))

    # Skeleton preferences file on first successful onboarding.
    prefs = os.path.join(d, "preferences.md")
    if not os.path.exists(prefs):
        with open(prefs, "w") as fh:
            fh.write("# Preferences (telegram %s)\n\n"
                     "- Diet: \n- Default budget: \n- Favourite cuisines: \n"
                     "- Dislikes/allergies: \n" % tid)

    print("OK: user %s authenticated on THEIR OWN Zomato account." % tid)
    print("Tokens stored at the scoped path mcp-tokens/%s/%s.json -- Hermes "
          "opens this user's isolated session on their next Zomato request." %
          (SERVER, tid))


def cmd_status(tid=None):
    tid = resolve_telegram_id(tid)
    tokens = read_json(scoped_token_path(tid, ".json"))
    # ``token_present`` is the flag the persona keys on -- true only when this
    # user has their own scoped Zomato token on disk.
    if tokens:
        exp = tokens.get("expires_at")
        fresh = (exp is None) or (exp > time.time())
        print("token_present: true")
        print("AUTHED (access token %s)" % (
            "valid" if fresh else "expired - refresh due on next connect"))
    elif read_json(os.path.join(udir(tid), ".oauth-pending.json")):
        print("token_present: false")
        print("PENDING: authorize URL issued, waiting for the redirect URL")
    else:
        print("token_present: false")
        print("NOT_AUTHED")


def cmd_logout(tid=None):
    tid = resolve_telegram_id(tid)
    # Remove ONLY this user's own scoped credentials -- never another user's,
    # never the flat/global token, and no gateway restart (the scoped session
    # simply has no token to reconnect with on this user's next request). The
    # provider discovery metadata (.meta.json) is intentionally kept.
    removed = []
    for suffix in (".json", ".client.json"):
        path = scoped_token_path(tid, suffix)
        if os.path.exists(path):
            os.remove(path)
            removed.append(os.path.basename(path))
    # Drop any in-flight PKCE state for this user too.
    pending = os.path.join(udir(tid), ".oauth-pending.json")
    if os.path.exists(pending):
        os.remove(pending)
    token_absent = not os.path.exists(scoped_token_path(tid, ".json"))
    if token_absent:
        print("OK: user %s disconnected from Zomato (removed: %s)." %
              (tid, ", ".join(removed) or "nothing was stored"))
    else:
        die("could not remove tokens for user %s" % tid)


def cmd_whoami(name):
    directory = read_json(os.path.join(HERMES, "channel_directory.json")) or {}
    hits = [c["id"] for c in directory.get("platforms", {}).get("telegram", [])
            if c.get("type") == "dm" and c.get("name") == name]
    if len(hits) == 1:
        print(hits[0])
    elif not hits:
        die("no telegram DM named %r in channel_directory.json" % name)
    else:
        die("ambiguous name %r -> ids %s" % (name, ", ".join(hits)))


def main():
    args = sys.argv[1:]
    # (fn, min_args, max_args) -- id-less forms resolve the user automatically.
    cmds = {
        "start": (cmd_start, 0, 1),    # start [telegram_id]
        "finish": (cmd_finish, 1, 2),  # finish [telegram_id] <redirect_url>
        "status": (cmd_status, 0, 1),  # status [telegram_id]
        "logout": (cmd_logout, 0, 1),  # logout [telegram_id]
        "whoami": (cmd_whoami, 1, 1),  # whoami <display_name>
    }
    if not args or args[0] not in cmds:
        die("usage: zomato_user_auth.py start|status|logout [telegram_id] | "
            "finish [telegram_id] <redirect_url> | whoami <display_name>")
    fn, lo, hi = cmds[args[0]]
    rest = args[1:]
    if not (lo <= len(rest) <= hi):
        die("usage: zomato_user_auth.py start|status [telegram_id] | "
            "finish [telegram_id] <redirect_url> | whoami <display_name>")
    fn(*rest)


if __name__ == "__main__":
    main()

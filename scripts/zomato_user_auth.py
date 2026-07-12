#!/usr/bin/env python3
"""Per-Telegram-user Zomato MCP OAuth (PKCE) for the Hermes bot.

Subcommands (all print plain text, never secrets):

  start  <telegram_id>                 register client + print authorize URL
  finish <telegram_id> <redirect_url>  exchange code, store + activate tokens
  status <telegram_id>                 authed / pending / not-authed
  activate <telegram_id>               make an already-authed user the active one
  whoami <display_name>                map a Telegram display name -> numeric id

Token layout (all chmod 600, gitignored):
  users/<id>/zomato-tokens.json    the user's Zomato OAuth tokens
  users/<id>/zomato-client.json    the dynamically-registered OAuth client
                                   bound to those tokens (needed for refresh)
  users/<id>/.oauth-pending.json   PKCE verifier + state while auth is in flight
  users/.active-zomato-user        telegram id currently installed into Hermes

Hermes reads ~/.hermes/mcp-tokens/zomato.json when it (re)connects the zomato
MCP server, so exactly ONE user is active at a time. `finish`/`activate` swap
the active token + client files; the user must then send /reload-mcp in
Telegram (or the gateway must restart) for the swap to take effect.

Stdlib only. Never prints token values.
"""

import json
import os
import sys
import time
import base64
import hashlib
import secrets
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS = os.path.join(REPO, "users")
HERMES = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))
TOKDIR = os.path.join(HERMES, "mcp-tokens")

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


def cmd_start(tid):
    d = udir(tid)
    os.makedirs(d, exist_ok=True)
    os.chmod(d, 0o700)

    # Reuse the user's registered client if one exists; register otherwise.
    client = read_json(os.path.join(d, "zomato-client.json"))
    if not client or "client_id" not in client:
        client = post_json(REGISTER, {
            "redirect_uris": [REDIRECT_URI],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "client_name": "Hermes Zomato Companion (tg %s)" % tid,
        })
        write_private(os.path.join(d, "zomato-client.json"), client)

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


def _install_active(tid):
    """Copy the user's token + client files into Hermes's mcp-tokens dir."""
    d = udir(tid)
    tokens = read_json(os.path.join(d, "zomato-tokens.json"))
    client = read_json(os.path.join(d, "zomato-client.json"))
    if not tokens or not client:
        die("user %s has no stored tokens; run start/finish first" % tid)
    os.makedirs(TOKDIR, exist_ok=True)
    write_private(os.path.join(TOKDIR, "zomato.json"), tokens)
    write_private(os.path.join(TOKDIR, "zomato.client.json"), client)
    write_private(os.path.join(USERS, ".active-zomato-user"), {"telegram_id": tid})


def cmd_finish(tid, redirect_url):
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

    client = read_json(os.path.join(d, "zomato-client.json"))
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
    # Hermes persists an absolute expires_at next to expires_in; mirror that.
    if isinstance(tokens.get("expires_in"), (int, float)):
        tokens["expires_at"] = time.time() + int(tokens["expires_in"])
    write_private(os.path.join(d, "zomato-tokens.json"), tokens)
    os.remove(os.path.join(d, ".oauth-pending.json"))

    # Skeleton preferences file on first successful onboarding.
    prefs = os.path.join(d, "preferences.md")
    if not os.path.exists(prefs):
        with open(prefs, "w") as fh:
            fh.write("# Preferences (telegram %s)\n\n"
                     "- Diet: \n- Default budget: \n- Favourite cuisines: \n"
                     "- Dislikes/allergies: \n" % tid)

    _install_active(tid)
    print("OK: user %s authenticated and set as the ACTIVE Zomato account." % tid)
    print("NOTE: send /reload-mcp in Telegram (and confirm) so Hermes reconnects "
          "with the new tokens.")


def cmd_status(tid):
    d = udir(tid)
    tokens = read_json(os.path.join(d, "zomato-tokens.json"))
    active = read_json(os.path.join(USERS, ".active-zomato-user")) or {}
    if tokens:
        exp = tokens.get("expires_at")
        fresh = (exp is None) or (exp > time.time())
        print("AUTHED (access token %s)%s" % (
            "valid" if fresh else "expired - refresh due on next connect",
            " [ACTIVE]" if active.get("telegram_id") == tid else ""))
    elif read_json(os.path.join(d, ".oauth-pending.json")):
        print("PENDING: authorize URL issued, waiting for the redirect URL")
    else:
        print("NOT_AUTHED")


def cmd_activate(tid):
    _install_active(tid)
    print("OK: user %s is now the ACTIVE Zomato account. Send /reload-mcp in "
          "Telegram to apply." % tid)


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
    cmds = {"start": (cmd_start, 1), "finish": (cmd_finish, 2),
            "status": (cmd_status, 1), "activate": (cmd_activate, 1),
            "whoami": (cmd_whoami, 1)}
    if not args or args[0] not in cmds or len(args) - 1 != cmds[args[0]][1]:
        die("usage: zomato_user_auth.py start|status|activate|whoami <arg> | "
            "finish <telegram_id> <redirect_url>")
    cmds[args[0]][0](*args[1:])


if __name__ == "__main__":
    main()

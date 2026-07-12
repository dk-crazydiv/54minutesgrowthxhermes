# Per-Telegram-user Zomato onboarding

How a brand-new Telegram user gets their own Zomato account wired into the
Hermes bot, without touching anyone else's login.

## The flow (what the user sees)

1. User DMs the bot "Hi". No `users/<telegram_id>/zomato-tokens.json` exists,
   so the agent sends a welcome + a Zomato authorize URL.
2. User opens the URL, logs into Zomato, approves. The browser lands on
   `http://127.0.0.1:8976/callback?code=...&state=...` — the page does NOT
   load (nothing listens there); that's expected. User copies the full address
   from the URL bar and pastes it back into the chat.
3. Agent runs `finish`, which exchanges the code (PKCE) for tokens, stores
   them per-user, installs them as the active Hermes zomato tokens, and asks
   the user to send `/reload-mcp` (+ confirm). After that, every request from
   that Telegram id uses their own account — no re-login until refresh fails.

## The machinery

`scripts/zomato_user_auth.py` (stdlib-only python3):

| Command | Does |
|---|---|
| `start <id>` | Dynamic client registration (Zomato's `/register` returns a static public client — id `fd37dd28-…`, secret `Z-MCP` — and echoes back any redirect URI, so localhost works), generates PKCE verifier+challenge, saves `users/<id>/.oauth-pending.json`, prints `AUTHORIZE_URL: …` |
| `finish <id> <redirect_url>` | Validates `state`, exchanges `code` at `https://mcp-server.zomato.com/token`, writes `users/<id>/zomato-tokens.json` (with `expires_at`, like Hermes does), creates `preferences.md` skeleton, installs tokens as active |
| `status <id>` | `NOT_AUTHED` / `PENDING` / `AUTHED [ACTIVE]` — never prints secrets |
| `activate <id>` | Re-installs an already-authed user's tokens as active |
| `whoami "<name>"` | Maps a Telegram display name → numeric id via `~/.hermes/channel_directory.json` (the session prompt only shows "DM with \<name\>") |

File layout (all chmod 600, gitignored — see `.gitignore`):

```
users/<telegram_id>/zomato-tokens.json   the user's OAuth tokens
users/<telegram_id>/zomato-client.json   registered client (needed for refresh)
users/<telegram_id>/.oauth-pending.json  PKCE state while auth is in flight
users/.active-zomato-user                which id is currently installed
```

## How per-user tokens reach the MCP layer (the design)

Hermes stores MCP OAuth material in `~/.hermes/mcp-tokens/zomato.json`
(+ `.client.json`, `.meta.json`) via `tools/mcp_oauth.py` FileTokenStorage.
The MCP SDK's `OAuthClientProvider` loads that file **when the zomato server
(re)connects**, not per tool call. So:

- `finish`/`activate` copy the user's token + client files over
  `~/.hermes/mcp-tokens/zomato.json` / `zomato.client.json`.
- The swap takes effect on the next reconnect — `/reload-mcp` in Telegram
  (built-in gateway slash command, needs a confirm tap) or a gateway restart.
- Token refreshes done by Hermes land back in `~/.hermes/mcp-tokens/zomato.json`
  only — refreshed tokens are NOT synced back to `users/<id>/` (known gap;
  worst case the user re-runs the login flow).

### Single-active-user caveat

Hermes has exactly one token file per MCP server, and one shared zomato
connection for all Telegram sessions. **Only one user's Zomato account is
live at a time.** Two users ordering simultaneously will fight over the
connection. Fine for the demo; a real fix means per-session MCP auth inside
Hermes itself.

### Terminal-backend caveat (action needed once, by a human)

The SOUL has the agent run `scripts/zomato_user_auth.py` via its terminal
tool. On this machine `~/.hermes/config.yaml` has `terminal.backend: docker`
— a sandbox with **no host mounts**, so the script/repo/`~/.hermes` are not
reachable from the agent's terminal. For the flow to work, a human must set:

```yaml
terminal:
  backend: local
```

in `~/.hermes/config.yaml` and restart the gateway. (An automated change to
this was intentionally not made — it removes the terminal sandbox for a bot
that may be reachable by non-owners; decide with the Telegram allowlist in
mind.) Until then, a human can run the same commands by hand while the agent
relays URLs.

## Reset procedure (make the bot un-authed again)

```sh
cd ~/.hermes/mcp-tokens
cp zomato.json zomato.json.bak-$(date +%Y%m%d)   # backup
rm zomato.json                                   # bot is now un-authed
rm -rf <repo>/users/<id>                         # forget a specific user
rm -f <repo>/users/.active-zomato-user
launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway
```

Done on 2026-07-12 for Jatin's login (backup: `zomato.json.bak-20260712`).
`users/kartik/` and all swiggy token files untouched.

## Human test script (the part that can't be automated)

1. Confirm `terminal.backend: local` in `~/.hermes/config.yaml` (see caveat),
   restart gateway, check `~/.hermes/logs/gateway.log` for "telegram connected".
2. From a Telegram account with **no** `users/<id>/` folder, DM the bot "Hi".
   Expect: welcome + an `https://mcp-server.zomato.com/authorize?...` URL
   containing `code_challenge` and `redirect_uri=http://127.0.0.1:8976/callback`.
3. Open the URL, log in, approve. Copy the final `http://127.0.0.1:8976/...`
   address (page won't load — expected) and paste it into the chat.
4. Expect: "connected" confirmation + instruction to send `/reload-mcp`.
   Send `/reload-mcp`, tap confirm.
5. Ask "show my saved addresses" — should return YOUR addresses, not the
   previous account's.
6. Sanity: `python3 scripts/zomato_user_auth.py status <id>` →
   `AUTHED ... [ACTIVE]`; `users/<id>/preferences.md` exists;
   `git status` shows no token files.

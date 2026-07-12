# Project Notes

Research facts carried over from the plan doc. These are the load-bearing
decisions — the things that, if they change, change everything downstream.

## Hermes

- **One-command install.** Hermes is meant to be stood up with a single
  command, not a multi-day integration project. If setup starts sprawling,
  something has gone wrong — re-read the docs, don't patch around it.
- **Gateway processes.** Hermes runs its work through gateway processes
  rather than inlining model calls. The gateway is the seam where models
  get swapped and where traffic gets watched. Treat it as the front door.
- **Any OpenAI-compatible endpoint works.** Hermes speaks the
  OpenAI-compatible API, so glm, minimax, and anything else that matches
  that shape can drop in. This is why "glm + minimax" is a config choice,
  not a rewrite — both present the same interface to the gateway.

## Swiggy MCP

- **Free from localhost.** The Swiggy MCP server runs locally and costs
  nothing to run. It's the bridge between Hermes and Swiggy's actual API.
- **First call is `get_addresses`.** When a session starts, the first thing
  the MCP does is pull the saved addresses. Everything downstream —
  restaurant search, cart, checkout — is scoped to an address. No address,
  no order, so addresses come first.

## Auth

- **OAuth 2.1 with PKCE.** Swiggy auth is OAuth 2.1 + PKCE, not a stored
  password. The flow is: phone number in, OTP out, human reads the OTP and
  types it back. The copilot never sees the OTP and never holds the
  password.
- **Phone + OTP, human in the loop.** The phone number starts it; the OTP
  completes it; the human supplies both. This is the concrete shape of
  "never act as the human without them" — the grant is the human's click,
  literally.

## Three servers

The system is three servers, not one monolith:

1. **Hermes / agent server** — the brain. Runs the agent loop, talks to glm
   and minimax through the gateway.
2. **Swiggy MCP server** — the hands. Localhost, free, exposes Swiggy
   actions as MCP tools. `get_addresses` is the entry point.
3. **Admin app** — the control room. Small, human-facing, watches the other
   two.

Keeping them as three means each can be restarted, swapped, or watched on
its own. Don't merge them to save a port — the separation is the point.

## Open questions

- Nothing parked here yet. When a fact turns out to be a guess, move it
  here and mark it.

## Telegram gateway — proven live, and how to bring it back
The whole bring-up, start to first reply (operator-verified):
1. `bash setup.sh` — installs hermes pinned + hash-verified into
   vendor/hermes-agent. Idempotent; run it after any clone.
2. `cp .env.example .env` and fill four values: GLM_API_KEY and
   MINIMAX_API_KEY (copy from ~/.local/share/opencode/auth.json — keys
   "zai-coding-plan" and "minimax-coding-plan"), TELEGRAM_BOT_TOKEN (from
   @BotFather), TELEGRAM_ALLOWED_USERS (numeric ID from @userinfobot —
   NOT the @username).
3. `bash scripts/smoke.sh` — both brains must answer PONG before anything
   else. If one fails, it's the key or the base URL, nothing deeper.
4. `bash scripts/telegram.sh start` — the gateway log is
   ~/.hermes/logs/gateway.log; a healthy round-trip logs "inbound message"
   then "response ready ... time=Ns". First reply took ~13s on glm-5.2.
Gotchas that cost time once, never again:
- Hermes must be installed ON THE HOST. Task sandboxes can install and
  test it inside their VM, but the gateway serving real Telegram runs on
  the host — a task proves the scripts; the operator (or a host step)
  runs them.
- The gateway defaults the model per provider when none is configured
  ("No model configured — defaulting to glm-5.2"). Fine for now; set it
  explicitly when routing matters.
- The bot token transited a board comment once. Rotate it in @BotFather
  when convenient and update .env — one line, no restart drama
  (telegram.sh restart).

- The gateway dies if its launching shell dies — start it with nohup +
  disown, or better, install it as a service once and forget it:
  `hermes gateway install` (user service, auto-restart). It went down once
  this way; the bot was silent until restarted.

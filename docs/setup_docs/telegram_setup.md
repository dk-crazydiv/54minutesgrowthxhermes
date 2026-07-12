# Telegram gateway setup

The gateway is a long-lived Hermes process that connects your Telegram bot to the
brains. One bot token, one allowlist, one script.

## Steps

1. Make a bot: message @BotFather on Telegram, `/newbot`, copy the token.
2. Get your numeric user ID from @userinfobot (the number, not your @username).
3. Put both in the repo root `.env`:

   ```
   TELEGRAM_BOT_TOKEN=<token>
   TELEGRAM_ALLOWED_USERS=<your numeric id>
   ```

4. `bash setup.sh` (copies `.env` to `~/.hermes/.env` and installs `config/SOUL.md`
   as the bot's persona).
5. Start it:

   ```bash
   bash scripts/telegram.sh start-bg   # background, pid at ~/.hermes/gateway.pid
   bash scripts/telegram.sh status     # check
   bash scripts/telegram.sh logs       # tail ~/.hermes/logs/gateway.log
   ```

6. Prove it: message the bot from your phone. A round-trip shows in the log as an
   inbound `[telegram]` line, an agent turn, and the outbound reply. First reply takes
   ~13s on glm.

## Gotchas

- The gateway must run on the host, never inside a task sandbox.
- `start-bg` survives the terminal closing but not a reboot. For that, install it as a
  service: `hermes gateway install` (user service). This is on the backlog.
- The allowlist wants numeric IDs. An empty `TELEGRAM_ALLOWED_USERS` means the bot
  warns and may answer strangers — don't leave it empty.
- If the bot goes silent, check `scripts/telegram.sh status` first, then the log.
  Most silence is "the process died with its shell".
- Treat the bot token like a password. Ours leaked in a board comment once, which is
  why token rotation is on the backlog.

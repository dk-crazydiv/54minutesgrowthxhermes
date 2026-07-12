# 05 · Setup — get Hermes running

← [Index](README.md) | Prev: [Scoring](04-scoring.md) | Next: [Your track →](06-your-track.md)

Sort your model access, then get Hermes answering. If you already run Hermes, you only need the first section. The rest is for first-timers.

## Sort your LLM access first

Hermes needs an LLM to drive it. It talks to anything that speaks the OpenAI API, so you're not boxed in. Three options — **OpenAI recommended.**

| Option | Cost | Notes |
|--------|------|-------|
| **OpenAI / GPT-5.6 Sol** (recommended) | Credits on us | The best frontier model to drive Hermes; official partner. Sent your OpenAI org ID? You already have $200 credits + Codex Pro. → openai.com |
| **OpenRouter** | $10 credit | Cheapest way in. Same models, more flexibility. → openrouter.ai |
| **Nous Portal** | $20/month | Managed Tool Gateway — web search, image gen, TTS, browser automation all handled by Nous. → portal.nousresearch.com |

### Running OpenAI

Grab a key from `platform.openai.com/api-keys` and put it in `~/.hermes/.env`:

```
OPENAI_API_KEY=sk-...
```

Then set the provider in `~/.hermes/config.yaml`. **The provider id is `openai-api`, not `openai`:**

```yaml
model:
  provider: "openai-api"
  default: "gpt-5.6-sol"
```

Or do it in one line:

```bash
hermes chat --provider openai-api --model gpt-5.6-sol
```

> **Your provider is not scored.** No track gives points for which model you run. Power-up points come from the six five partner integrations only. Going the OpenRouter route? Watch the walkthrough — it covers adding $10 credit and connecting it to Hermes.

## Using Hermes as your coding partner? Bring your setup with you

If you already code with Claude Code or Codex, don't start from a blank agent. Most carries over; the rest takes ~5 minutes. **Do this before the sprint starts, not during it.**

| Thing | Effort | How |
|-------|--------|-----|
| **Project file** | Already works | Hermes reads your repo's `CLAUDE.md` on its own. It looks for `.hermes.md`, then `AGENTS.md`, then `CLAUDE.md`, and loads only the **first** it finds. Keep one file, not three. |
| **Skills** | One line | Point Hermes at your existing skills folder in `~/.hermes/config.yaml` and every one shows up as a `/slash` command. |
| **Global instructions** | Port by hand | Hermes deliberately does **not** read your global `~/.claude/CLAUDE.md`. Move durable parts into `~/.hermes/SOUL.md` (behavior) and `~/.hermes/memories/MEMORY.md` (facts). MEMORY.md is capped at ~2,200 chars. |
| **Commands & subagents** | Rewrite as skills | No `.claude/commands` or `.claude/agents` equivalent. Each command becomes a skill (same `/name` back). Subagents are spawned at runtime instead. |
| **MCP servers** | Translate to YAML | Your `mcpServers` JSON becomes an `mcp_servers:` block in `~/.hermes/config.yaml`. |

The skills one-liner, in `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/.claude/skills
```

For the rest, let Hermes do the work — open it in your repo and give it:

> Read my ~/.claude folder and this repo's CLAUDE.md, then port them to Hermes.
> Turn each command in .claude/commands into a skill under ~/.hermes/skills/.
> Translate my MCP servers into the mcp_servers: block in ~/.hermes/config.yaml.
> Summarise my global CLAUDE.md into ~/.hermes/SOUL.md and memories/MEMORY.md.
> Tell me what you could not carry over and why.

There is no one-click importer (`hermes import` restores Hermes backups, not Claude setups). Run the prompt above before 10:00 AM, then check `hermes skills browse` shows what you expect.

---

## First time with Hermes? (first-run walkthrough)

Already have Hermes installed and answering? Skip to [Your track](06-your-track.md).

### 01 · Install Hermes
Works on Linux, macOS, WSL2, Termux. One line:

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Open a fresh terminal, then pick your model provider and verify:

```bash
hermes model
hermes status
```

On Nous Portal you should see the Nous Tool Gateway with managed tools active. On OpenAI/OpenRouter you'll see your provider and model instead (you're wiring your own tools rather than renting the managed gateway).

### 02 · Wire up Telegram
Hermes runs on your machine; Telegram becomes your remote control. Four steps:

1. **Create a Telegram bot.** Talk to `@BotFather`, send `/newbot`, give a display name and a username ending in `bot`. Save the token privately. (Useful: `/mybots`, `/setprivacy`, `/revoke`.)
2. **Get your numeric Telegram user ID.** Use `@userinfobot` or `@get_id_bot`. The number matters; your username doesn't.
3. **Configure the Hermes gateway.** Run `hermes gateway setup`, select Telegram, paste the bot token and your numeric allowed user ID.
4. **Start & test.** Run `hermes gateway` and leave it running. DM your bot: *"Hello Hermes. Reply in one sentence and tell me what tools are active."*

If the wizard fails, put these in `~/.hermes/.env` then restart:

```
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_ALLOWED_USERS=<your-numeric-user-id>
```

> Telegram first, not WhatsApp. Less ceremony. Add other channels once the agent already works.

### 03 · Memory and skills (after chat works)
Only start after Hermes answers from Telegram. Memory tiers:

| Tier | Name | What |
|------|------|------|
| 0 | Always-on | `USER.md` + `MEMORY.md`, injected into the system prompt every turn. |
| 1 | Session history | Raw sessions as `.jsonl`, indexed in SQLite with FTS5 full-text search for cross-session recall. |
| 2 | Pluggable | Holographic (local, free) or Honcho (self-improving user model). Only one active at a time. |

```bash
hermes memory setup
hermes skills browse
```

### 04 · Checkpoint: is your agent alive?
- `hermes status` shows your provider and model, or the Nous Tool Gateway
- Telegram DM responds from your bot
- A web-search prompt works
- A Telegram image test works, or the URL fallback works
- `hermes memory status` is clear if you enabled external memory

Final test — send your bot:
> Give me a one-paragraph setup report: model, tool route, channel, memory, and one thing still missing.

If the answer is coherent, setup is alive. Go pick your idea.

## Common breaks and fixes

| Symptom | Fix |
|---------|-----|
| Provider not authenticated | Re-run `hermes model` and finish login. On OpenAI/OpenRouter, check the key is in `~/.hermes/.env` with no trailing spaces. |
| OpenAI key set but Hermes won't start | Provider id is `openai-api` (not `openai`); model id is `gpt-5.6-sol`. Check both in `config.yaml`, then `hermes status`. |
| Telegram bot token copied wrong | Re-run `hermes gateway setup` and paste again. |
| Telegram user ID wrong | Get the numeric ID from `@userinfobot`/`@get_id_bot`, re-run `hermes gateway setup`. |
| Group messages don't appear | Fix BotFather privacy mode (`/setprivacy`) or make the bot a group admin. Remove and re-add after changing. |
| Vision over SSH doesn't see clipboard | Stop debugging the clipboard. Send the image to the bot via Telegram or a URL. |
| Memory provider confusion | Only one external provider active at a time. Pick Holographic or Honcho, not both (`hermes memory status`). |
| Ollama context window too small | Hermes needs ≥64K tokens. Set `num_ctx` to at least 65536 server-side via a Modelfile. |
| MCP tools not showing up | MCP servers register at startup. After changing `config.yaml`, restart Hermes or run `/reload-mcp` inside chat. |

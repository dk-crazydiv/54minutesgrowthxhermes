# Web search (Linkup) + Telegram voice notes (STT)

Wired 12 Jul via `scripts/setup-hermes-search-voice.sh` (also runs as part of
`bash setup.sh`). Both capabilities are **native Hermes features** — we only
configured them and added one small provider plugin.

## What Hermes ships natively (discovered 2026-07-12, v2026.7.7.2)

**Web search** — `web_search`/`web_extract` are in `_HERMES_CORE_TOOLS`
(`toolsets.py`), which the `hermes-telegram` platform toolset uses, so the
Telegram bot already has search tools. Backends are pluggable via
`agent/web_search_registry.py`; bundled providers: `ddgs` (keyless, was
active), `tavily`, `exa`, `parallel`, `firecrawl`, `searxng`, `brave-free`,
`xai`. **Linkup is NOT bundled**, but user plugins in `~/.hermes/plugins/`
can register providers via `ctx.register_web_search_provider()`. Selection:
`web.search_backend` > `web.backend` > availability walk. An explicitly
configured backend wins **even if its key is missing** — that's why our
Linkup provider falls back internally (below).

**Voice notes** — the Telegram adapter downloads incoming voice/audio to
`~/.hermes/audio_cache` and transcribes via `tools/transcription_tools.py`.
Six built-in STT providers: `local` (faster-whisper, keyless, **default**),
`local_command`, `groq` (`GROQ_API_KEY`), `openai` (`VOICE_TOOLS_OPENAI_KEY`,
note: not `OPENAI_API_KEY`), `mistral`, `xai`. Config was already
`stt.enabled: true` with `stt.local.model: base` — the only missing piece was
the `faster-whisper` package in the Hermes venv.

## What the script does (idempotent)

1. Syncs `config/hermes-plugins/web-linkup/` → `~/.hermes/plugins/web-linkup/`.
2. `~/.hermes/config.yaml`: adds `web-linkup` to `plugins.enabled`, sets
   `web.search_backend: linkup`, ensures `stt.enabled: true`.
3. Installs `faster-whisper` into `~/.hermes/hermes-agent/venv`.

Restart the gateway after running it:
`launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway` (or
`scripts/telegram.sh stop && start-bg`), then check
`~/.hermes/logs/gateway.log` for `✓ telegram connected`.

## The web-linkup plugin

Source of truth: `config/hermes-plugins/web-linkup/` (repo). Search-only
provider hitting `POST https://api.linkup.so/v1/search`
(`Authorization: Bearer $LINKUP_API_KEY`, body
`{q, depth: standard, outputType: searchResults}`).

**Graceful fallback:** while `LINKUP_API_KEY` is unset in `~/.hermes/.env`,
`search()` delegates to the bundled `ddgs` provider — so "what's the weather
in Bangalore" works today, and flips to Linkup the moment the key lands.
`web_extract` still resolves through `web.backend` (ddgs) since Linkup is
search-only.

## Keys the human owes (all optional — everything works keyless today)

- `LINKUP_API_KEY` in `~/.hermes/.env` (and repo `.env` so setup carries it)
  → real Linkup search instead of ddgs fallback. Restart gateway after.
- Nothing for voice: local faster-whisper needs no key. To switch to a cloud
  STT set `stt.provider: groq` + `GROQ_API_KEY` (free tier) or
  `stt.provider: openai` + `VOICE_TOOLS_OPENAI_KEY`.

## Verified 2026-07-12 (Jatin's machine)

- `hermes plugins list` shows `web-linkup | enabled | user`.
- Provider registers under `linkup`; with no key, a live `search("weather in
  Bangalore today")` returned 3 real ddgs results through the fallback path.
- `transcribe_audio()` on a generated wav returned
  `{'success': True, 'provider': 'local'}` — the whisper `base` model is now
  downloaded/cached, so the first real voice note won't stall on a 145MB pull.
- Gateway restarted clean: `✓ telegram connected`, no plugin errors.

**Not verifiable non-interactively (human test):** send the bot a Telegram
voice note ("what's the weather in Bangalore") and confirm it transcribes and
answers with a web search. Also re-test once `LINKUP_API_KEY` is added.

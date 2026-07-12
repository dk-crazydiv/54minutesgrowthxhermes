# Active agents on this machine

This file says which brains and surfaces are running HERE, right now. It is committed
once as a template, then gitignored — every teammate keeps their own copy, so we can
all run different agents without stepping on each other. Update it when you change
what's running.

## Owner

Kartik (kartik@deepklarity.com)

## Brains

| Provider | Model | Status | Used for |
|---|---|---|---|
| zai (GLM) | glm-5 | working, smoke green | thinking |
| minimax | MiniMax-M3 | working, smoke green | chatty/fast replies |
| openai-codex | gpt-5.5 | working, smoke green | code-heavy work |

## Surfaces

| Surface | Status |
|---|---|
| Telegram gateway | running in background (`scripts/telegram.sh status` to check) |
| Git watcher | manager session runs it (`bootstrap/watch_git.sh status`) |

## Notes

Smoke everything with `bash scripts/smoke.sh`. Keys live in `.env` (never committed).

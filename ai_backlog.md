# AI backlog

- [ ] `~/.hermes/config.yaml` default model got flipped to `openai-codex:gpt-5.5` mid-day and that combo 400s ("Unknown Model") — CLI test harness pins `-m glm-5.2 --provider zai` to dodge it. Decide the real default and fix config + gateway.
- [ ] `~/.hermes/config.yaml` still carries `swiggy-food` / `swiggy-instamart` MCP entries; docs/hermes/setup.md says they were removed 12 Jul. Reconcile (remove entries or fix doc).
- [ ] MCP attach in CLI `hermes chat -q` is flaky without an explicit `-t` (one session got core tools only, no `mcp__zomato__*`). Harness passes `-t hermes-cli,zomato`; find the root cause if it bites the gateway too.

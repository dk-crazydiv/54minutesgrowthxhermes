# Codex brain setup (OpenAI via ChatGPT subscription)

Hermes ships an `openai-codex` provider (alias: `codex`). It talks to
`chatgpt.com/backend-api/codex` using OAuth tokens, so your ChatGPT subscription pays
for it. No API key, nothing in `.env`.

## The path that works

1. Install the OpenAI Codex CLI and log in (`npm i -g @openai/codex`, then
   `codex login`). This writes `~/.codex/auth.json`. If you already use codex in your
   terminal, you're done with this step.

2. Import those tokens into the Hermes auth store. Warning: `hermes auth add
   openai-codex` does NOT import — it always starts a fresh device-code login, and
   OpenAI rate-limits that (we hit a 429 on first try). Import directly instead, from
   `vendor/hermes-agent`:

   ```bash
   cd vendor/hermes-agent
   venv/bin/python - <<'EOF'
   from hermes_cli import auth as a
   toks = a._import_codex_cli_tokens()
   print("imported:", bool(toks))
   if toks:
       a._save_codex_tokens(toks)
       print("saved")
   EOF
   ```

3. Prove it:

   ```bash
   ./hermes -z "Reply with exactly PONG and nothing else." --provider openai-codex --model gpt-5.5
   ```

   You should get `PONG`. Or run `bash scripts/smoke.sh` from the repo root — it tests
   all three brains and skips codex cleanly if tokens are missing.

## Gotchas

- `hermes auth status codex` can say "logged out" even when the runtime works. The
  runtime reads the credential pool, the status command reads a different slot. Trust
  the PONG test, not the status line.
- Model name: we use `gpt-5.5` (same as `~/.codex/config.toml`). Override with
  `CODEX_MODEL=<model>` when running smoke.sh.
- Hermes keeps its own token session. If the Codex CLI rotates its token, Hermes keeps
  working independently. If Hermes tokens die, redo step 2.

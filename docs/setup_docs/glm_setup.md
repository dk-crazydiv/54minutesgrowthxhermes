# GLM + MiniMax brains setup (API keys via .env)

GLM (Z.AI) is the thinking brain, MiniMax the chatty one. Both are OpenAI-compatible
endpoints, so they're pure config: a key in `.env`, no code.

## Steps

1. Get the keys from Kartik. On his machine they live in the opencode auth store at
   `~/.local/share/opencode/auth.json`, fields `zai-coding-plan.key` and
   `minimax-coding-plan.key`.

2. Put them in the repo root `.env` (copy `.env.example` first):

   ```
   GLM_API_KEY=<key>
   MINIMAX_API_KEY=<key>
   ```

   `.env` is gitignored. Never commit it, never paste keys in a commit or a doc.

3. `bash setup.sh` copies `.env` to `~/.hermes/.env`, where the gateway reads it.
   Re-run setup any time you change `.env`.

4. Prove it: `bash scripts/smoke.sh`. GLM and MiniMax must both say PONG.

## Gotchas

- Coding-plan keys need the coding endpoint. Hermes auto-detects, but if GLM errors,
  set `GLM_BASE_URL=https://api.z.ai/api/coding/paas/v4` in `.env`.
- Naming drift: the same provider is called `zai` (smoke.sh `--provider zai`),
  `GLM_API_KEY` (.env), and glm (docs). They're all Z.AI. Fixing the drift is on the
  backlog.
- Default models: `glm-5` and `MiniMax-M3` (override with `GLM_MODEL` /
  `MINIMAX_MODEL`). Set models explicitly where routing matters — an unset model makes
  the gateway log "No model configured, defaulting to glm-5.2".

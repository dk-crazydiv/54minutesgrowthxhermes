# Objective

Put a Hermes agent on Kartik's Telegram so his existing model subscriptions do the work.
GLM (Z.AI coding plan) and MiniMax run it today. Codex (ChatGPT subscription) joins next.

The bot should feel like texting a sharp assistant. Fast replies from the cheap chatty
brain, hard thinking from the strong one, and the human never pays per-token for what a
subscription already covers.

## Roles

- **Kartik** owns the phone, the subscriptions, and every final decision.
- **Manager Fable (this session)** plans, dispatches, watches, and keeps the
  mission-control page current. It does not do worker-sized jobs by hand.
- **Worker Fables** each get their own session. Everyone works on main and pushes
  often. The manager sees pushes through the git watcher and pulls at clean moments.

## What done looks like

1. Telegram bot answers reliably, survives reboots, allowlisted to Kartik.
2. `scripts/smoke.sh` proves every enabled brain answers, including Codex.
3. Routing is deliberate: named model per job, no "defaulting to" lines in the logs.
4. Any session can cold-start from RESUME.md alone.

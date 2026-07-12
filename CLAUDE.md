# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Start here, every session

**Read `docs/roadmap/RESUME.md` first and run `bash bootstrap/watch_git.sh once`.** RESUME.md is the entrypoint: current state, the watcher ritual, and the hard facts. Everyone works on main — small commits, push often, pull before you push; the watcher tells the manager when new work landed. Voice for all docs and updates: `docs/roadmap/TONE.md`.

## What this project is

Two layers, one repo:

1. **The platform (now):** a Hermes agent on Kartik's Telegram, powered by his subscriptions — GLM (Z.AI) and MiniMax today, Codex (ChatGPT subscription) next. See `docs/roadmap/OBJECTIVE.md`.
2. **The product idea (buildathon):** the **Food Companion Agent on Zomato** — search, repeat, optimise, place, and track Zomato food orders by chatting. Spec, scope, and the Zomato-over-Swiggy decision: `docs/idea.md`. Swiggy research in `docs/swiggy/` is reference-only.

**Hackathon scope (food ordering only — build these four flows, nothing more):**
1. Natural-language search (one filtered Zomato call: price/rating/distance/offers)
2. Repeat a previous order (lifetime history; re-resolve items against the live menu)
3. Prepare and optimise a cart (offers/MOV/budget awareness via get_cart_offers)
4. Calendar-aware order timing

Grocery/Instamart is out of scope entirely — Zomato is food delivery only, and that's
the product. The old flow 5 (back-in-stock watch) died with the platform decision.

Everything else in `docs/idea.md` is a demo-able extension, not a build target.

## Design Principles

**Simplicity is a feature.** This is a hackathon — between two correct approaches, pick the one with fewer moving parts. Don't write a framework when a function will do. Don't generalize from one instance. Don't add config for a decision you can just make. If a shortcut is the right call, take it — but be able to say in one sentence why it won't bite before the demo.

**Default First.** Everything should work out of the box with sensible defaults (budget, preferences, polling interval). Configuration is suggestive, not required — the user intervenes only when they want something different.

**Solve the actual problem.** The value is fewer steps to a placed order, not clever prediction. Every feature should be traceable to "faster ordering with fewer clicks." If it isn't, cut it.

**Demo-first prioritization.** A feature that works end-to-end in the demo conversation beats two features that half-work. When in doubt, ask: "does this make the demo script run?"

## Domain Rules (non-negotiable)

These come from the limitations in `docs/idea.md` — treat them as hard constraints:

- **The user always gives final approval before an order is placed.** The agent prepares carts; it never checks out unprompted.
- **Never blindly retry checkout** — duplicate orders are a real failure mode. On ambiguous checkout errors, check order status before retrying.
- **One restaurant per cart, exactly one variant per item** — Zomato rejects mixed carts; the server's `final_amount` is authoritative, never recompute totals client-side.
- **Prices and availability can change** between search and checkout — re-verify via a fresh cart at confirmation time, don't trust stale search results. Fees/taxes only exist on a live cart.
- **Payment is UPI QR or COD only** — the QR comes back at checkout; payment never flows through the agent.
- Calendar data is used only to time orders — don't surface or store meeting content beyond what's needed.

## Methodical Problem-Solving

**Understand before designing. Observe before acting. Change one thing at a time.**

1. **Observe first** — read the actual error/MCP response before theorizing. Check what IS happening, not what SHOULD.
2. **State your hypothesis** before changing anything: "I think the problem is X because Y, and changing Z should fix it."
3. **Verify assumptions before building on them** — especially MCP tool schemas and responses. Call the tool and look at real output; don't assume field names or shapes.
4. **Change one thing at a time.** Shotgun fixes hide the real cause.
5. **When stuck after 2 attempts, zoom out** — the diagnosis is probably wrong, not the fix.

**Treat the cause, not the symptom.** If a fix only works for this exact instance and wouldn't prevent the same class of problem next time, it's a symptom patch.

## Disk-Anchored Development

**The disk is the memory, not the conversation.** Sessions end and context compacts — any work spanning more than one focused task must leave a trail a future session can pick up cold.

| Content | Location |
|---|---|
| Product spec & scope | `docs/idea.md` |
| Hermes integration notes / API findings | `docs/hermes/` |
| Swiggy MCP notes (tool schemas, real response shapes, quirks) | `docs/swiggy/` |
| Zomato research (comparison/fallback) | `docs/zomato/` |
| Work queued for AI sessions | `ai_backlog.md` |
| Work for the humans | `human_backlog.md` |

**When you discover something about the Hermes or Swiggy MCP APIs (a tool's real schema, an undocumented behavior, a rate limit), write it into the matching `docs/` subdirectory in the same turn.** Re-discovering API behavior every session is the biggest time sink in a hackathon.

**Backlog discipline:** finished items get checked off, not deleted. New follow-up work discovered mid-task goes to `ai_backlog.md` rather than derailing the current task. Don't create new tracker/status files — these two backlogs plus `docs/` are the whole system.

## Subagent Strategy

The main conversation is a coordinator. Delegate independent exploration (reading docs, probing MCP tools, searching code) to parallel subagents in a single message — sequential dispatch of independent tasks is an anti-pattern. Keep synthesis, architecture decisions, and anything touching the demo script in the main conversation.

## Testing & Proof

**Tests pass ≠ feature works.** The bar for "done" is the demo conversation running live against real Hermes + Swiggy MCP calls. For every flow:

1. State the scenarios first (happy path, unavailable item, price change, checkout ambiguity).
2. Verify against real MCP responses, not mocked shapes you invented.
3. Run the end-to-end conversation for the flow before calling it complete. "It should work" is not evidence.

Anti-patterns: testing your own mocks, happy-path-only checks, and skipping the live run — the #1 cause of demo-day surprises.

## Working Style

- End substantive work with concrete `Next Steps:` — commands to run or things to verify.
- When docs and reality diverge, fix the doc — don't grow another one.
- No `git stash` — use branches or temporary commits.

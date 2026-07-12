# Track 03 · AI as Agency — rubric

← [Scoring framework](../04-scoring.md) | [Index](../README.md)

**164 base points + overflow (uncapped).** Root parameter: **working product shipping real output, 20x.**

A team of AI agents replaces a full human function. A manager agent plans, specialists execute, handoffs pass work between them, memory persists across tasks, and a control surface lets a non-engineer assign work. The framework: *if an agency was run with agents instead of humans, how would it work?*

## The parameters

### 1. Working product shipping real output — 20x · max 80 (root)
Real surface = a system a paying customer could use tomorrow. Staged WordPress or sandbox Gmail = L3 max. **Overflow past L5: +1 pt × 20x per additional real task completed autonomously during judging.**

| Level | Band | Meaning |
|-------|------|---------|
| L1 | Demo only, canned responses. 0 completed tasks | Agents talk through the workflow but complete no declared job; no usable output lands anywhere. |
| L2 | Under 30% task success | Crew executes but output is broken, fake, incomplete, or hallucinated. |
| L3 | 50–70% task success | Useful part of the job done; at least one usable artifact. Staged/sandbox/mocked surfaces cap here. |
| L4 | 70–85% task success | Most of the job across a realistic workflow, but a human approves every step; edge cases break it. |
| L5 | 85%+ across 3+ repeated runs | End to end on real live surfaces; escalates by exception only, handing edge cases to a human with full context. |

### 2. Agent org structure — 5x · max 20
How the agent team is organized. Flat vs managed, static vs dynamic delegation.

| Level | Meaning |
|-------|---------|
| L1 | One monolithic agent does everything. |
| L2 | 2–3 agents with hardcoded handoffs, no manager. |
| L3 | Clear roles (manager + specialists), static routing. |
| L4 | Dynamic: manager plans subtasks per request, delegates, reviews outputs. |
| L5 | Emergent org: manager spawns sub-specialists on the fly, agents escalate when stuck, roles self-adjust. |

### 3. Observability — 7x · max 28
Tool-agnostic. What a mentor can *see* about the system matters, not the logo.

| Level | Meaning |
|-------|---------|
| L1 | `console.log` / print statements only. |
| L2 | Structured logs written to a file, no UI. |
| L3 | Can pull up a specific run and see what each agent did, step by step (any tool). |
| L4 | Trace tree across agents (who called whom), token + cost per step, filter by agent/task. |
| L5 | Production-grade: diff two runs side by side, alerts on failure/cost spike, search across runs — a senior eng would trust it to debug prod. |

> Langfuse, Braintrust, OTel, a homebrewed dashboard over Postgres: all score the same at every L-tier. The question is not "what tool" but "what can we see about the system, and what can the team do with what they see?"

### 4. Evaluation and iteration — 5x · max 20
Ability to improve the system over time. Manual vs closed-loop.

| Level | Meaning |
|-------|---------|
| L1 | No evals — changes ship on vibes. |
| L2 | Manual spot-checks ("this run looked fine"). |
| L3 | Named eval set exists, run manually to compare versions. |
| L4 | Automated eval pipeline, CI-style, fails a release if quality drops. |
| L5 | Closed-loop: failed runs feed a growing eval set; version-controlled prompts/agents; measurable gains across versions. |

### 5. Agent handoffs and memory — 2x · max 8
Does context survive between agents and across tasks?

| Level | Meaning |
|-------|---------|
| L1 | Remembers nothing; every turn starts from zero. |
| L2 | Holds one or two basic fields within the task. |
| L3 | Holds context within a single task, lost at handoff. |
| L4 | Holds context across the task and one or two handoffs. |
| L5 | Full relevant history + policy knowledge (now + this user's past + business rules), survives all handoffs. |

### 6. Cost and latency per task — 1x · max 4
Lower tier (slower or more expensive) governs.

| Level | Bound |
|-------|-------|
| L1 | Over 30 min OR over $5 |
| L2 | 10–30 min OR $2–$5 |
| L3 | 5–10 min OR $0.50–$2 |
| L4 | 1–5 min OR $0.10–$0.50 |
| L5 | Under 1 min AND under $0.10 |

### 7. Management UI — 1x · max 4
L5 tested live: a non-eng volunteer onboards a new role unassisted.

| Level | Meaning |
|-------|---------|
| L1 | CLI or code only. |
| L2 | Basic web UI, dev-only. |
| L3 | Functional UI, a PM could operate with docs. |
| L4 | Clean UI, non-eng operates with one walkthrough. |
| L5 | Delightful UI: a non-eng volunteer defines a brand-new agent role (job, tools, guardrails) in under 10 min unassisted, and it works. |

## AI as Agency total
`80 + 20 + 28 + 20 + 8 + 4 + 4 = 164 base points.` Real-output overflow on top, uncapped.

## Power-ups
Same +25/partner table as every track — see [Scoring framework](../04-scoring.md#power-ups-same-on-every-track).

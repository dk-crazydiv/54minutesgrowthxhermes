# 04 · Scoring — framework

← [Index](README.md) | Prev: [Rules](03-rules.md) | Next: [Setup →](05-setup.md)

Your track's rubric, plus partner power-ups on top. One formula everywhere. This page is the framework; the per-track parameter tables live in their own files:

- [Track 01 · Virality](scoring-tracks/track-01-virality.md) — 164 base + overflow
- [Track 02 · Revenue](scoring-tracks/track-02-revenue.md) — 208 base + overflow
- [Track 03 · AI as Agency](scoring-tracks/track-03-ai-as-agency.md) — 164 base + overflow

## Eligibility — the only rule

Every team must use **Hermes** in at least one of two ways. **No Hermes, no score.** This is the only eligibility rule.

1. **As your coding partner.** Hermes built your product. Sessions, real prompts, receipts. Keep your session receipts so mentors have something to glance at.
   > *Example: Team Chai opens their Hermes session history: 41 prompts, a schema argument at 11:14, a refactor at 2 pm, commits authored mid-session. The mentor scrolls for thirty seconds, watches the product take shape prompt by prompt, and nods. Qualified.*
2. **As the base harness.** Your product runs on Hermes and your end users interact with it. Show at least one Hermes capability doing real work in your build.
   > *Example: TutorBot runs on Hermes. A judge texts it on Telegram from her own phone, it recalls her weak topics from yesterday's memory, and the 6 pm cron fires a revision quiz while everyone watches. Three capabilities, each doing real work for a real user.*

Either one qualifies. Doing both is allowed.

## Rubric 101 — L1 to L5

Every parameter is scored L1 to L5. A lens, not a spreadsheet you fill at the end. Apply the rubric to your own build as you go.

| Level | Name | Meaning |
|-------|------|---------|
| **L1** | Floor | Didn't attempt. 0 points. |
| **L2** | Baseline | Attempted. Missing the core. |
| **L3** | Working | Does what it claims. |
| **L4** | Strong | Real quality. Stands out in the zone. |
| **L5** | Exceptional | Reachable if you ship well. Overflow stacks on top. |

### The formula

```
points = (L − 1) × weight
```

The same everywhere. L5 on a 20x-weight parameter is 80 points. L3 on the same parameter is 40. **L1 is always 0** — participation does not score.

## How we verify

Numbers are verified, not trusted. Signups get checked in your database live, not on a screenshot. Traffic data gets cross-checked against signup data, and the two have to make sense together. Mentors are on the floor all day. And when something smells off, we go deeper: we call your customers, we email your signups and watch what bounces, and we run checks we do not publish. **A spoofed number zeroes the parameter.**

## The four things you can score

| Component | Value | What it is |
|-----------|-------|------------|
| **Core track base** | 164 to 208 | Your track's rubric, scored L1 to L5 across its parameters. |
| **Overflow** | Uncapped | Past the L5 ceiling on flagged parameters, every additional increment keeps paying. |
| **Power-ups** | +25 each | Flat 25 per partner, no cap. All six = 150. All five = 125. |
| **Cross-track bonus** | 50 cap | Wins in someone else's track at half weight. |

## Power-ups (same on every track)

Do the integration, earn the points: **+25 per partner, no cap.** All six = +150, all five = +125. Real use only — a mentor has to see it working in your build.

| Power-up | Points | Counts when | Evidence |
|----------|--------|-------------|----------|
| **Wispr Flow** | 25 | 500+ words dictated during the event | Wispr stats screenshot |
| **ElevenLabs** | 25 | Voice does real work in the product, not a dead snippet | Live demo of the interaction |
| **Convex** | 25 | Convex stores real product state or is the main backend | Repo + Convex dashboard |
| **Linkup** | 25 | Live search doing real work in the product | Code + live query |
| **Dodo Payments** | 25 | Live checkout in the product (an activated account alone earns nothing) | Dodo dashboard + live checkout |
| **Cloudflare** | 25 | Hosting, Workers, or any CF product doing real work | Live URL + CF dashboard |

## Cross-track bonus

You pick one track, but wins outside it still pay. Say you build an AI as Agency product and your launch takes off on social: those impressions and signups earn bonus points too, **at half the weight** they carry in their home track, **capped at 50 total.** Same proof required. Nothing is paid twice: if your own track already scores a parameter, there is no bonus on it.

| Source track | Parameter | Original weight | Bonus weight | Max bonus |
|--------------|-----------|-----------------|--------------|-----------|
| Virality | Signups | 25x | 12.5x | 50 |
| Virality | Visitors | 10x | 5x | 20 |
| Virality | Reactions + comments | 2x | 1x | 4 |
| Revenue | Signups | 20x | 10x | 40 |
| Revenue | Live product quality | 8x | 4x | 16 |
| Revenue | Revenue generated | 12x | 6x | 24 |
| AI as Agency | Real output shipping | 20x | 10x | 40 |
| AI as Agency | Observability | 7x | 3.5x | 14 |

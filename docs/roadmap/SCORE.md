# Score

Track: Revenue (208 base + overflow). This is the north star — every hour of work
should move a number on this page. Rubric: `growthx-handbook/scoring-tracks/track-02-revenue.md`.
Last honest count: 2026-07-12, before the four Telegram proofs landed.

## Eligibility

We qualify as **the base harness case** (rule 03, way 2): the product runs on Hermes
and end users talk to it on Telegram (@swiggy_mcp_buildathon_bot). To hold up in
judging, a judge must text the bot **from their own phone** and see at least one
Hermes capability do real work — a Zomato MCP call answering a real question is
enough. We also have session receipts as backup (way 1), but the harness case is
the one to demo. **No Hermes, no score** — so the gateway staying up through judging
is a scoring requirement, not an ops nicety.

## Where we are right now (verified only)

| # | Parameter | Weight | Level | Points | Evidence a judge sees |
|---|-----------|--------|-------|--------|----------------------|
| 1 | Signups | 20x | **L1** | **0** | Signup = email + first-use event in the product. Our 3 emails are landing-page drops — nobody outside the team has used the bot. That's waitlist, not signups. |
| 2 | Live product quality | 8x | **L2** | **8** | Bot is live, Zomato MCP proven read-only, but a cold user can't reach value unassisted yet — the four proofs in BACKLOG.md are still in flight. |
| 3 | Revenue | 12x | **L1** | **0** | $0. No payment rail exists. |
| 4 | Waitlist | 4x | **L2** | **4** | 3 real emails in Convex prod (cheerful-crow-656), live counter on https://zomato-companion.pages.dev. Judges check the DB live, so this number is safe. |
| 5 | Business impact | 4x | **L2** | **4** | Case exists in docs/idea.md but no math shown (metric + baseline + % movement). One paragraph fixes this. |
| 6 | Right to win | 2x | **L3** | **4** | Kartik is a heavy Zomato user with ~39 pages of order history wired into the build — real domain exposure, visible in the product. |
| 7 | Why now | 1x | **L4** | **3** | Zomato MCP is a months-old unlock; this product literally could not exist without it. Say that out loud in the demo. |
| 8 | Moat | 1x | **L2** | **1** | Thin. Order-history personalization is the story, but it's copyable. |

**Base: 24 points.**

Power-ups earning now: **Cloudflare +25** (Pages hosting, live URL) and
**Convex +25** (real product state, dashboard shows signups).

**Current total: ~74 points.**

## Power-ups — earning, cheap, and honest calls

| Power-up | Status | Call |
|----------|--------|------|
| Cloudflare | **Earning, +25** | Live URL + CF dashboard. Done. |
| Convex | **Earning, +25** | Repo + Convex dashboard with real signups. Done. |
| Wispr Flow | Cheap, +25 | On Kartik, zero code: dictate 500+ words today, screenshot the stats page. Start now, it accrues while we build. |
| ElevenLabs | ~1h, +25 | Voice order confirmation: bot sends a spoken final-bill voice note to Telegram before checkout. Real work, not a dead snippet, and it makes the demo better anyway. |
| Linkup | ~1–1.5h, +25 | Live search doing real work: bot pulls weather ("raining, order in before the surge") or restaurant news/reviews into the lunch-under-₹300 flow. One API call in the flow + a live query for the mentor. Zomato MCP alone doesn't count — the search has to be Linkup. |
| Dodo Payments | ~1.5h, +25 (+12 revenue if a stranger pays) | Honest path: a "Pro early access" tier (~$5) on the landing page via Dodo checkout. The +25 needs a **live working checkout** shown to a mentor — that we can do today. The revenue parameter is stricter: teammate/friend payments are L1 by rule, so revenue points only land if a real outsider pays. Ship the checkout for the power-up; treat any revenue as upside. |

All six live = +150. We're at +50.

## Next points, ranked by points per hour

| # | Move | Points | Effort | Risk |
|---|------|--------|--------|------|
| 1 | Wispr: Kartik dictates 500+ words, screenshots stats | +25 | ~0 (passive) | Only that he forgets. Start now. |
| 2 | Get 1–25 outsiders to actually use the bot (text it, get a reply) — signups L1→L2 | +20 | ~1h of DMs + making the bot safe for strangers (read-only answers, no checkout on other people's messages) | Bot must not expose Kartik's account data to strangers — scope replies. This is the root parameter; it's worth the care. |
| 3 | ElevenLabs voice confirmation in the checkout flow | +25 | ~1h | Low. Falls back to text if TTS fails. |
| 4 | Linkup live context in the lunch flow | +25 | ~1–1.5h | Low-medium. Must visibly do real work for the mentor. |
| 5 | Dodo live checkout on the landing page | +25 | ~1.5h | Account activation friction. Activated-but-unused earns nothing — the checkout must complete live. |
| 6 | Land the four Telegram proofs — quality L2→L3 | +8 | in flight | This is also the demo, so it's not optional; the points are a side effect. |
| 7 | Business-impact paragraph with real math (Kartik's own order spend as baseline) | +4 | 15 min | None. |
| 8 | Waitlist push in one real channel (LinkedIn/WhatsApp groups) — L2→L3 needs 51 emails | +8 | ~1h of posting | 51 is a stretch from 3; do it as a byproduct of the signups push, not instead. |
| 9 | Cross-track bonus: Virality **visitors** at 5x (our track doesn't score visitors) — needs traffic data that cross-checks against signups | up to +20 | free if #8 happens | Traffic without matching signups looks spoofed; only claim what the funnel supports. |

No cross-track bonus on signups or revenue — our own track already scores those, and
nothing pays twice. Overflow (uncapped) is flagged on signups (251+), revenue ($500+),
and waitlist (1,000+) — none are realistic today; ignore overflow.

## Realistic ceiling by 5:30 PM

Take moves 1–7: 74 + 25 + 20 + 25 + 25 + 25 + 8 + 4 = **~206**. Call it
**74 now → ~180–210 realistic**, with the swing riding on signups and the two
untested power-ups (Linkup, Dodo).

## Ways to score zero — read once

- **Spoofed numbers zero the parameter.** Signup emails get bounce-checked, traffic
  gets cross-checked, customers get called. Never inflate; 3 real beats 30 fake.
- **Team members don't count** as signups, waitlist, or revenue. Friend payments
  are explicitly L1.
- **Revenue removal test:** if the product vanished and the money would still have
  been paid, it doesn't count. No consulting, no manual work dressed as product.
- **Gateway down = no Hermes capability to show = no score.** Keep
  `scripts/telegram.sh status` green through judging.
- **Submit in the window** at growthx.club/hermes-buildathon/submit. Late = out,
  no appeals. Kartik submits the live URL early, not at 5:25.
- **Fresh-build rule:** we started today from scaffolding — fine. If anything feels
  borderline, flag it in the submission; hiding origins is auto-disqualification.
- **A demo video standing in for the live app counts as broken (quality L1).**
  The judge uses the real bot and the real page, from their device.

# Score

Track: Revenue (208 base + overflow). This is the north star — every hour should
move a number here. Rubric: `growthx-handbook/scoring-tracks/track-02-revenue.md`.
Last honest count: 2026-07-12 ~3 PM, on branch `3pmdemo`, ~2.5h to the 5:30 demo.

## Eligibility

We qualify as **the base harness case** (rule 03, way 2): the product runs on Hermes
and users talk to it on Telegram (@swiggy_mcp_buildathon_bot). A judge texts the bot
from their own phone and watches Hermes capabilities do real work — Zomato MCP calls,
memory, cron scheduling, web search, voice-note transcription. We can show five.
Session receipts exist as backup (way 1). **No Hermes, no score** — the gateway
staying up through judging is a scoring requirement.

## Where we are right now (verified only)

| # | Parameter | Weight | Level | Points | Evidence a judge sees |
|---|-----------|--------|-------|--------|----------------------|
| 1 | Signups | 20x | **L1** | **0** | Signup = external email + first-use event. Per-user OAuth onboarding was built and reverted (commit e6b3762) — the bot runs single-user on Kartik's Zomato account, so no outsider has a first-use event. Landing-page emails are waitlist, not signups. |
| 2 | Live product quality | 8x | **L3** | **16** | All four proofs work live: order history, stats from real history, a REAL order placed end-to-end (cart → confirm → checkout → UPI QR as a scannable Telegram photo), weather-aware personalized recs. Scheduled ordering via cron with a >20% price guard. 6/6 test suite in `tests/results.md` with session IDs. Persona hides internals. L4 is in reach if the demo runs clean — "noticeably better than the Zomato app" is a real claim when the QR lands in chat. |
| 3 | Revenue | 12x | **L1** | **0** | $0. No payment rail. Kartik's own order payment is his money, not revenue. |
| 4 | Waitlist | 4x | **L2** | **4** | 6 real emails in Convex prod — judges can hit https://cheerful-crow-656.convex.site/stats live. LinkedIn post is out; L3 needs 51. |
| 5 | Business impact | 4x | **L2** | **4** | Case is in docs/idea.md but still no math (metric + baseline + % movement). Still a 15-minute fix nobody has done. |
| 6 | Right to win | 2x | **L3** | **4** | Kartik's ~39 pages of real order history power the build; the stats and reorder flows only exist because of it. |
| 7 | Why now | 1x | **L4** | **3** | Zomato MCP is a months-old unlock; the product cannot exist without it. Say it in the demo. |
| 8 | Moat | 1x | **L3** | **2** | Workflow lock-in is now real: preferences persist in Hermes memory, history personalizes every answer, cron jobs live in the user's agent. Thin but live. |

**Base: 33 points.**

Power-ups earning now: **Cloudflare +25** (Pages, live URL) and **Convex +25**
(signups live in prod, verifiable endpoint). Still just those two.

**Current total: ~83 points.**

## Power-ups — status check

| Power-up | Status | Call |
|----------|--------|------|
| Cloudflare | **Earning +25** | https://zomato-companion.pages.dev + CF dashboard. |
| Convex | **Earning +25** | Live stats endpoint, repo, dashboard. |
| Linkup | **NOT earning yet** | Plugin is wired, `web.search_backend: linkup` is set — but without `LINKUP_API_KEY` it silently falls back to ddgs (docs/hermes/search-and-voice.md). ddgs answering is NOT Linkup doing real work; a mentor checking the code path would see the fallback. **Ask Kartik if the key landed in `~/.hermes/.env`; if yes, restart the gateway and run one live weather query — that's +25 in 15 minutes.** |
| ElevenLabs | Not earning | Voice notes IN work via faster-whisper (local STT) — that's Hermes, not ElevenLabs, and earns nothing on this row. The +25 needs ElevenLabs doing real work: e.g. the bot speaks the final bill as a voice note before checkout. ~1h. |
| Wispr Flow | Unknown, on Kartik | 500+ words dictated + stats screenshot. Zero code. If he's been dictating today it's already earned — get the screenshot. |
| Dodo Payments | Not earning | Needs a live completed checkout, not an activated account. ~1.5h for a "Pro early access" tier on the landing page. Tight against 2.5h; only start it after Linkup/ElevenLabs are done. |

## Next points, ranked by points per hour (~2.5h left)

| # | Move | Points | Effort | Risk |
|---|------|--------|--------|------|
| 1 | Wispr stats screenshot from Kartik | +25 | minutes if he dictated | Zero. Just ask. |
| 2 | Linkup key → restart gateway → one live query saved as proof | +25 | ~15 min if the key exists | Key may not exist; getting one takes signup time. Do it first, it's the cheapest code points on the board. |
| 3 | ElevenLabs spoken final-bill before checkout | +25 | ~1h | Low; falls back to text. Also makes the demo better. |
| 4 | Business-impact paragraph with real math (Kartik's own annual Zomato spend as baseline — the stats flow already computed it) | +4 | 15 min | None. |
| 5 | Quality L3→L4: rehearse the demo path twice, fix any rough edge a judge would hit cold | +8 | folded into demo prep | The 353s/504s wall times in tests are the risk — a slow flow in front of a judge reads as rough. Pre-warm sessions. |
| 6 | Dodo live checkout on landing page | +25 | ~1.5h | Account activation friction; abandoning it half-done earns 0. Only if moves 1–4 are banked by ~4:15. |
| 7 | Waitlist L2→L3 (51 emails) | +8 | passive — LinkedIn post is out, reshare in group chats | 6→51 in 2.5h is unlikely; don't spend build time on it. |
| 8 | Cross-track: Virality visitors at 5x (needs traffic data cross-checking with signups) | up to +20 | free byproduct of #7 | Only claim what CF analytics + Convex jointly support. |

**Dropped: the Signups L1→L2 play (+20).** Per-user OAuth is reverted; with a
single-user Zomato account, an outsider texting the bot has no honest first-use
event on the core flow. Re-opening onboarding in 2.5h risks the demo for 20 points —
not worth it. Signups stay 0; say so plainly if asked.

## Realistic ceiling by 5:30 PM

83 + 25 (Wispr) + 25 (Linkup) + 25 (ElevenLabs) + 4 (impact math) + 8 (quality L4)
= **~170**. Dodo lands it near **~195**. Call it **83 now → 150–170 realistic**,
swing riding on which power-ups actually cross the bar.

## Ways to score zero — read once

- **Gateway is a manual background process (PID 36340, not a service).** If the
  laptop sleeps or the shell dies during judging, there is no Hermes capability to
  show and the whole score is at risk. `bash scripts/telegram.sh status` before the
  demo, and again right before any judge touches the bot. `hermes gateway install`
  is 5 minutes of insurance.
- **Spoofed numbers zero the parameter.** Our waitlist endpoint is live-checkable —
  good. Never quote a number the judge can't pull themselves.
- **Team members and friends don't count** as signups, waitlist, or revenue.
- **Revenue removal test:** product gone = money gone, or it doesn't count.
  Kartik paying for his own tea order is not revenue.
- **A demo video instead of the live bot = quality L1.** The judge uses the real
  bot and the real page from their own device.
- **Submit in the window** at growthx.club/hermes-buildathon/submit — early, not
  at 5:25. Late = out, no appeals.
- **Don't claim Linkup while ddgs is answering.** A mentor who greps the fallback
  sees it in one minute, and a claimed-but-fake power-up smells like spoofing.

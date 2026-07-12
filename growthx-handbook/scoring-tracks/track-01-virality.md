# Track 01 · Virality — rubric

← [Scoring framework](../04-scoring.md) | [Index](../README.md)

**164 base points + overflow (uncapped).** Root parameter: **signups / meaningful actions, 25x.**

Narrative matters, platform does not: X, LinkedIn, YouTube, Instagram all count the same on impressions. **Ad-driven numbers are discounted to 25% of face value.** Four of the five parameters overflow: past the L5 ceiling, every additional increment adds points on top, uncapped.

## The five parameters

Each is scored L1→L5; `points = (L−1) × weight`.

### 1. Impressions and views — 1x · max 4
Weighted total: organic + (ads × 0.25), aggregated across all platforms.

| Level | Band | Meaning |
|-------|------|---------|
| L1 | Under 100 | The story never left the building. Whatever was posted reached almost nobody, or nothing was posted. Verified via native analytics on the builder's own device. |
| L2 | 101 to 1k | One or two posts; the builder's immediate (first-degree) network saw them. |
| L3 | 1k to 2.5k | Content escaped the first-degree circle — reach past the builder's own follower count. |
| L4 | 2.5k to 5k | The narrative found an audience beyond anyone the builder knows; at least one post clearly outperforms baseline. |
| L5 | 5k to 7.5k | Genuine distribution inside 8 hours; still climbing at judging. **Overflow: beyond 7.5k, +1 pt × 1x per additional 1,000 impressions.** |

### 2. Reactions and comments — 2x · max 8
Organic + (ad-driven × 0.25), aggregated across platforms.

| Level | Band | Meaning |
|-------|------|---------|
| L1 | Under 3 | Nobody responded (or only teammates, mentally excluded). |
| L2 | 3 to 10 | Courtesy engagement from the inner circle. |
| L3 | 11 to 25 | Actual responses from strangers — how-does-it-work comments, link requests. |
| L4 | 26 to 50 | Engagement has texture: substantive comments, tagging, a mini-discussion. |
| L5 | 51 to 100 | Comments section alive at judging; strangers answering each other. **Overflow: beyond 100, +1 pt × 2x per additional 10 reactions.** |

### 3. Amplification quality — 3x · max 12
Not volume — *whose* accounts reshared. Notable = 10k+ followers with domain authority.

| Level | Meaning |
|-------|---------|
| L1 | None outside the team engaged or reshared. |
| L2 | 1–2 peer builders commenting or liking. |
| L3 | 3+ peer builders engaging, or 1 sub-10k-follower founder/operator engaging. |
| L4 | 1 notable (10k+) founder or operator reshare. |
| L5 | Multiple notables engaging, a Product Hunt feature, press, or known investor amplification. |

### 4. Visitors to product — 10x · max 40
Unique visitors from Datafast (recommended), or PostHog, Plausible, GA4. **Read-only access required or capped at L2.**

| Level | Band | Meaning |
|-------|------|---------|
| L1 | Under 10 | Nobody clicked through, or no way to prove it (no analytics / no shareable dashboard). |
| L2 | 11 to 50 | A trickle of real outsiders — typically direct engagers from the launch post. |
| L3 | 51 to 250 | Distribution is converting. Watch the anti-spoof lens (see below). |
| L4 | 251 to 1,000 | Real traffic — hundreds of unique strangers, usually one breakout post or notable reshare. |
| L5 | 1,000+ | A genuinely viral day. Mentors audit rather than admire. **Overflow: beyond 1k, +1 pt × 10x per additional 100 visitors.** |

### 5. Signups or meaningful actions — 25x · max 100 (the heaviest virality parameter)
Signup, install, account creation, first-use event. Team members do not count. Anonymous visits do not count.

| Level | Band | Meaning |
|-------|------|---------|
| L1 | Up to 5 | Almost no one committed; after excluding team + venue friends there may be nothing left. |
| L2 | 6 to 25 | First real strangers converted — saw the story, clicked through, handed over an email / created an account. |
| L3 | 26 to 100 | Conversion at real volume. Anti-spoof: signups above 50% of unique visitors read as fabricated. |
| L4 | 101 to 250 | A breakout — over a hundred strangers in 8 hours. At 25x this level alone outscores maxing every other parameter, so mentors audit hard. |
| L5 | 251 to 1,000 | Hundreds of real users in a single day; funnel worked end to end. **Overflow: beyond 1k, +1 pt × 25x per additional 50 signups.** |

## Virality total
`4 + 8 + 12 + 40 + 100 = 164 base points.` Overflow uncapped.

## Anti-spoof checks (Virality only)
Two ratio checks run on every submission. When **both** flags trigger → manual review.

| Check | Ceiling | Consequence of breach |
|-------|---------|-----------------------|
| **Impressions → visitors** | 10% CTR max (1 visitor per 10 weighted impressions) | Visitors parameter drops to L1 (0 pts) unless the team proves a verifiable non-social traffic source. |
| **Visitors → signups** | 50% conv. max (1 signup per 2 visitors) | Signups parameter drops to L1 (0 pts) unless the team proves a verifiable direct-share source. |

## Power-ups
Same +25/partner table as every track — see [Scoring framework](../04-scoring.md#power-ups-same-on-every-track).

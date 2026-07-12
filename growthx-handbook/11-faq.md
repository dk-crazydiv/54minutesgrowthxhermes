# 11 · FAQ

← [Index](README.md) | Prev: [After](10-after.md) | Next: [Terms →](12-terms.md)

Questions builders usually ask. Read once at the start of the day. Check back when you hit an edge case.

## Format

**Can I build solo, or do I need a team?**
Either. Solo builders and teams of any size compete on the same rubric.

**Can I switch tracks after registration?**
No. The track you pick at registration is the rubric you're scored on. Wins in other tracks still pay through the cross-track bonus, so a strong build never wastes evidence.

**Can I use code I wrote before the event?**
Helper utilities, yes. An existing product, no. The thing you're scored on gets built today.

**Do I have to use Hermes?**
Yes. No Hermes, no score, and it is the only eligibility rule. Qualify in at least one of two ways: Hermes as your coding partner (with session receipts mentors can glance at), or Hermes as the base harness (with at least one capability doing real work in your build). Doing both is allowed.

## Scoring

**How do points actually work?**
Every parameter is scored L1 to L5, and `points = (L − 1) × weight`. So L5 on a 20x parameter is 80 points, L3 on the same is 40. On flagged parameters, overflow past L5 keeps adding points on top, uncapped.

**Why does scoring speed up past L5?**
On purpose. Past the ceiling, every point is verified evidence, and verified evidence keeps paying.

**How are signups verified?**
Numbers are verified, not trusted. Signups get checked in your database live, not on a screenshot, and traffic data gets cross-checked against signup data so the two make sense together. When something smells off we go deeper: we call your customers, we email your signups and watch what bounces, and a spoofed number zeroes the parameter.

**What trips the anti-spoof checks?**
On Virality, two ratios: more than 1 visitor per 10 weighted impressions, or more than 1 signup per 2 visitors. Breach one and that parameter drops to L1 unless you prove a verifiable non-social or direct-share source. Trip both and it goes to manual review.

**What counts as revenue?**
Money earned from selling the product, not your team's time. Consulting fees, done-for-you work, and payments from team members or friends do not count. The test: if you removed the product tomorrow, does the revenue also disappear? If yes, it counts.

**What is the cross-track bonus?**
Wins outside your track earn bonus points at half the original parameter weight, capped at 50 per team, with the same evidence bar as the primary track. You can never claim a bonus on a parameter your own track already scores. The same evidence is never paid twice.

## Partners & tools

**How do power-ups work?**
Every partner integration earns a flat +25, no cap. Real use only: a mentor watches it doing real work in your build, or it earns nothing. Stack all six = +150. Stack all five = +125.

**Does opening a Dodo Payments account count as the Dodo power-up?**
No. An activated account alone earns nothing. A live checkout in your product counts.

**Can I use my own LLM keys and other AI coding assistants?**
Yes. Bring whatever models and tools you like. Just remember the Hermes rule still has to hold for your build to be eligible.

## Demo & edge cases

**What if my demo fails on stage?**
Narrate what should be happening, recover, and move on. Judges have seen demos crash before, and how you recover matters more than the crash.

**What if my numbers come in after submission?**
Only what is verifiable at judging counts. A signup that lands after the check is a nice story, not a score.

**My starting point feels borderline. What do I do?**
Flag it to a mentor early and let them make the call. Hiding the origin of your build is automatic disqualification.

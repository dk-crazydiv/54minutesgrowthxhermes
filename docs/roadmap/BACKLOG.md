# Backlog

Work lives here. Finished lines get deleted, because git remembers them.
The product is the Swiggy Companion Agent (`docs/idea.md`). Everything here serves the demo.

## Now

- **Wire Swiggy/Zomato MCP into the Hermes bot and pick one.** Setup script and
  limits docs are in `scripts/setup-hermes-mcp.sh`, `docs/swiggy/`, `docs/zomato/`.
  Connect, call real tools, decide swiggy vs zomato by what actually works.
- **NL search + repeat order, live in Telegram.** "Find lunch under ₹300" and
  "repeat my last order" answering in chat against real MCP responses.
- **Cart prep + optimise + demo script.** Coupon/MOV math ("₹64 more for the coupon"),
  user approves before checkout. Then write the 4-minute demo script.

- **Context limits are a live concern.** Long Telegram threads + big MCP responses
  (Zomato tools.json is 5.5k lines) will blow the window. Keep tool output trimmed,
  and the user needs a fresh-chat command in Telegram to reset the session.

## Next

- **Submit the live URL.** Landing page is live at https://zomato-companion.pages.dev
  (Zomato-branded). Kartik submits it at growthx.club/hermes-buildathon/submit.
- **ElevenLabs power-up (+25).** Voice must do real work in the product — e.g. the bot
  sends a spoken order confirmation or ETA update. Needs a live demo for a mentor.
- **Wispr Flow power-up (+25).** On Kartik: dictate 500+ words during the event and
  screenshot the Wispr stats page. No code needed.
- **Calendar timing + stock-watch** — demo as extensions if time allows, not build targets
  until the three flows above run live.

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

## Next

- **Deploy the landing page.** `site/index.html` is built; blocked on `npx wrangler login`
  (Kartik). Then `npx wrangler pages deploy site --project-name swiggy-companion` and
  submit the URL at growthx.club/hermes-buildathon/submit.
- **Calendar timing + stock-watch** — demo as extensions if time allows, not build targets
  until the three flows above run live.

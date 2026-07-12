# Backlog

Work lives here. Finished lines get deleted, because git remembers them.
The product is the Zomato Companion Agent (`docs/idea.md`). Everything here serves the demo.

## Now — prove these over Telegram, in order

Each one is a real message from Kartik to @swiggy_mcp_buildathon_bot, a real Zomato
MCP call, and a screenshot-worthy reply. Watch it live on the debug dashboard
(`python3 scripts/debug-dashboard.py` → http://127.0.0.1:8787).

1. **"Show my order history."** Baseline proof the Telegram → Hermes → Zomato path
   works end-to-end. Paginate — history is ~39 pages, never pull it all.
2. **"Tell me something interesting about my ordering."** Stats/facts mined from
   history: most-ordered dish, total spent this year, longest streak, most-loved
   restaurant. This is the wow that sells the landing page's promise.
3. **"Order my most-loved ice cream." — actually place it.** Find it from history,
   build the cart, show the final bill, Kartik confirms, checkout (UPI QR comes back).
   **Cancellation caveat (tell the user BEFORE they confirm):** the Zomato MCP has
   NO cancel/refund tools — cancelling means the Zomato app, and Zomato's free-cancel
   window is roughly 60 seconds / until the restaurant accepts. After that it's paid
   for and coming. The agent must say this at confirmation time.
4. **"Get me lunch under ₹300 before my next meeting."** NL search + offer math +
   timing in one flow — the demo-script centrepiece.

Domain rules still hold: final bill shown before checkout, Kartik confirms, never
retry checkout blind, one restaurant per cart, server's final_amount is authoritative.

## Next

- **Submit the live URL.** Landing page is live at https://zomato-companion.pages.dev.
  Kartik submits it at growthx.club/hermes-buildathon/submit.
- **4-minute demo script** built from whichever of the four proofs land cleanest.
- **ElevenLabs power-up (+25).** Voice doing real work — e.g. spoken order confirmation.
- **Wispr Flow power-up (+25).** On Kartik: dictate 500+ words during the event,
  screenshot the Wispr stats page.
- **Calendar-aware timing** as a demo extension if time allows.

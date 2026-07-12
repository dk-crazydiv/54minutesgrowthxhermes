# Swiggy Companion Agent

## What it is

A lightweight companion agent built on Hermes and Swiggy MCP that helps users complete food and grocery tasks faster through conversation.

Instead of opening Swiggy, searching manually, comparing options, checking order value, tracking unavailable products and reviewing the cart, the user can simply ask the agent.

Examples:

* “Order my usual breakfast.”
* “Find lunch under ₹300 before my 1 PM meeting.”
* “Add the groceries I normally buy every week.”
* “Tell me when this product is back in stock.”
* “How much more do I need to add for this offer?”
* “Show me cheaper alternatives.”
* “Repeat my last order.”
* “Track my current order.”

The agent acts as a faster conversational layer over Swiggy.

## Why it is useful

Ordering on food and grocery apps often involves several repeated steps:

1. Open the application.
2. Search for an item.
3. Choose a restaurant or product.
4. Check delivery time.
5. Compare prices.
6. Add items to the cart.
7. Check coupons and minimum order value.
8. Complete checkout.
9. Track the order.

The companion agent reduces this into one or two messages.

The main value is not complex prediction. It is:

* Faster ordering
* Fewer clicks
* Better use of order history
* Faster repeat purchases
* Easier cart management
* Context-aware recommendations
* Proactive reminders and alerts

## Core features

### 1. Quick repeat ordering

The user can repeat previous Food or Instamart orders without searching again.

Examples:

* “Repeat yesterday’s lunch.”
* “Order the same groceries as last Sunday.”
* “Add my usual milk, eggs and bread.”

### 2. Natural-language search

The user can describe what they need instead of navigating filters.

Examples:

* “Find a vegetarian dinner under ₹350.”
* “Show me quick breakfast options.”
* “Find a one-kilogram rice pack from my usual brand.”
* “Show restaurants delivering within 30 minutes.”

### 3. Meeting-aware ordering

The agent can read the user’s calendar and help time the order.

Examples:

* “I have meetings from 12 to 2. Get lunch before that.”
* “Find something that arrives before my next call.”
* “Remind me to order after this meeting.”

The calendar is used only to make ordering faster and more convenient.

### 4. Monthly budget awareness

The user sets a monthly Food and Instamart budget.

The agent can then say:

* “You have ₹2,400 remaining this month.”
* “This order is above your usual meal budget.”
* “Here are three cheaper alternatives.”
* “This cart keeps you within your weekly limit.”

The budget feature helps guide the order but does not block the user.

### 5. Back-in-stock monitoring

When an Instamart product is unavailable, the user can ask the agent to watch it.

Flow:

Unavailable product
→ scheduled availability checks
→ product becomes available
→ user receives an alert
→ agent prepares the cart
→ user confirms checkout

This will likely require periodic checking because there may not be a native back-in-stock event or webhook.

### 6. Pending order-value assistant

The agent checks whether the user is close to:

* A coupon threshold
* Minimum order value
* Free delivery
* A configured cart budget

Examples:

* “You need ₹64 more to use this coupon.”
* “Adding ₹90 only saves ₹50, so it is not worth it.”
* “Adding eggs unlocks the offer and you usually buy them anyway.”
* “Remove this item to stay under ₹500.”

### 7. Smart substitutions

If a product or dish is unavailable, the agent can suggest alternatives.

It can prioritize:

* Same brand
* Similar pack size
* Similar price
* Previous purchases
* User preferences

### 8. Cart preparation

The agent can prepare the cart and show:

* Items
* Quantities
* Substitutions
* Delivery estimate
* Coupon impact
* Total order value

The user gives final approval before the order is placed.

### 9. Order tracking

After checkout, the same conversation can be used to:

* Check order status
* Check delivery ETA
* View order details
* Identify delays

## Simple user experience

The agent can work through Telegram, WhatsApp, Slack, a web chat or the Hermes interface.

Example conversation:

User:

“Get me lunch before my 1 PM meeting. Keep it under ₹300.”

Agent:

“You have a meeting from 1 PM to 2 PM. I found three options that should arrive before 12:45:

1. South Indian meal — ₹245
2. Rice bowl — ₹279
3. Veg thali — ₹290

Which one should I add?”

User:

“Rice bowl.”

Agent:

“Added. Your total is ₹279. A coupon requires ₹349, but adding another item would cost more than the saving. Proceed with ₹279?”

User:

“Yes.”

The companion agent then places and tracks the order.

## Core architecture

User
→ Hermes companion agent
→ Swiggy MCP
→ Food, Instamart and Dineout

Optional supporting integrations:

* Google Calendar
* Weather
* User budget storage
* Scheduled checks
* Preference memory

## Recommended hackathon scope

Build the smallest useful version with these five flows:

1. Search through natural language
2. Repeat a previous order
3. Prepare and optimise a cart
4. Use calendar context to time an order
5. Watch an unavailable Instamart product

Additional features can be shown as extensions rather than fully built.

## Main limitations

* Food and Instamart use separate carts and transactions.
* Scheduled ordering may need to be handled by Hermes rather than Swiggy.
* Back-in-stock monitoring may require periodic polling.
* Prices and availability can change between search and checkout.
* Checkout must not be retried blindly because duplicate orders may occur.
* Final transaction approval should remain with the user.
* Nutrition and health information may not be consistently available.
* Monthly budget calculations depend on the order history available through the integration.

## One-line pitch

Swiggy Companion is a conversational Hermes agent that helps users search, repeat, optimise, place and track Swiggy Food and Instamart orders with fewer steps.

## Shorter pitch

Order from Swiggy without navigating Swiggy.



## Decision: Zomato is the build target; Swiggy is reference-only

Decided 12 Jul 2026 by the team after live probes on real accounts (measured data in
`docs/zomato/mcp-limits.md` and `docs/swiggy/`). Supersedes the earlier Swiggy-first
draft from the same day.

**Why Zomato:**

- **Search is a one-call answer.** "Find chicken biryani under ₹300, rated 4.3+"
  returns dishes with exact prices, orderable variant_ids, restaurant rating/votes,
  ETA and distance in a single filtered call (8 working filter knobs). Swiggy has no
  filters at all and its dish search only works scoped to one restaurant — flow 1
  would be a hand-built fan-out pipeline, with 40% ads in results.
- **Lifetime order history** (verified back to the account's first order, 2017) —
  "repeat my usual" is grounded in real evidence of what "usual" means, and enables
  eating-pattern/budget features. Swiggy shows only the last 5 orders.
- **Better checkout and auth for a live demo:** UPI QR mid-chat or COD, no order-value
  cap observed, refresh tokens (no mid-hackathon re-login).
- **Richer menu data:** variants, addons, veg/spicy tags, populated nutrition
  (protein/calories/health score), and built-in personalization signals.

**Known Zomato costs we accept (and design around):**

- **Food delivery only — and that's the product now.** The grocery/Instamart flow
  (back-in-stock watch) is cut entirely; hackathon scope is the four food flows
  (search, repeat, cart optimise, calendar timing). Lifetime-history features
  (eating patterns, budget) are demo-able extensions.
- **Repeat-order needs re-resolution:** history has no per-item prices and dates omit
  the year — rebuilding a cart means resolving items against the live menu.
- **README says personal use/testing only** — fine for a buildathon demo, but nothing
  we build can ship publicly without Zomato's developer-access approval.
- Pagination cursors must be double-encoded; search pages are heavy (use page_size 3–5);
  per-dish ratings are always 0; fees only appear on a live cart.

**What Swiggy remains for:** reference and comparison. The research in `docs/swiggy/`
stays current as of 12 Jul 2026; no further Swiggy build work is planned.

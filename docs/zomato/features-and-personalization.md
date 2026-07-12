# Zomato Companion — Features, Personalization & Insights Catalog

Grounded catalog for the Zomato Companion agent (Hermes on Kartik's Telegram). Every idea
names the tools/data it needs; everything must trace to the 11 Zomato MCP tools
(`docs/zomato/mcp-limits.md`, `tools/tools-digest.txt`) plus Hermes built-ins (cron,
MEMORY.md/USER.md memory, Telegram, Google Calendar MCP). Personal stats computed
12 Jul 2026 from the full export `data/order-history-full-2017-2026.json` (777 orders).

Hard constraints respected throughout: history carries **totals only** (no per-item
prices), order dates **omit the year** (anchor via date windows / cursor epoch),
`dietary_tag` is `"undefined"` pre-2020, no delivery fees before a live cart, per-dish
ratings are always 0 on search/menu, personal-use-only per Zomato README, and the user
always confirms before checkout.

---

## The real numbers (Kartik's export — doubles as demo material)

All 777 orders are Delivered. Year assignment for 2023+ is reliable (dense data,
rollover-detected); the ~18 sparse pre-2023 orders actually span 2017–2022 (first order
5 Jul 2017 per mcp-limits.md) but calendar-rollover detection compresses them — use the
cursor epoch or date-window queries when a pre-2023 year matters.

**Spend & volume**
- Lifetime spend: **₹2,50,942** across 777 orders · avg **₹323** / median **₹268** · max ₹3,260 (The Masala Story)
- By year: 2023 = 329 orders/₹95,954 · 2024 = 220/₹76,630 · 2025 = 153/₹51,693 · 2026 YTD = 57/₹20,793
- Avg order value climbing: ₹292 (2023) → ₹348 (2024) → ₹365 (2026)
- Last-12-months run rate ≈ ₹3,200/month, ~10 orders/month (peak 2023: 4.2 orders/week)

**Restaurants** (169 distinct; 90% of orders are at repeat restaurants)
- Top: Mumbai Tiffin 55×/₹13,660 · Truffles 54×/₹21,114 · Meghana Foods 33×/₹12,421 · FreshMenu 30× · California Burrito 26× · Szechuan Dragon 25× · Dietboite 25× · Al Daaz 24× · McDonald's 23× · La Pino'z 18×
- 2026 tastes shifted: Al Daaz (10×) and Meghana Foods (8×) lead; Mumbai Tiffin last ordered 14 Apr 2025, Truffles 6 Aug 2025 — old favorites gone quiet.

**Dishes** (most-ordered items)
- Pulka 72 · Plain Chapati 30 · Crispy Mushroom Rice Bowl (Mini) 27 · Chicken Grilled Salad 26 · Butter Cube 22 · Phulka 21 · Paneer Biryani 20 · Rumali Roti 17 · Premium Phulka Thali 15 · Chicken Cheese Sandwich 15

**Diet** (item-level tags, post-2020): **veg 897 (77%) · non-veg 233 (20%) · egg 15 · undefined 26** — a mostly-veg eater whose non-veg is concentrated in biryani/steak/shawarma.

**When**
- **59% of orders land 12:00–15:59; single biggest hour is 14:00 (194 orders)** — this is a lunch account. Dinner (19–22h) is 25%.
- Days are flat Mon–Sat (~105–112 each); **Sunday is the peak (128)** and Sunday skews indulgent: Meghana Foods 18×, McDonald's/La Pino'z/Al Daaz.
- Longest recent gap: 12 Jun → 7 Jul 2026 slow-down (June: only 5 orders/₹1,389 — lowest month in 12).

**Price trends from single-item repeat orders** (order total as dish-price proxy — only valid when the order had exactly one item, qty 1):
- Dietboite Chicken Grilled Salad: 21 orders, ₹278 (Jan 2025) → ₹283 (Apr 2026)
- Meghana Chicken Boneless Biryani: 11 orders, ₹400 (Jun 2024) → ₹411 (Apr 2026)
- Meghana Paneer Biryani: 17 orders, ₹366 → ₹339 (got cheaper)
- California Burrito Mushroom Rice Bowl: 18 orders, ₹212 → ₹204

---

## Tier 1 — Core-flow enrichers (the four flows: search, repeat, cart optimise, calendar timing)

| Idea | What it does | Tools/data | Effort |
|---|---|---|---|
| **"My usual" resolver** | "Order my usual lunch" → history shows Mumbai Tiffin thali / Dietboite salad / CB rice bowl by frequency+recency; re-resolve items against live menu (history has no item prices), build cart, confirm. | `get_order_history` (search_query) → `get_menu_items_listing` → `get_restaurant_menu_by_categories` → `create_cart`; USER.md caches the resolved variant_ids | M |
| **One-call filtered search** | "Chicken biryani under ₹300 rated 4.3+" answered in one `get_restaurants_for_keyword` call — exact prices, variant_ids, rating/votes, ETA, distance. Use `page_size` 3–5 (10-result pages ≈ 67KB). | search tool, 9 filter knobs | S |
| **Cart truth pass** | Before confirmation always rebuild via `create_cart` and show server `final_amount` (authoritative — fees/taxes only exist here), never search-time prices. | `create_cart` | S |
| **Offer optimiser** | After cart creation, run `get_cart_offers`; compute "add ₹X to unlock code Y saving ₹Z — worth it?" using min-order-value + max-cap fields. Suggest a filler item from his repeat list (Pulka ₹—, Butter Cube). | `get_cart_offers`, `create_cart` (promo_code), history for filler candidates | M |
| **Calendar-aware timing** | "Lunch before my 1 PM call" → read calendar, filter by `near_and_fast=True` / "under 40 minutes" keyword, compare `res_ddt` ETA vs meeting start. | Google Calendar MCP, search ETA fields | M |
| **Preference defaults in USER.md** | Persist: veg-first (77% veg), lunch ≈ ₹280–350 budget, saved address_id, payment habit (still always *ask* payment method — tool guardrail), spice/addon habits (362 items ordered with addons). | Hermes memory, history | S |
| **Checkout safety** | Show full bill, explicit confirm, UPI QR into Telegram or COD; on ambiguous checkout error check `get_order_tracking_info` before any retry (duplicate-order rule). | `checkout_cart`, `get_order_tracking_info` | S |

## Tier 2 — Demo-able extensions (cheap, high wow)

| Idea | What it does | Tools/data | Effort |
|---|---|---|---|
| **"Zomato Wrapped" spend report** | On demand (or monthly cron): "₹2.5L lifetime, ₹95K in 2023 alone; your avg order rose ₹292→₹365; June 2026 was your cheapest month in a year." Pre-computed from the export; refresh via date-window history calls. | history + date filters, cron, Telegram | S |
| **Budget tracker** | User sets monthly budget in USER.md; agent sums current-month totals via `start_date`/`end_date` and warns at cart time: "This ₹411 biryani takes you to ₹3,650 of your ₹4,000." Suggestive, never blocking. | history date filters, memory, `create_cart` | S |
| **Dish price-watch** | For his single-item repeats, track order-total drift (salad +₹5, chicken biryani +₹11, paneer biryani −₹27) and check live menu price before reorder: "Paneer Biryani is ₹339 today, cheaper than your last order." | history (single-item totals) + `get_restaurant_menu_by_categories` live price | S |
| **Deal hunter** | "Anything good on sale?" → `flash_sale=True` / `offers_tag=DOTD/BOGO/GOLD` searches scoped to his 169 known restaurants first. | search filters + history | S |
| **Order tracking notifier** | After checkout, Hermes cron polls `get_order_tracking_info` and pushes status + rider name/phone/rating + chat deeplink to Telegram; flags stalls. | tracking tool, cron, Telegram | M |
| **Sunday-treat suggester** | Cron Sunday ~13:00: "It's Sunday — Meghana day (18 of your Sundays)? Chicken Boneless Biryani was ₹411 last time." One-tap into the repeat flow. | cron, history, search/menu | S |
| **"You've gone quiet on…" re-discovery** | Surface lapsed favorites: "55 orders from Mumbai Tiffin but none since Apr 2025 — back on the rotation?" Plus `new_for_you_filter=True` for genuinely new options. | history recency, search filter | S |
| **Protein/nutrition-aware picks** | For his Chicken Grilled Salad habit: `get_menu_items_listing`'s `partial_menu` returns populated `health_info` (protein/calories/health score) + `por_text` ("You ordered 17 months ago"). "Highest-protein lunch under ₹300 at Dietboite." Caveat: zeroed on search surface; only reliable via menu-listing partial_menu. | menu tools (health_info) | M |

## Tier 3 — Later / moonshots

| Idea | What it does | Tools/data | Effort / risk |
|---|---|---|---|
| **Weekly meal planner** | Plan Mon–Fri lunches from his rotation within budget; queue one confirm-to-order prompt per day at ~13:30 via cron. Still one user approval per order — never auto-checkout. | cron, memory, full order loop | L |
| **Veg-streak / eating-pattern coach** | Diet nudges from dietary_tag stream (77% veg): streaks, "3rd non-veg this week". Tags only post-2020; framing must stay non-judgmental. | history dietary tags, memory | M |
| **Price-drop watch on favorites** | Daily cron re-checks menu price of his top 10 dishes; alert on drop or flash sale. Human-ish call volume only (Akamai ceiling). | cron, menu tools | M |
| **Group/large-order concierge** | "Ordering for 6" — scale from his ₹3,260 Masala Story precedent, gourmet filter, offer optimisation. No cap observed on order value. | search (is_gourmet), cart, offers | L |
| **Multi-address awareness** | History is account-wide but `res_ddt` recomputes per address — "your office address gets Truffles in 25 min vs 50 at home." | `get_saved_addresses_for_user`, search per address | M |
| **Year-true archive** | One-time backfill assigning exact years to all 777 orders via per-year date-window queries (fixes the pre-2023 compression); unlocks true 2017–2022 nostalgia stats. | history date filters, ~10 calls | S |

**Explicitly not possible** (don't pitch): per-item price history (totals only), review-text mining, catalog/market crawls, card/wallet payments, cancellations/refunds, anything non-food, public distribution (personal use only).

---

## Personalization data model (what lives in Hermes memory)

- `USER.md`: saved address_id(s); veg-first preference; lunch window 13:00–15:00; per-meal budget ≈ ₹350; monthly budget if set; payment preference note (still ask each time).
- `MEMORY.md`: resolved variant_id map for top ~10 usual dishes (avoids re-resolving menus every reorder — but re-verify price/availability at cart time, menus drift); computed stats snapshot + date; lapsed-favorite list.
- Refresh strategy: stats recomputed from live `get_order_history` with `start_date`/`end_date` windows (year-anchoring trick) rather than re-exporting 39 pages.

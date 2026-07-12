# Zomato MCP — Capabilities & Limits

Verified 12 Jul 2026 against the live server (`ZomatoMcpServer v3.1.0`) via authenticated `tools/list` dump + empirical read-only probes on a real account. Full HTML report: https://claude.ai/code/artifact/46ef0bd4-539d-42fa-a28c-b83d65c948db

## Quick answers (O(1) lookup)

Zomato publishes no limits doc — everything below is empirically measured (12 Jul 2026) or from live tool schemas ([`tools.json`](./tools.json)).

| Question | Answer | Source |
|---|---|---|
| Rate limit? | **None hit** at ~125 req/min sequential + 10 parallel + ~200/session; Akamai bot mgmt is the real ceiling — keep human-ish volumes | measured |
| Oldest order? | **Lifetime** — first order ever (2017 on this account), no cutoff | measured |
| Full history export? | Yes — 777 orders / 39 pages / ~50 s on this account | measured |
| History page size? | Fixed 20/page; search default 10 (`page_size` settable) | measured + schema |
| Refresh tokens? | **Yes** (unlike Swiggy v1.0) | OAuth flow |
| Payment? | **UPI QR or COD only** — no cards/wallets | tool schema |
| Order value cap? | None observed | measured |
| Latency? | 0.25–0.5 s light tools; 0.9–1.9 s search/history pages | measured |
| Cancel/refund tools? | **None** | tools/list |
| Verticals? | Food delivery only | tools/list |
| Per-item prices in history? | **No** — totals only; item dates omit the year | measured |
| Pagination gotcha? | Double-encode `postback_params` (`json.dumps` twice) or Pydantic rejects it | measured |
| Third-party use allowed? | **No** — personal use/testing only per README | official README |

## Server

| Server | Endpoint | Tools |
|---|---|---|
| Zomato (food delivery only) | `POST https://mcp-server.zomato.com/mcp` | 11 |

- OAuth 2.0 + PKCE, dynamic client registration, **refresh tokens supported**. Scopes: `mcp:tools`, `mcp:resources`, `mcp:prompts`.
- Officially whitelisted redirect URIs: Claude, ChatGPT, VS Code, Postman — but localhost worked in practice via dynamic registration (`mcp-remote`).
- Protocol: MCP 2025-03-26, Streamable HTTP (SSE responses). Ships 4 `ui://mcp-app/*` HTML widgets (search/menu/cart). Prompts list empty.
- README states **third-party apps not currently permitted** (personal use/testing only; developer-access form: forms.eternal.com/form/ja8hap2tpm).

## 1. Query rate limits (measured)

| Aspect | Measured |
|---|---|
| MCP-layer rate limit | **None hit** — 40 sequential calls in 19 s (~125 req/min) + 10 fully parallel + ~200 calls/session, all 200 OK |
| Rate headers / 429s | None observed |
| Latency | 0.25–0.5 s light tools (addresses); 0.9–1.9 s history/search pages |
| Practical ceiling | Akamai bot management upstream — keep to human-ish volumes, no scraping-scale traffic |

## 2. Data recency / history depth (measured)

| Aspect | Measured |
|---|---|
| Oldest reachable order | **Account's first order ever — 5 Jul 2017** (9 years back). No retention cutoff. |
| Full export | 777 orders / 39 pages / ~50 s (this account) |
| Page size | Fixed 20 orders/page (history); search default 10/page (`page_size` settable) |
| Scoping | **Account-wide, NOT per-address** — despite the tool description, any valid `address_id` returns the same history |
| Filters | `search_query` (restaurant/dish name), `start_date`/`end_date` (`YYYY-MM-DD`) — both work down to single-year windows |

## 3. Data available per entity

| Entity | You get | You don't get |
|---|---|---|
| Past order | order_id, res id/name/address, items (name, qty, **veg/non-veg dietary tag**, addons), total paid (₹ string), status, date, image, reorderable flag | **Per-item prices, fees/taxes, delivery time; item dates omit the year** (anchor via date windows or cursor epoch) |
| Restaurant (search) | res_id, chain_id, rating + votes, distance, ETA, offer text, serviceability, matching dishes inline with variant ids + prices | Review text, rating distribution, city catalog dumps |
| Menu item | price, discounted price, variants (`v_…`) with per-variant pricing, addon groups (`ctl_…`, min/max selection), tags, categories, per-dish rating + review count, image, nutrition fields (calories/macros/health score — often zero/unpopulated) | — |
| Cart (new) | Full charge breakdown w/ taxes, item_total, final_amount (authoritative), promo discount, ETA, blocked payment types, shareable link | — |
| Offers | code_name, value, discount_type, max cap, min order value, recommendation status (via `get_cart_offers`) | — |
| Live tracking | All active orders: status, rider name/phone/rating/deliveries, chat deeplink, unread chat count | — |
| User | Saved addresses (id + name; searched addresses can include lat/lng + city cells), phone binding via OTP | Other users' data, Gold membership state |

## 4. Hard transactional limits

| Limit | Value |
|---|---|
| Payment | **`upi` (QR code returned at checkout) or `cash_on_delivery` only** — no saved cards/wallets; payment never flows through the client |
| Cart | One restaurant per cart; exactly one variant per item; server `final_amount` authoritative (never recompute) |
| Location | Saved `address_id` only — raw lat/long explicitly forbidden. India only. |
| Search | Intent/keyword search only (9 filter knobs: price range, min_rating 0–5, distance km, gourmet, new-for-you, near_and_fast, flash_sale, offers_tag ∈ default/DOTD/GOLD/BOGO) — no catalog crawl primitive |
| Verticals | Food delivery only — no Dineout/District/Blinkit |
| Cancellations/refunds | No tools |
| Guardrails (in tool descriptions) | Always ask user for payment method; show bill before checkout; confirm before placing order |

## 5. Key gotchas

- **Pagination bug**: echoing `postback_params` verbatim fails — the FastMCP layer auto-parses JSON-looking strings into dicts, then Pydantic rejects ("expected string, got dict"). Fix: **double-encode** (`json.dumps(postback_params)`) so one parse still yields a string. Applies to both history and search pagination.
- History `request_type` must be `"initial"` then `"load_more"` with `has_more: true` echoed.
- History response nests under `order_history`: orders live at `order_history.order_history_items`, next to `has_more` and `postback_params` (verified 12 Jul on Kartik's account: 122 orders / 7 pages — page counts vary by account; full dump in `users/kartik/history.csv`).
- Order dates come without a year (`"11 Jul, 2:45PM"`); the pagination cursor carries `last_created_timestamp.seconds` (epoch) — use it or date windows to assign years.
- Search results lazily omit heavy fields (`variants: "NOT_RETRIEVED"`, `all_addons_data: "NOT_RETRIEVED"`) — fetch the menu tools for full detail.
- Tool IDs vocabulary: restaurants `res_id` (int) / `chain_id`; variants `v_…`; add-ons `ctl_…`; carts `cart_id`.
- `bind_user_number` / `bind_user_number_verify_code` exist for phone+OTP binding (status enum {1,2,3}).
- Old orders (2017–2019 era) return `dietary_tag: "undefined"` — the veg/non-veg tag is only populated on recent orders.
- Cross-address history is identical except `res_ddt` (delivery ETA), which is recomputed relative to the queried address.
- Date-filtered responses can return all matches in one page with `has_more: false` and an empty `last_created_timestamp: {}` in postback — dates still omit the year, so anchor years from the window you asked for.
- Search (verified 12 Jul): the 9 filter knobs work empirically (min_rating dropped low-rated results; max_price restricted inline dishes to min_price ≤ threshold). One search call returns dish candidates with exact prices + variant_ids + restaurant rating/votes/ETA/distance/offer text. Caveats: a default 10-result page is ~67KB (blows tool-output limits — use `page_size` 3–5); per-dish `rating`/`reviews` are always 0 on the search/menu surface; no delivery-fee or promoted flags pre-cart; distance/time constraints can also be embedded in the keyword itself.
- `get_menu_items_listing` bonus: its `partial_menu` (~10 recommended items) comes in full detail including populated `health_info` (protein/carbs/calories + score) and personalization (`por_text`: "You ordered 17 months ago") — the nutrition fields that are zeroed on search are real here.

## 6. The 11 tools

| Tool | Required params | Purpose |
|---|---|---|
| `get_restaurants_for_keyword` | address_id, keyword | Search (keyword/cuisine/restaurant; filters; pagination) |
| `get_menu_items_listing` | res_id, address_id | Dish→category index (lightweight) |
| `get_restaurant_menu_by_categories` | res_id, categories, address_id | Deep menu: variants, addons, nutrition |
| `get_saved_addresses_for_user` | — | Saved addresses (only way to get address_id) |
| `bind_user_number` | phone_number | Send OTP to bind phone |
| `bind_user_number_verify_code` | auth_packet, code | Verify OTP |
| `create_cart` | res_id, items, address_id, payment_type | Priced cart (promo_code, delivery_instruction optional) |
| `get_cart_offers` | cart_id, address_id | Applicable promos |
| `checkout_cart` | cart_id | Place order; returns UPI QR image |
| `get_order_history` | address_id | Lifetime history; search + date filters + cursor pagination |
| `get_order_tracking_info` | — | All active orders + rider info |

Full JSON schemas: [`tools.json`](./tools.json) · human-readable digest: [`tools-digest.txt`](./tools-digest.txt)

## 7. Build implications

**Feasible:** personal spend/eating analytics (9-year history with dietary tags + totals), "reorder my usual" agent, deal/budget hunter (flash_sale/BOGO/DOTD filters + cart offers), nutrition-aware ordering (where populated), order-tracking notifier with rider chat deeplinks, full end-to-end ordering loop (UPI QR / COD).

**Blocked:** market/competitor analytics (no catalog dumps, no review text, own-address-relative search only), per-item price history (past orders carry totals only), card/wallet payments, anything beyond food delivery, and — legally — any third-party distribution (personal use only, per Zomato README).

## Zomato vs Swiggy (headline differences)

| Dimension | Zomato | Swiggy Food |
|---|---|---|
| Order history | **Lifetime (2017→now measured)** | Last 5 orders incl. delivered (Instamart: 15 days) |
| Payment | UPI QR + COD | COD only (< ₹1,000 cap) |
| Order value cap | None observed | < ₹1,000 beta cap |
| Verticals | Food only | Food + Instamart + Dineout |
| Rate limits | None hit (~125/min OK) | None now; 120/min planned v1.x |
| Refresh tokens | Yes | Not until v1.1 |

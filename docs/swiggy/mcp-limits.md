# Swiggy MCP — Capabilities & Limits

Researched 12 Jul 2026 from Swiggy Builders Club docs v1.0 (`mcp.swiggy.com/builders/llms-full.txt`) plus live unauthenticated probes. Full HTML report: https://claude.ai/code/artifact/089a3d30-6db9-4adc-9ed7-e3050fcf13c7

## Quick answers (O(1) lookup)

| Question | Answer | Source |
|---|---|---|
| Rate limit today? | **None** (abuse shed upstream as 5xx) | official docs + live burst test |
| Rate limit planned? | 120 req/min/user/server; write tools 30/min; burst 2× over 10 s; 429 + `Retry-After` | official docs |
| Token lifetime? | Access token **5 days**, no refresh token (v1.1); session 30 days sliding | official docs |
| Oldest Food order? | Last **5 orders only**, incl. delivered — observed span ~1 year; **no pagination/count param**. Re-verified adversarially: extra `page`/`count`/`offset`/`limit` params silently ignored, identical 5 back; history is account-wide (any addressId → same 5). Untested loophole: `get_food_order_details` with an out-of-band older orderId (IDs unguessable from MCP surface). `"total":5` may mean "returned", not "exist". | 2 live probes 12 Jul 2026 |
| Oldest Instamart order? | **15 days**; default 10, max ~20 per call | tool schema |
| Max order value? | **< ₹1,000** (Food & Instamart, beta cap) | official docs |
| Min order? | Instamart ₹99; Food per-restaurant | official docs |
| Payment? | **COD only** (online = v2) | official docs |
| Tracking poll cadence? | ≥ 10 s apart | official docs |
| Cancel/refund tools? | **None** — customer care 080-67466729 | tool descriptions |
| Menu pagination? | pageSize default 5, max 8 categories/page | tool schema |
| Cart TTL? | Exists (`CART_EXPIRED`) but value undocumented — refetch every turn | official docs |
| Idempotent checkout? | **No** — never blind-retry; wait 2–5 s, check orders list first | official docs |

## Servers

| Server | Endpoint | Tools |
|---|---|---|
| Food | `POST mcp.swiggy.com/food` | 14 |
| Instamart | `POST mcp.swiggy.com/im` | 13 |
| Dineout | `POST mcp.swiggy.com/dineout` | 8 |

One OAuth 2.1 PKCE token (phone + OTP) works across all three. Access token 5 days; session 30 days sliding; no refresh tokens until v1.1. Every endpoint — even `tools/list` — requires auth.

## 1. Query rate limits

| Aspect | Current (v1.0, verified live) | Planned (v1.x) |
|---|---|---|
| MCP-layer rate limit | **None** — 20-req burst: no throttling, no 429, no rate headers | 120 req/min per user per server |
| Write tools | None | 30 req/min per user per server |
| Burst allowance | N/A | 2× steady-state over 10 s |
| Tracking polls (`track_*`) | Guidance: ≥ 10 s apart (ETA cadence 10 s) | Same |
| Enforcement | Abuse shed upstream as 5xx; scraping ⇒ access revoked without notice | `429` + `Retry-After` + `X-RateLimit-*` |

## 2. Data recency / history depth

| Server | Order history | Max per call | Forward-looking |
|---|---|---|---|
| Instamart | **Last 15 days only** (`get_orders`) | 20 orders (default 10) | Immediate delivery only |
| Food | **Last 5 orders, incl. delivered** — observed span ~1 year back (verified live 12 Jul 2026); no count/pagination param (schema: only `addressId`, `activeOnly`), always returns 5. History is **account-wide, not address-scoped** — different addressIds return the identical 5 orders | 5 (fixed) | Immediate only, no scheduling |
| Dineout | **No history list** — status by known orderId only | 1 | Slots ~7 days ahead |

- Preference signal: `your_go_to_items` (Instamart only, frequent/recent items per address; lookback undocumented).
- Audit logs: 90 days, Swiggy-side, lawful request only. Account deletion erases data within 30 days.

## 3. Data available per entity

| Entity | You get | You don't get |
|---|---|---|
| Order (in window) | Items + quantities/variants, item price/subtotal + `totalPaid`, status, refunds, delivery address + coords, payment method | Anything older than window (Food: older than last 5 orders); invoices; **no delivery/handling fee line items** — `get_food_order_details` (verified live 12 Jul 2026) returns per-item price/subtotal and grand `totalPaid` only, not the full fee breakdown |
| Live tracking | Status, ETA, courier location, store info | — |
| Restaurant (Food) | Ratings, distance, open/closed, offers, full menu with variants/addons, coupons | Historical prices |
| Product (Instamart) | Name, brand, pack-size variants (`spinId`), address-scoped availability | Bulk catalog export (forbidden abuse pattern) |
| Dineout | Ratings + count, cost-for-two, highlights, deals, free slots (breakfast/lunch/dinner) | Paid deals (rejected), cancellation |
| User | Saved addresses (coords stripped), go-to items | Name/phone/email (opaque ID only), reviews history |

## 4. Hard transactional limits

| Limit | Value |
|---|---|
| Max order value (Food & Instamart) | **< ₹1,000** (beta cap) |
| Min order (Instamart) | ₹99 |
| Payment (Food) | COD only (online payment = v2 roadmap) |
| Dineout | Free reservations only, 1–20 guests, ~7-day window, no cancel/modify tool |
| Cancellations/refunds | **No tools** — customer care 080-67466729 |
| Order placement idempotency | None — never blind-retry; wait 2–5 s, check orders list, then retry |
| Menu pagination | `get_restaurant_menu` pageSize default 5, max 8 categories |

## 5. Key gotchas

- Instamart `update_cart` **replaces the entire cart** (not additive); items are `{spinId, quantity}`.
- Food cart binds to one restaurant (switch = auto-flush); Instamart cart binds to address.
- `get_addresses` strips coordinates; `track_order` needs lat/lng — get them from `get_orders`.
- Food items carry EITHER `variations` OR `variantsV2`, never both; addon validity gated by variant (`valid_addons`).
- `coupon_applied` with `coupon_discount = 0` = suggested, NOT applied.
- Instamart `get_orders` default `orderType` is `"DASH"`, not `"INSTAMART"`. Verified live 12 Jul 2026: defaults, `orderType:"INSTAMART"` and `"ALL"` (with `count:20`, `activeOnly:false`) all return `{"orders":[],"hasMore":false}` on this account — yet `your_go_to_items` still returns 6 frequent products, so preference data survives beyond the 15-day order window.
- Carts have a TTL (`CART_EXPIRED`) — refetch cart at every turn, never cache in agent memory.
- No symbolic error codes in v1.0 — classify on HTTP status + `error.message` text.
- IDE-installed MCP servers hit **production** — real orders on your account. Staging (`mcp-staging.swiggy.com`) needs an access application.
- DPDP: treat all tool data as PII; no persistence/training without consent + DPA; out-of-India inference needs DPA + SCCs.

## 6. Build implications

**Feasible:** conversational ordering agents (all 3 verticals end-to-end), Instamart reorder/routine automation (go-to items + 15-day history), Food "repeat order" via last-5 delivered orders (each carries a full `reorderMeta` with itemIds/variants), combined evening planner (Dineout + Food, one token), small COD orders.

**Blocked:** spend analytics / long-horizon dashboards (unless you accumulate data yourself → consent obligations), orders ≥ ₹1,000, online payment on Food, scheduled orders, cancellations, catalog/price scraping, Dineout beyond free booking.

**Roadmap:** v1.1 — refresh tokens, rate-limit headers, error-code registry, status page, Food widgets. v1.2 — Instamart/Dineout widgets. v2 — versioned URLs, online payment on Food.

# Swiggy Food MCP — search & discovery surface (probed 2026-07-12, addressId 295250620, HSR Layout)

## search_restaurants
Params: `addressId` (req), `query` (req, restaurant name or cuisine, NL queries supported), `offset` (pagination, use `nextOffset` from response). **No structured filters** — no cuisine/rating/price/veg/sort params; filtering must be done client-side on returned fields.

Probe `"biryani"`: 10 results, `total: 10`, **no `nextOffset` field appeared** in the response (pagination param exists but response gave no cursor at 10 results).

Per-restaurant fields: `id`, `name` (ads marked with literal `" (Ad)"` suffix in name), `cuisines[]`, `avgRating`, `totalRatings` ("22K+"), `costForTwo` ("₹400 for two"), `areaName`, `distanceKm`, `deliveryTimeMinutes`, `deliveryTimeRange` ("25-30 MINS"), `offer` ("70% OFF UPTO ₹130" / "ITEMS AT ₹49" / "₹100 OFF ABOVE ₹499"), `imageUrl`, `availabilityStatus` ("OPEN"/"CLOSED"/"UNAVAILABLE").

Example (trimmed):
```json
{"id":"233815","name":"Paradise Biryani","cuisines":["Biryani","Hyderabadi"],"avgRating":4.5,"totalRatings":"22K+","costForTwo":"₹400 for two","distanceKm":1.6,"deliveryTimeMinutes":26,"offer":"70% OFF UPTO ₹130","availabilityStatus":"OPEN"}
```

## search_menu
Params: `addressId` (req), `query` (req, dish name), `offset`, `restaurantIdOfAddedItem` (scope to restaurant), `vegFilter` (0/1; 1 = veg-only; no non-veg-only filter).

**KEY FINDING: global (unscoped) search_menu returns 0 results.** Probed "chicken biryani", "biryani", "masala dosa" without restaurantId — all `{"items":[],"total":0}`. In practice search_menu only works **scoped to a restaurant** via `restaurantIdOfAddedItem`. So "find me X under ₹300 anywhere, fast" is NOT one call — it's search_restaurants → pick restaurant(s) → search_menu per restaurant.

Scoped probe ("chicken biryani", restaurant 1027154): 10 items, `total: 10`. Per-item fields: `name`, `price` (number, ₹), `menu_item_id`, `inStock` (0/1), `imageUrl`, `rating` ("4.4"), `totalRatings` ("386"), `hasVariants`, `hasAddons`, `addons[]` (full groups: `groupId`, `groupName`, `choices[{id,name,price}]`, `maxAddons`, `maxFreeAddons`). No restaurant metadata, no ETA, no veg flag in this response — restaurant context comes from the search_restaurants step.

Items have EITHER `variations` OR `variantsV2` (never both) — reuse the same format when calling update_food_cart.

Example (trimmed):
```json
{"name":"Bowl Supreme Boneless Chicken Biryani","price":260,"menu_item_id":"166754812","inStock":1,"rating":"4.3","totalRatings":"454","hasVariants":false,"hasAddons":true}
```

## get_restaurant_menu
Params: `addressId` (req), `restaurantId` (req), `page` (default 1), `pageSize` (categories per page, default 5, max 8).

Probe (1027154 Nandhana Palace): returns `restaurant` header block (`isOpen`, `deliveryTime`, `slaString`, `costForTwoMessage`, `avgRating`, address) + `categories[]`. Categories can have nested `subcategories[]` (e.g. "Acclaimed Biryani" → "Non-Veg Biryani"/"Veg Biryani"). "Recommended" category is truncated (`totalItems: 20, hasMoreItems: true` with only 10 shown). Top level: `totalCategories: 20, page: 1, pageSize: 5, hasMore: true`.

Per-item fields (compact view): `id`, `name`, `description` (truncated ~100 chars), `price`, `inStock`, `isVeg` (bool — present here, NOT in search_menu), `isBestseller` (only when true), `rating`, `imageUrl`, `hasVariants`, `hasAddons`. No addon detail — use search_menu (scoped) to get variant/addon IDs for ordering.

## Notes for "find lunch under ₹300 before 1PM"
- Enables: search_restaurants gives ETA + distance + rating + open/closed + offer text in one call → filter `deliveryTimeMinutes` and `availabilityStatus` client-side; then scoped search_menu or get_restaurant_menu gives per-dish price/rating/veg → filter price ≤ 300 client-side.
- Missing: no price/rating/veg filters server-side; no global dish search (must fan out per restaurant, costs 1 call each — mind rate limits in mcp-limits.md); no per-dish ETA (use restaurant ETA); dish veg flag only in get_restaurant_menu, not search_menu; offers are display strings, not structured discounts (real discount only visible in cart).
- Ads: strip/annotate `" (Ad)"` suffix in restaurant names; results mix ads with organic.

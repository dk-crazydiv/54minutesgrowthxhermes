# Kartik

- Name: Kartik Godawat
- Telegram user id: `8626910859` (folder can be renamed to this id when
  Priyam's per-Telegram-user auth flow lands — naming is `users/<telegram-id-or-slug>/`)
- Zomato: linked via MCP OAuth (token in `~/.hermes/mcp-tokens/zomato.json`, not in repo)

## Order history — use the CSV, don't re-pull

`history.csv` is the full lifetime Zomato order history (122 orders,
2022-06 → 2026-07), dumped once on 2026-07-12 via `get_order_history`
pagination. **Answer history questions from this CSV** — only hit the MCP
for orders newer than the latest row. Years were inferred from the
newest-first order (Zomato omits the year in dates). No per-item prices —
Zomato returns order totals only.

Sensitive data policy: no user addresses or phone numbers are stored here —
only restaurant name/area, items, totals, status.

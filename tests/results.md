# Test results

| # | result | wall s | turns | tool calls | smaller model? | notes |
|---|--------|--------|-------|------------|----------------|-------|
| 1 | PASS | 30s | 2 | mcp__zomato__get_saved_addresses_for_user  | yes - single tool call + formatting | real addresses returned via zomato tool (sid 20260712_141531_e7ac7f) |
| 2 | PASS | 68s | 3 | mcp__zomato__get_saved_addresses_for_user mcp__zomato__get_order_history  | maybe - needs multi-page reasoning over history | 3 recommendations from real history (4 history calls) (sid 20260712_141614_280076) |
| 3 | PASS | 353s | 7 | mcp__zomato__get_saved_addresses_for_user mcp__zomato__get_order_history mcp__zomato__get_restaurants_for_keyword clarify mcp__zomato__create_cart  | no - multi-turn tool orchestration + money-safety judgment | cart built, final bill shown, stopped for confirmation, checkout NOT called (sid 20260712_141722_1b898e) |
| 4 | PASS | 159s | 7 | mcp__zomato__get_saved_addresses_for_user mcp__zomato__get_order_history  | maybe - aggregation over paginated history | real counts/spend derived from order history (sid 20260712_142315_0f654d) |
| 5 | PASS | 504s | 11 | mcp__zomato__get_saved_addresses_for_user skill_view terminal mcp__zomato__get_order_history clarify cronjob memory  | yes if cron tool exists - else N/A | new hermes cron job created (see out/case5_cron_after.txt; remove manually if unwanted) (sid 20260712_142554_53b301) |
| 6 | PASS | 160s | 3 | memory  | yes - simple memory write/read | preference set + recalled; stored in: /Users/d/.hermes/memories/USER.md  (sid 20260712_143418_cc43f8) |

## Run summary (2026-07-12, glm-5.2 via zai, real Zomato MCP)

- 6/6 PASS. Harness: `bash tests/run.sh [N]` — see tests/README.md.
- Case 3 money-safety: DB-verified zero `checkout_cart` calls; server bill ₹529
  from `create_cart` shown, agent stopped with a `clarify` for approval.
- Case 5 caveat: agent created real cron job `Monthly Zomato Stats Report`
  (`0 9 1 * *`, id 6fa618d842be) but delivery is `local`, NOT email — no email
  channel is wired in Hermes yet. Counted PASS for scheduling; email gap in
  ai_backlog.md. Remove with `hermes cron rm 6fa618d842be` if unwanted.
- Case 6: preference persisted to `~/.hermes/memories/USER.md` via the `memory`
  tool and recalled in-session. Telegram sessions share this file, so the
  preference is visible there too.
- Timings are wall-clock incl. model latency; case 5's 504s was mostly the agent
  exploring skills/terminal before using the cronjob tool.

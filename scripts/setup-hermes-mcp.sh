#!/usr/bin/env bash
# Registers the Swiggy (food + instamart) and Zomato MCP servers in Hermes Agent's
# config (~/.hermes/config.yaml). Idempotent: skips servers already configured.
# Endpoints per docs/swiggy/mcp-setup.md and docs/zomato/mcp-setup.md.
set -euo pipefail

CONFIG="${HERMES_CONFIG:-$HOME/.hermes/config.yaml}"

SERVERS=(
  "swiggy-food|https://mcp.swiggy.com/food"
  "swiggy-instamart|https://mcp.swiggy.com/im"
  "zomato|https://mcp-server.zomato.com/mcp"
)

mkdir -p "$(dirname "$CONFIG")"
touch "$CONFIG"

if ! grep -qE '^mcp_servers:' "$CONFIG"; then
  printf '\nmcp_servers:\n' >> "$CONFIG"
fi

for entry in "${SERVERS[@]}"; do
  name="${entry%%|*}"
  url="${entry##*|}"
  if grep -qE "^  ${name}:" "$CONFIG"; then
    echo "skip: $name already in $CONFIG"
    continue
  fi
  # Insert the server block directly under the top-level mcp_servers: key
  # so it can't land under some other mapping at the end of the file.
  block="  ${name}:\n    url: \"${url}\"\n    auth: oauth"
  awk -v block="$block" '
    { print }
    /^mcp_servers:/ && !done { printf "%s\n", block; done=1 }
  ' "$CONFIG" > "$CONFIG.tmp" && mv "$CONFIG.tmp" "$CONFIG"
  echo "added: $name -> $url"
done

echo
echo "Done. Next:"
echo "  1. Run: hermes chat"
echo "  2. Hermes prints an authorize URL per server (Swiggy: phone+OTP, Zomato: OAuth) — complete each in the browser."
echo "  3. If Hermes was already running, use /reload-mcp inside the session."

if ! command -v hermes >/dev/null 2>&1; then
  echo
  echo "WARNING: 'hermes' not found on PATH — install Hermes Agent first: https://hermes-agent.nousresearch.com/docs/"
fi

#!/usr/bin/env bash
# Make the gateway present as plain Hermes to end users: clean /new banner,
# no model/provider/context internals, no random tips. Idempotent; run.sh
# reapplies it after setup.sh re-vendors hermes.
set -e
cd "$(dirname "$0")/.."
V=vendor/hermes-agent

python3 - <<'EOF'
import re

# 1) locale: friendly reset banner, no tip line
p = "vendor/hermes-agent/locales/en.yaml"
s = open(p).read()
s = s.replace('header_default:        "✨ Session reset! Starting fresh."',
              'header_default:        "✨ Fresh chat. What are we eating?"')
s = s.replace('header_new:            "✨ New session started!"',
              'header_new:            "✨ Fresh chat. What are we eating?"')
s = re.sub(r'tip:\s+"\\n✦ Tip: \{tip\}"', 'tip:                   ""', s)
open(p, "w").write(s)

# 2) gateway: drop the Model/Provider/Context info block from /new replies
p = "vendor/hermes-agent/gateway/slash_commands.py"
s = open(p).read()
old = """            session_info = await asyncio.to_thread(
                self._reset_notice_session_info, source
            )"""
if old in s:
    s = s.replace(old, "            session_info = \"\"  # branding patch: hide internals")
    open(p, "w").write(s)
EOF
echo "hermes branding patch applied"

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
_welcome = ('"✨ Fresh chat. What are you craving? Try \\"my last order\\", '
            '\\"something under ₹300\\", or \\"surprise me\\"."')
s = s.replace('header_default:        "✨ Session reset! Starting fresh."',
              'header_default:        ' + _welcome)
s = s.replace('header_new:            "✨ New session started!"',
              'header_new:            ' + _welcome)
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
python3 - <<'EOF'
# 3) deliver MCP-produced media (e.g. Zomato checkout QR) as real attachments:
# zomato tools aren't on the producer-tool allowlist, so their MEDIA: tags
# were falling through as literal text on Telegram.
p = "vendor/hermes-agent/gateway/run.py"
s = open(p).read()
old = '''_AUTO_APPEND_MEDIA_TOOL_NAMES = {
    "text_to_speech",
    "text_to_speech_tool",
    "image_generate",
}'''
new = '''_AUTO_APPEND_MEDIA_TOOL_NAMES = {
    "text_to_speech",
    "text_to_speech_tool",
    "image_generate",
    # buildathon patch: Zomato MCP checkout returns a payment QR image
    "checkout_cart",
    "mcp__zomato__checkout_cart",
    "zomato__checkout_cart",
}'''
if old in s:
    s = s.replace(old, new)
    open(p, "w").write(s)
EOF
python3 - <<'EOF'
# 4) upscale tiny cached PNGs (Zomato's payment QR arrives ~100px) so they're
# scannable on a phone. Uses macOS sips; no-op if it fails.
p = "vendor/hermes-agent/gateway/platforms/base.py"
s = open(p).read()
anchor = """    filepath.write_bytes(data)
    return str(filepath)"""
patched = """    filepath.write_bytes(data)
    # buildathon patch: upscale tiny PNGs (payment QRs) to a scannable size
    try:
        if ext.lower() == ".png" and len(data) < 20000:
            import subprocess
            subprocess.run(["sips", "--resampleWidth", "800", str(filepath)],
                           capture_output=True, timeout=10)
    except Exception:
        pass
    return str(filepath)"""
if anchor in s and "upscale tiny PNGs" not in s:
    s = s.replace(anchor, patched, 1)
    open(p, "w").write(s)
EOF
python3 - <<'EOF'
# 5) hide tool-execution internals from end users: force display.tool_progress
# off in the runtime config so Telegram never shows "terminal / shell /
# Searching / Reading" cards — only the final food answer. Idempotent; config
# lives in ~/.hermes (not vendored), so we enforce it here where run.sh reapplies
# branding after every setup.
import os, re
cfg = os.path.join(os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes")), "config.yaml")
if os.path.exists(cfg):
    s = open(cfg).read()
    # match the exact "tool_progress:" key (not tool_progress_prompt/_command/etc.)
    if re.search(r'(?m)^(\s*)tool_progress:[ \t]*\S+', s):
        s2 = re.sub(r'(?m)^(\s*)tool_progress:[ \t]*\S+.*$', r'\1tool_progress: off', s)
    elif re.search(r'(?m)^display:\s*$', s):
        s2 = re.sub(r'(?m)^(display:\s*)$', r'\1\n  tool_progress: off', s, count=1)
    else:
        s2 = s + "\ndisplay:\n  tool_progress: off\n"
    if s2 != s:
        open(cfg, "w").write(s2)
        print("config: display.tool_progress forced off")
    else:
        print("config: display.tool_progress already off")
EOF
echo "hermes branding patch applied"

#!/usr/bin/env python3
"""TEMPORARY hackathon debug dashboard for the Hermes Telegram agent.

Usage:  python3 scripts/debug-dashboard.py   then open http://127.0.0.1:8787

Read-only. Localhost only. No auth (do not expose). Stdlib only.

Data sources:
  - ~/.hermes/state.db      (sqlite, ro): sessions (model/brain, counts) +
                            messages (user queries, assistant replies, tool calls)
  - ~/.hermes/logs/gateway.log and errors.log: recent WARNING/ERROR lines

Shows, newest first: incoming messages, which model handled them, tool/MCP
calls, and errors. Auto-refreshes every 3s. Masks token-looking secrets.

Delete this file after the buildathon.
"""
import html
import json
import os
import re
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

HERMES = os.path.expanduser("~/.hermes")
DB = os.path.join(HERMES, "state.db")
LOGS = [os.path.join(HERMES, "logs", f) for f in ("gateway.log", "errors.log")]
PORT = int(os.environ.get("PORT", "8787"))
LIMIT = 200

SECRET_RE = re.compile(
    r"(\d{6,}:[A-Za-z0-9_-]{25,}"          # telegram bot tokens
    r"|sk-[A-Za-z0-9_-]{16,}"               # api keys
    r"|Bearer\s+\S{16,}"
    r"|[A-Za-z0-9_-]{40,})"                 # long opaque blobs
)

def mask(s):
    return SECRET_RE.sub(lambda m: m.group(0)[:6] + "…MASKED", s or "")

def esc(s):
    return html.escape(mask(s))

def fetch_rows():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
    con.row_factory = sqlite3.Row
    try:
        return con.execute("""
            SELECT m.id, m.role, m.content, m.tool_calls, m.tool_name,
                   m.timestamp, m.finish_reason,
                   s.model, s.display_name, s.id AS sid
            FROM messages m JOIN sessions s ON s.id = m.session_id
            ORDER BY m.id DESC LIMIT ?""", (LIMIT,)).fetchall()
    finally:
        con.close()

def tail_log_lines(path, n=40):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 64_000))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    keep = [l for l in lines if " ERROR " in l or " WARNING " in l or " CRITICAL " in l]
    return keep[-n:][::-1]

def fmt_tool_calls(raw):
    try:
        calls = json.loads(raw)
    except Exception:
        return esc(str(raw)[:300])
    out = []
    for c in calls or []:
        fn = (c.get("function") or {}) if isinstance(c, dict) else {}
        out.append(f"<b>{esc(fn.get('name') or c.get('name', '?'))}</b>"
                   f"({esc(str(fn.get('arguments', ''))[:400])})")
    return "<br>".join(out) or esc(str(raw)[:300])

def render():
    rows_html = []
    for r in fetch_rows():
        ts = time.strftime("%m-%d %H:%M:%S", time.localtime(r["timestamp"]))
        cls, label, body = "", r["role"], esc((r["content"] or "")[:600])
        if r["role"] == "user":
            cls, label = "query", "USER"
        elif r["role"] == "assistant" and r["tool_calls"]:
            cls, label, body = "tool", "TOOL CALL", fmt_tool_calls(r["tool_calls"])
        elif r["role"] == "tool":
            cls, label = "toolres", f"TOOL RESULT · {esc(r['tool_name'] or '')}"
        elif r["role"] == "assistant":
            cls, label = "reply", "ASSISTANT"
        if r["finish_reason"] and r["finish_reason"] not in ("stop", "end_turn", "tool_calls"):
            cls += " err"
        rows_html.append(
            f"<tr class='{cls}'><td class='ts'>{ts}</td>"
            f"<td class='model'>{esc(r['model'] or '?')}<br><small>{esc(r['sid'])}</small></td>"
            f"<td class='role'>{label}</td><td class='body'>{body}</td></tr>")

    log_html = []
    for p in LOGS:
        for line in tail_log_lines(p):
            cls = "err" if "ERROR" in line or "CRITICAL" in line else "warn"
            log_html.append(f"<div class='{cls}'>{esc(line)}</div>")

    return f"""<!doctype html><meta charset=utf-8>
<meta http-equiv=refresh content=3><title>Hermes debug (temp)</title>
<style>
 body{{font:13px/1.4 ui-monospace,monospace;background:#111;color:#ddd;margin:16px}}
 h1{{font-size:15px}} .note{{color:#888}}
 table{{border-collapse:collapse;width:100%;margin-top:8px}}
 td{{border-bottom:1px solid #2a2a2a;padding:4px 8px;vertical-align:top}}
 .ts{{white-space:nowrap;color:#888}} .model{{color:#9cf;white-space:nowrap}}
 .query .role{{color:#7f7;font-weight:bold}} .reply .role{{color:#ccc}}
 .tool .role{{color:#fc6;font-weight:bold}} .toolres .role{{color:#c9f}}
 .err{{background:#3a1414}} .warn{{color:#da5}} .body{{word-break:break-word}}
 #logs div{{padding:2px 4px}} small{{color:#666}}
</style>
<h1>Hermes debug dashboard <span class=note>— TEMPORARY, localhost only, read-only,
auto-refresh 3s — {time.strftime('%H:%M:%S')}</span></h1>
<table><tr><td class=ts>time</td><td>model / session</td><td>event</td><td>content</td></tr>
{''.join(rows_html)}</table>
<h1>gateway/errors log (WARNING+)</h1><div id=logs>{''.join(log_html)}</div>"""

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            page = render().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        except Exception as e:
            page = f"dashboard error: {html.escape(str(e))}".encode()
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    print(f"Hermes debug dashboard (temporary) -> http://127.0.0.1:{PORT}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()

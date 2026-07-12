#!/usr/bin/env python3
"""TEMPORARY hackathon debug dashboard for the Hermes Telegram agent.

Usage:  python3 scripts/debug-dashboard.py   then open http://127.0.0.1:8787

Read-only. Localhost only. No auth (do not expose). Stdlib only.

Views:
  /            sessions grouped as collapsible threads (+ session picker)
  /?sid=<id>   single session expanded
  /users       per-user memory store (users/<slug>/: profile, prefs, history)

Data sources:
  - ~/.hermes/state.db      (sqlite, ro): sessions (model, token/tool counts) +
                            messages (user queries, replies, tool calls/results)
  - ~/.hermes/logs/gateway.log and errors.log: recent WARNING/ERROR lines
  - <repo>/users/<slug>/    profile.md, preferences.md, notes.md, history.csv

Auto-refreshes every 3s. Masks token-looking secrets.
Delete this file after the buildathon.
"""
import csv
import html
import json
import os
import re
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

HERMES = os.path.expanduser("~/.hermes")
DB = os.path.join(HERMES, "state.db")
LOGS = [os.path.join(HERMES, "logs", f) for f in ("gateway.log", "errors.log")]
USERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "users")
PORT = int(os.environ.get("PORT", "8787"))
MSG_LIMIT = 400          # messages scanned across sessions
SESSION_LIMIT = 30       # sessions listed

SECRET_RE = re.compile(
    r"(\d{6,}:[A-Za-z0-9_-]{25,}"          # telegram bot tokens
    r"|sk-[A-Za-z0-9_-]{16,}"               # api keys
    r"|Bearer\s+\S{16,}"
    r"|[A-Za-z0-9_-]{40,})"                 # long opaque blobs
)

def mask(s):
    return SECRET_RE.sub(lambda m: m.group(0)[:6] + "…MASKED", s or "")

def esc(s):
    return html.escape(mask(str(s)))

def db():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
    con.row_factory = sqlite3.Row
    return con

def fetch_sessions():
    con = db()
    try:
        return con.execute("""
            SELECT id, model, display_name, started_at, ended_at,
                   message_count, tool_call_count,
                   input_tokens, output_tokens
            FROM sessions ORDER BY started_at DESC LIMIT ?""",
            (SESSION_LIMIT,)).fetchall()
    finally:
        con.close()

def fetch_messages(sids):
    if not sids:
        return {}
    con = db()
    try:
        q = ",".join("?" * len(sids))
        rows = con.execute(f"""
            SELECT id, session_id, role, content, tool_calls, tool_name,
                   timestamp, finish_reason
            FROM messages WHERE session_id IN ({q})
            ORDER BY id DESC LIMIT ?""", (*sids, MSG_LIMIT)).fetchall()
    finally:
        con.close()
    by_sid = {}
    for r in rows:
        by_sid.setdefault(r["session_id"], []).append(r)
    for v in by_sid.values():
        v.reverse()  # chronological within a thread
    return by_sid

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
    """Render tool calls as: <name>(trimmed pretty args)."""
    try:
        calls = json.loads(raw)
    except Exception:
        return esc(str(raw)[:300])
    out = []
    for c in calls or []:
        fn = (c.get("function") or {}) if isinstance(c, dict) else {}
        name = fn.get("name") or (c.get("name") if isinstance(c, dict) else None) or "?"
        args = fn.get("arguments", "")
        try:  # arguments usually a JSON string — compact it for readability
            args = json.dumps(json.loads(args), ensure_ascii=False)
        except Exception:
            args = str(args)
        if len(args) > 300:
            args = args[:300] + f"… (+{len(args)-300} chars)"
        out.append(f"<span class=tname>{esc(name)}</span>"
                   f"<span class=targs>({esc(args)})</span>")
    return "<br>".join(out) or esc(str(raw)[:300])

def fmt_tool_result(content):
    """Trimmed preview of a tool result, compacted if JSON."""
    s = content or ""
    try:
        s = json.dumps(json.loads(s), ensure_ascii=False)
    except Exception:
        pass
    if len(s) > 400:
        s = s[:400] + f"… (+{len(s)-400} chars)"
    return esc(s)

def msg_row(r):
    ts = time.strftime("%H:%M:%S", time.localtime(r["timestamp"]))
    cls, label, body = "", r["role"], esc((r["content"] or "")[:600])
    if r["role"] == "user":
        cls, label = "query", "USER"
    elif r["role"] == "assistant" and r["tool_calls"]:
        cls, label, body = "tool", "TOOL CALL", fmt_tool_calls(r["tool_calls"])
    elif r["role"] == "tool":
        cls, label = "toolres", f"RESULT · {esc(r['tool_name'] or '')}"
        body = fmt_tool_result(r["content"])
    elif r["role"] == "assistant":
        cls, label = "reply", "ASSISTANT"
    if r["finish_reason"] and r["finish_reason"] not in ("stop", "end_turn", "tool_calls"):
        cls += " err"
    return (f"<tr class='{cls}'><td class='ts'>{ts}</td>"
            f"<td class='role'>{label}</td><td class='body'>{body}</td></tr>")

def render_sessions(sel_sid=None):
    sessions = fetch_sessions()
    msgs = fetch_messages([s["id"] for s in sessions])
    picker = ["<select onchange=\"location='/?sid='+this.value\">",
              f"<option value=''>— all sessions ({len(sessions)}) —</option>"]
    blocks = []
    for s in sessions:
        sid = s["id"]
        rows = msgs.get(sid, [])
        turns = sum(1 for r in rows if r["role"] == "user")
        started = time.strftime("%m-%d %H:%M", time.localtime(s["started_at"]))
        title = f"{started} · {s['display_name'] or sid[:8]} · {s['model'] or '?'}"
        stats = (f"{turns} turns · {s['message_count']} msgs · "
                 f"{s['tool_call_count']} tool calls · "
                 f"{s['input_tokens']}/{s['output_tokens']} tok in/out")
        picker.append(f"<option value='{esc(sid)}'"
                      f"{' selected' if sid == sel_sid else ''}>{esc(title)}</option>")
        if sel_sid and sid != sel_sid:
            continue
        is_open = " open" if (sel_sid or s is sessions[0]) else ""
        blocks.append(
            f"<details class=sess{is_open}><summary><b>{esc(title)}</b> "
            f"<span class=stats>{esc(stats)}</span> "
            f"<small>{esc(sid)}</small></summary>"
            f"<table>{''.join(msg_row(r) for r in rows) or '<tr><td class=note>no messages</td></tr>'}"
            f"</table></details>")
    picker.append("</select>")

    log_html = []
    for p in LOGS:
        for line in tail_log_lines(p):
            cls = "err" if "ERROR" in line or "CRITICAL" in line else "warn"
            log_html.append(f"<div class='{cls}'>{esc(line)}</div>")

    return (f"<div class=bar>Session: {''.join(picker)}"
            + (" <a href='/'>show all</a>" if sel_sid else "") + "</div>"
            + "".join(blocks)
            + f"<h1>gateway/errors log (WARNING+)</h1><div id=logs>{''.join(log_html)}</div>")

def render_users():
    if not os.path.isdir(USERS_DIR):
        return "<p class=note>no users/ directory yet</p>"
    blocks = []
    for slug in sorted(os.listdir(USERS_DIR)):
        d = os.path.join(USERS_DIR, slug)
        if not os.path.isdir(d):
            continue
        parts = [f"<details class=sess open><summary><b>{esc(slug)}</b></summary>"]
        for name in ("profile.md", "preferences.md", "notes.md"):
            p = os.path.join(d, name)
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    txt = f.read()[:4000]
                parts.append(f"<h2>{esc(name)}</h2><pre>{esc(txt)}</pre>")
        hp = os.path.join(d, "history.csv")
        if os.path.exists(hp):
            with open(hp, newline="", encoding="utf-8", errors="replace") as f:
                rows = list(csv.reader(f))
            head, body = rows[:1], rows[1:]
            parts.append(f"<h2>history.csv — {len(body)} rows (last 50 shown)</h2><table>")
            for row in head + body[-50:]:
                tag = "th" if row in head else "td"
                parts.append("<tr>" + "".join(
                    f"<{tag} class=body>{esc(c[:80])}</{tag}>" for c in row) + "</tr>")
            parts.append("</table>")
        parts.append("</details>")
        blocks.append("".join(parts))
    return "".join(blocks) or "<p class=note>users/ is empty</p>"

def render(path, qs):
    view = "users" if path == "/users" else "sessions"
    sel_sid = (qs.get("sid") or [None])[0]
    body = render_users() if view == "users" else render_sessions(sel_sid)
    return f"""<!doctype html><meta charset=utf-8>
<meta http-equiv=refresh content=3><title>Hermes debug (temp)</title>
<style>
 body{{font:13px/1.4 ui-monospace,monospace;background:#111;color:#ddd;margin:16px}}
 h1{{font-size:15px}} h2{{font-size:13px;color:#9cf;margin:10px 0 4px}}
 .note{{color:#888}} a{{color:#4db8e8}}
 .bar{{margin:8px 0}} select{{background:#222;color:#ddd;border:1px solid #444;
   font:inherit;padding:2px;max-width:70%}}
 details.sess{{border:1px solid #2a2a2a;border-radius:4px;margin:8px 0;padding:2px 8px}}
 summary{{cursor:pointer;padding:4px 0}} .stats{{color:#9cf}}
 table{{border-collapse:collapse;width:100%;margin-top:4px}}
 td,th{{border-bottom:1px solid #2a2a2a;padding:4px 8px;vertical-align:top;text-align:left}}
 .ts{{white-space:nowrap;color:#888}}
 .query .role{{color:#7f7;font-weight:bold}} .reply .role{{color:#ccc}}
 .tool .role{{color:#fc6;font-weight:bold}} .toolres .role{{color:#c9f}}
 .tname{{color:#fc6;font-weight:bold}} .targs{{color:#aaa}}
 .err{{background:#3a1414}} .warn{{color:#da5}} .body{{word-break:break-word}}
 #logs div{{padding:2px 4px}} small{{color:#666}}
 pre{{white-space:pre-wrap;background:#181818;padding:6px;border-radius:4px}}
</style>
<h1>Hermes debug dashboard <span class=note>— TEMPORARY, localhost only, read-only,
auto-refresh 3s — {time.strftime('%H:%M:%S')}</span>
&nbsp; <a href='/'{" style='font-weight:bold'" if view == "sessions" else ""}>Sessions</a> ·
<a href='/users'{" style='font-weight:bold'" if view == "users" else ""}>Users</a></h1>
{body}"""

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        try:
            page = render(u.path, parse_qs(u.query)).encode()
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

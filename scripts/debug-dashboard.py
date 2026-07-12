#!/usr/bin/env python3
"""TEMPORARY hackathon debug dashboard for the Hermes Telegram agent.

Usage:  python3 scripts/debug-dashboard.py   then open http://127.0.0.1:8787

Read-only. Localhost only. No auth (do not expose). Stdlib only.

Views:
  /             sessions grouped as collapsible threads (+ session picker,
                users summary strip)
  /?sid=<id>    single session expanded
  /users        per-user memory store (users/<slug>/: profile, prefs, history)
  /user/<slug>  everything for one user: memory files, history.csv
                (last 20, ?all=1 shows all) and their sessions/threads.
                Attribution: sessions.user_id == telegram id found in
                users/<slug>/profile.md; sessions with no user_id (CLI test
                runs) are grouped under the "cli-tests" pseudo-user.

Data sources:
  - ~/.hermes/state.db      (sqlite, ro): sessions (model, token/tool counts) +
                            messages (user queries, replies, tool calls/results)
  - ~/.hermes/logs/gateway.log and errors.log: recent WARNING/ERROR lines
  - <repo>/users/<slug>/    profile.md, preferences.md, notes.md, history.csv

Auto-refreshes every 3s via JS reload; open/closed accordion state is kept in
sessionStorage and re-applied after each refresh, and refresh is skipped while
the user has text selected. Masks token-looking secrets.
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

TELEGRAM_ID_RE = re.compile(r"[Tt]elegram user id:?\s*`?(\d{5,})`?")
CLI_USER = "cli-tests"

def user_map():
    """slug -> telegram user id, parsed from users/<slug>/profile.md."""
    m = {}
    if os.path.isdir(USERS_DIR):
        for slug in sorted(os.listdir(USERS_DIR)):
            p = os.path.join(USERS_DIR, slug, "profile.md")
            if os.path.isfile(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    hit = TELEGRAM_ID_RE.search(f.read())
                if hit:
                    m[slug] = hit.group(1)
    return m

def slug_for_session(s, id_to_slug):
    """Which user does a session belong to? NULL user_id -> cli-tests."""
    uid = s["user_id"] or s["chat_id"]
    if not uid:
        return CLI_USER
    return id_to_slug.get(str(uid), f"tg-{uid}")

def fetch_sessions(user_slug=None, limit=SESSION_LIMIT):
    """Latest sessions; optionally only those attributed to user_slug."""
    con = db()
    try:
        rows = con.execute("""
            SELECT id, source, user_id, chat_id, model, display_name,
                   started_at, ended_at, message_count, tool_call_count,
                   input_tokens, output_tokens
            FROM sessions ORDER BY started_at DESC""").fetchall()
    finally:
        con.close()
    if user_slug is not None:
        id_to_slug = {v: k for k, v in user_map().items()}
        rows = [s for s in rows if slug_for_session(s, id_to_slug) == user_slug]
    return rows[:limit]

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

def csv_row_count(slug):
    p = os.path.join(USERS_DIR, slug, "history.csv")
    try:
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            return max(0, sum(1 for _ in csv.reader(f)) - 1)
    except OSError:
        return 0

def users_strip():
    """user -> sessions count, last active, csv orders; links to /user/<slug>."""
    id_to_slug = {v: k for k, v in user_map().items()}
    stats = {}  # slug -> [count, last_active]
    for s in fetch_sessions(limit=10_000):
        slug = slug_for_session(s, id_to_slug)
        st = stats.setdefault(slug, [0, 0])
        st[0] += 1
        st[1] = max(st[1], s["started_at"])
    for slug in id_to_slug.values():
        stats.setdefault(slug, [0, 0])
    cells = []
    for slug, (n, last) in sorted(stats.items(), key=lambda kv: -kv[1][1]):
        last_s = time.strftime("%m-%d %H:%M", time.localtime(last)) if last else "never"
        orders = csv_row_count(slug)
        cells.append(f"<a class=ucard href='/user/{esc(slug)}'><b>{esc(slug)}</b>"
                     f" · {n} sessions · last {last_s}"
                     + (f" · {orders} orders" if orders else "") + "</a>")
    return "<div class=ustrip>Users: " + " ".join(cells) + "</div>" if cells else ""

def render_sessions(sel_sid=None, user_slug=None):
    sessions = fetch_sessions(user_slug)
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
        is_open = " open" if (sel_sid or (not user_slug and s is sessions[0])) else ""
        blocks.append(
            f"<details class=sess id='d-{esc(sid)}'{is_open}><summary><b>{esc(title)}</b> "
            f"<span class=stats>{esc(stats)}</span> "
            f"<small>{esc(sid)}</small></summary>"
            f"<table>{''.join(msg_row(r) for r in rows) or '<tr><td class=note>no messages</td></tr>'}"
            f"</table></details>")
    picker.append("</select>")

    if user_slug is not None:  # embedded in a per-user page: threads only
        return "".join(blocks) or "<p class=note>no sessions for this user</p>"

    log_html = []
    for p in LOGS:
        for line in tail_log_lines(p):
            cls = "err" if "ERROR" in line or "CRITICAL" in line else "warn"
            log_html.append(f"<div class='{cls}'>{esc(line)}</div>")

    return (users_strip()
            + f"<div class=bar>Session: {''.join(picker)}"
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
        parts = [f"<details class=sess id='u-{esc(slug)}' open><summary><b>{esc(slug)}</b> "
                 f"<a href='/user/{esc(slug)}'>full view</a></summary>"]
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

def render_history_csv(slug, show_all):
    p = os.path.join(USERS_DIR, slug, "history.csv")
    if not os.path.exists(p):
        return ""
    with open(p, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))
    head, body = rows[:1], rows[1:]
    shown = body if show_all else body[-20:]
    toggle = (f"<a href='/user/{esc(slug)}'>show last 20</a>" if show_all
              else f"<a href='/user/{esc(slug)}?all=1'>show all</a>")
    out = [f"<h2>history.csv — {len(body)} rows, {len(shown)} shown · {toggle}</h2><table>"]
    for row in head + shown:
        tag = "th" if row in head else "td"
        out.append("<tr>" + "".join(
            f"<{tag} class=body>{esc(c[:80])}</{tag}>" for c in row) + "</tr>")
    out.append("</table>")
    return "".join(out)

def render_user(slug, qs):
    """Everything for one user: memory files, order history, all their threads."""
    parts = [f"<h1>user: {esc(slug)}</h1>"]
    d = os.path.join(USERS_DIR, slug)
    if os.path.isdir(d):
        tid = user_map().get(slug)
        if tid:
            parts.append(f"<p class=note>telegram id {esc(tid)}</p>")
        for name in ("profile.md", "preferences.md", "notes.md"):
            p = os.path.join(d, name)
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    txt = f.read()[:8000]
                parts.append(f"<details class=sess id='f-{esc(slug)}-{esc(name)}' open>"
                             f"<summary><b>{esc(name)}</b>"
                             f"</summary><pre>{esc(txt)}</pre></details>")
        parts.append(render_history_csv(slug, (qs.get("all") or [""])[0] == "1"))
    elif slug == CLI_USER:
        parts.append("<p class=note>pseudo-user: sessions with no telegram "
                     "user id (CLI test runs)</p>")
    else:
        parts.append("<p class=note>no users/ folder for this slug</p>")
    parts.append("<h2>conversation history</h2>")
    parts.append(render_sessions(user_slug=slug))
    return "".join(parts)

# Survives the auto-refresh: persist which <details id=…> are open in
# sessionStorage (per page URL) and re-apply after each reload. Refresh is a
# JS reload (not <meta refresh>) so we can skip it while text is selected.
SCRIPT = """<script>
(function () {
  var KEY = 'hermes-open:' + location.pathname + location.search;
  var stored = null;
  try { stored = JSON.parse(sessionStorage.getItem(KEY)); } catch (e) {}
  var all = document.querySelectorAll('details[id]');
  if (stored) {                       // re-apply user's open/closed choices
    var open = new Set(stored);
    all.forEach(function (d) { d.open = open.has(d.id); });
  }
  function save() {
    var ids = [];
    document.querySelectorAll('details[id]').forEach(function (d) {
      if (d.open) ids.push(d.id);
    });
    sessionStorage.setItem(KEY, JSON.stringify(ids));
  }
  all.forEach(function (d) { d.addEventListener('toggle', save); });
  if (!stored) save();                // seed with server defaults
  setInterval(function () {           // pause refresh while user has text selected
    if (String(window.getSelection && getSelection() || '').length) return;
    location.reload();
  }, 3000);
})();
</script>"""

def render(path, qs):
    sel_sid = (qs.get("sid") or [None])[0]
    if path.startswith("/user/"):
        view = "users"
        slug = os.path.basename(path[len("/user/"):].strip("/"))
        body = render_user(slug, qs)
    elif path == "/users":
        view = "users"
        body = render_users()
    else:
        view = "sessions"
        body = render_sessions(sel_sid)
    return f"""<!doctype html><meta charset=utf-8>
<title>Hermes debug (temp)</title>
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
 .ustrip{{margin:8px 0}} .ucard{{display:inline-block;border:1px solid #2a4a5a;
   border-radius:4px;padding:3px 8px;margin:2px;text-decoration:none}}
</style>
<h1>Hermes debug dashboard <span class=note>— TEMPORARY, localhost only, read-only,
auto-refresh 3s — {time.strftime('%H:%M:%S')}</span>
&nbsp; <a href='/'{" style='font-weight:bold'" if view == "sessions" else ""}>Sessions</a> ·
<a href='/users'{" style='font-weight:bold'" if view == "users" else ""}>Users</a></h1>
{body}
{SCRIPT}"""

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

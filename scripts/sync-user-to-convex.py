#!/usr/bin/env python3
"""Push users/<slug>/ (history.csv + *.md docs) to Convex prod. Stdlib only.

Usage: python3 scripts/sync-user-to-convex.py [slug]   (default: kartik)
Reads CONVEX_AGENT_KEY from env, repo .env, or ~/.hermes/.env.
"""
import csv
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = "https://cheerful-crow-656.convex.site"
DOC_KINDS = ["preferences", "stats", "profile", "notes"]


def agent_key():
    if os.environ.get("CONVEX_AGENT_KEY"):
        return os.environ["CONVEX_AGENT_KEY"]
    for p in [REPO / ".env", Path.home() / ".hermes/.env"]:
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith("CONVEX_AGENT_KEY="):
                    return line.split("=", 1)[1].strip()
    sys.exit("CONVEX_AGENT_KEY not found")


def post(path, body, key):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Agent-Key": key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "kartik"
    udir = REPO / "users" / slug
    key = agent_key()

    # Orders
    orders = []
    with open(udir / "history.csv", newline="") as f:
        for row in csv.DictReader(f):
            orders.append({
                "date": row["date"],
                "time": row["time"],
                "restaurant": row["restaurant"],
                "restaurantArea": row["restaurant_area"],
                "items": row["items"],
                "amountInr": float(row["amount_inr"] or 0),
                "status": row["status"],
                "orderId": row["order_id"],
                "resId": row["res_id"],
            })
    res = post(f"/u/orders/bulk?id={slug}", {"orders": orders}, key)
    print(f"orders: sent={len(orders)} {res}")

    # Docs
    for kind in DOC_KINDS:
        p = udir / f"{kind}.md"
        if not p.exists():
            print(f"doc {kind}: missing, skipped")
            continue
        res = post(f"/u/doc?id={slug}", {"kind": kind, "content": p.read_text()}, key)
        print(f"doc {kind}: {res}")


if __name__ == "__main__":
    main()

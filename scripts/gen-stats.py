#!/usr/bin/env python3
"""Regenerate users/<slug>/stats.md from history.csv. Usage: python3 scripts/gen-stats.py [slug]"""
import csv, collections, sys, os
slug = sys.argv[1] if len(sys.argv) > 1 else 'kartik'
base = os.path.join(os.path.dirname(__file__), '..', 'users', slug)
rows = list(csv.DictReader(open(os.path.join(base, 'history.csv'))))
ok = [r for r in rows if r['status'] == 'Delivered']
spend = lambda rs: sum(float(r['amount_inr']) for r in rs)
by_year = collections.Counter(r['date'][:4] for r in ok)
spend_year = collections.defaultdict(float)
for r in ok: spend_year[r['date'][:4]] += float(r['amount_inr'])
by_month = collections.defaultdict(lambda: [0, 0.0])
for r in ok:
    m = r['date'][:7]; by_month[m][0] += 1; by_month[m][1] += float(r['amount_inr'])
rest = collections.Counter(r['restaurant'] for r in ok)
items = collections.Counter()
for r in ok:
    for it in r['items'].split(';'):
        name = it.strip().rsplit(' x', 1)[0]
        if name: items[name] += 1
big = max(ok, key=lambda r: float(r['amount_inr']))
hours = collections.Counter()
for r in ok:
    t = r['time']; h = int(t.split(':')[0]) % 12 + (12 if 'PM' in t else 0)
    hours['morning (6-11)' if 6 <= h < 12 else 'lunch (12-16)' if 12 <= h < 17 else 'evening (17-20)' if 17 <= h < 21 else 'night (21-5)'] += 1
with open(os.path.join(base, 'stats.md'), 'w') as f:
    w = f.write
    w(f"# {slug} — precomputed order stats (from history.csv, regenerate with scripts/gen-stats.py)\n\n")
    w(f"- Lifetime: **{len(ok)} delivered orders**, ₹{spend(ok):,.0f} total, avg ₹{spend(ok)/len(ok):,.0f}/order\n")
    w(f"- Biggest order: ₹{float(big['amount_inr']):,.0f} at {big['restaurant']} on {big['date']}\n")
    w("- By year: " + ", ".join(f"{y}: {c} orders (₹{spend_year[y]:,.0f})" for y, c in sorted(by_year.items())) + "\n")
    w("- Time of day: " + ", ".join(f"{k}: {v}" for k, v in hours.most_common()) + "\n\n")
    w("## Top restaurants\n" + "".join(f"- {n} — {c} orders\n" for n, c in rest.most_common(10)))
    w("\n## Most-ordered items\n" + "".join(f"- {n} — {c}×\n" for n, c in items.most_common(15)))
    w("\n## Monthly (last 12)\n" + "".join(f"- {m}: {v[0]} orders, ₹{v[1]:,.0f}\n" for m, v in sorted(by_month.items())[-12:]))
print("wrote", os.path.join(base, 'stats.md'))

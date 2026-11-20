#!/usr/bin/env python3
"""Merge a daily run into data/tips.json (schema v2).

Usage: python3 scripts/merge.py new.json [--window 2026-11-19/2026-11-20] [--edition YYYY-MM-DD]

new.json: {"tips": [...], "sources": [...]}   (either key optional; a legacy "videos" key is read as sources)

What it assigns automatically:
- edition: the America/Denver date of this run (override with --edition). Set only on items that are
  new to the site; existing tips and sources keep the edition that first added them.
- source_id: explicit value if given; else a source whose canonical URL or "posted_in" post matches the
  tip's source_url (so a post sharing a video groups with that video); else the tip's own canonical URL.
  A missing source gets a stub (type from the tip's source_type; title/summary empty).
- subcategory: kept if given (a new name is added to data/taxonomy.json, so subcategories grow with the
  content); otherwise guessed from data/taxonomy.json keywords for the tip's topic.
- Leading source labels ("From the article ...:", "Shared by @x from @y:") are stripped from tip text,
  since every card already links its source. Put attributions in "credit" instead.
Dedupe: tips by id, then by (canonical source_url, title). Sources by id. An incoming source with a summary
updates summary/summary_status ("done" watched, "transcript" captions only, "skipped").
"""
import json, sys, re, datetime, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sitelib import DEN, ROOT, canonical, edition_of, guess_subcategory, assign_source_id, load_taxonomy

P = ROOT / "data/tips.json"
D = json.loads(P.read_text())
TAXP = ROOT / "data/taxonomy.json"
tax = load_taxonomy()
new = json.loads(pathlib.Path(sys.argv[1]).read_text())
arg = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
window = arg("--window")
now = datetime.datetime.now(DEN).replace(microsecond=0).isoformat()
edition = arg("--edition") or edition_of(now)

LABEL = re.compile(r"^(?:(?:From|Shared(?: approvingly)?(?: by @\w+)?|Endorsed(?: by @\w+)?|Highlighted(?: by @\w+)?|Example)"
                   r"\b[^:]{0,140}?:\s+)", re.I)
def clean(text):
    m = LABEL.match(text)
    if not m: return text
    rest = text[m.end():]
    print(f"  stripped source label: {m.group(0)!r}")
    return rest[:1].upper() + rest[1:]

sources = D.setdefault("sources", [])
by_sid = {s["id"]: s for s in sources}
s_added = s_upd = 0
for s in new.get("sources", []) + [dict(v, author=v.get("poster"), url=v.get("source_url"), type="video") for v in new.get("videos", [])]:
    s.pop("poster", None); s.pop("source_url", None)
    s.setdefault("id", canonical(s["url"]))
    if s["id"] in by_sid:
        cur = by_sid[s["id"]]
        if s.get("summary"):
            cur["summary"] = s["summary"]; cur["summary_status"] = s.get("summary_status", "done"); s_upd += 1
        for k, v in s.items(): cur.setdefault(k, v)
        continue
    s.setdefault("added_at", now); s["edition"] = edition
    if s.get("type") == "video": s.setdefault("summary_status", "coming")
    sources.append(s); by_sid[s["id"]] = s; s_added += 1

by_id = {t["id"]: t for t in D["tips"]}
seen = {(canonical(t["source_url"]), t["title"]) for t in D["tips"]}
added, new_subs = 0, []
for t in new.get("tips", []):
    if t["id"] in by_id:
        for k, v in t.items(): by_id[t["id"]].setdefault(k, v)
        continue
    key = (canonical(t["source_url"]), t["title"])
    if key in seen: continue
    t["tip"] = clean(t["tip"])
    t.setdefault("added_at", now); t["edition"] = edition
    names = [x["name"] for x in tax.setdefault(t["topic"], [])]
    if not t.get("subcategory"):
        t["subcategory"] = guess_subcategory(t, tax)
    elif t["subcategory"] not in names:
        tax[t["topic"]].append({"name": t["subcategory"], "keywords": []}); new_subs.append(f'{t["topic"]} › {t["subcategory"]}')
    t["source_id"] = assign_source_id(t, sources)
    if t["source_id"] not in by_sid:
        st = t.get("source_type", "post")
        s = dict(id=t["source_id"], type=st if st in ("post", "article", "video", "thread") else "post", title=None,
                 author=t["author"], url=re.sub(r"[?&]t=\d+s?$", "", t["source_url"]), date=t["date"],
                 added_at=now, edition=edition)
        sources.append(s); by_sid[s["id"]] = s; s_added += 1
    D["tips"].append(t); by_id[t["id"]] = t; seen.add(key); added += 1
if new_subs: TAXP.write_text(json.dumps(tax, indent=1, ensure_ascii=False) + "\n")
D["schema_version"] = 2
D["last_run"] = now
D.setdefault("runs", []).append({"at": now, "edition": edition, "window": window, "tips_added": added,
                                 "sources_added": s_added, "source_summaries_updated": s_upd})
P.write_text(json.dumps(D, indent=1, ensure_ascii=False))
print(f"merged into edition {edition}: +{added} tips, +{s_added} sources, {s_upd} summaries updated; "
      f"total {len(D['tips'])} tips / {len(sources)} sources" + (f"; new subcategories: {new_subs}" if new_subs else ""))

#!/usr/bin/env python3
"""Rebuild the static site from data/tips.json (schema v2: tips + sources, editions, subcategories).

Usage: python3 scripts/build.py
Daily runs: python3 scripts/merge.py new.json, then this, then commit + push.
"""
import json, html, re, datetime, hashlib, pathlib, sys
from collections import Counter, defaultdict
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sitelib import DEN, ROOT, canonical, assign_source_id, load_taxonomy, edition_of

D = json.loads((ROOT / "data/tips.json").read_text())
TAX = load_taxonomy()
SITE = D["site"]; BASE = SITE["base_url"]; TITLE = SITE["title"]
TAGLINE = SITE.get("tagline") or f"Searchable reference of AI tips from {len(D['accounts'])} builders on X"
SCOPE_SHORT = SITE.get("scope_short", "AI tools")
SCOPE_ABOUT = SITE.get("scope_about", "AI tools")
TOPIC_ORDER = list(TAX)
e = lambda s: html.escape(str(s or ""), quote=True)
def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
def dlabel(d, year=True): return datetime.date.fromisoformat(d).strftime("%b %-d, %Y" if year else "%b %-d")

tips = sorted(D["tips"], key=lambda t: t["posted_at"], reverse=True)
sources = {s["id"]: s for s in D["sources"]}
# ---- validate / backfill so the page never breaks on a partial merge ----
for t in tips:
    t.setdefault("edition", edition_of(t["added_at"]))
    t.setdefault("subcategory", "Other")
    if not t.get("source_id"): t["source_id"] = assign_source_id(t, list(sources.values()))
    if t["source_id"] not in sources:
        sources[t["source_id"]] = dict(id=t["source_id"], type=t.get("source_type", "post"), author=t["author"],
                                      url=t["source_url"], date=t["date"], added_at=t["added_at"], edition=t["edition"])
for s in sources.values(): s.setdefault("edition", edition_of(s["added_at"]))

by_src = defaultdict(list)
for t in tips: by_src[t["source_id"]].append(t)
def tsec(t):
    ts = t.get("video_timestamp")
    if not ts: return -1
    p = [int(x) for x in ts.split(":")]; return sum(x * 60 ** i for i, x in enumerate(reversed(p)))
for v in by_src.values(): v.sort(key=lambda t: (tsec(t), t["posted_at"]))

def home(s):
    """Main (topic, subcategory) of a source: the one holding most of its tips; ties go to the earliest tip."""
    ts = by_src.get(s["id"], [])
    if not ts: return (s.get("topic", "Other"), s.get("subcategory", "Other"))
    c = Counter((t["topic"], t["subcategory"]) for t in ts)
    best = max(c.values())
    for t in ts:
        if c[(t["topic"], t["subcategory"])] == best: return (t["topic"], t["subcategory"])
for s in sources.values(): s["_home"] = home(s)
def sort_key(s):
    ts = by_src.get(s["id"], [])
    return max([t["posted_at"] for t in ts] or [s["date"]])

topics = sorted({t["topic"] for t in tips} | {s["_home"][0] for s in sources.values()},
                key=lambda x: (TOPIC_ORDER.index(x) if x in TOPIC_ORDER else 99, x))
def subs_of(tp):
    present = {t["subcategory"] for t in tips if t["topic"] == tp} | {s["_home"][1] for s in sources.values() if s["_home"][0] == tp}
    order = [x["name"] for x in TAX.get(tp, [])]
    return sorted(present, key=lambda x: (order.index(x) if x in order else 99, x))
tip_count = Counter((t["topic"], t["subcategory"]) for t in tips)
topic_count = Counter(t["topic"] for t in tips)
editions = sorted({t["edition"] for t in tips} | {s["edition"] for s in sources.values()}, reverse=True)
latest = editions[0]
authors = sorted({t["author"] for t in tips} | {s["author"] for s in sources.values()}, key=str.lower)
last_run = datetime.datetime.fromisoformat(D["last_run"])
last_run_label = last_run.astimezone(DEN).strftime("%b %-d, %Y, %-I:%M %p") + " MT"
n_videos = sum(1 for s in sources.values() if s["type"] == "video")

css_v = hashlib.md5((ROOT / "assets/site.css").read_bytes()).hexdigest()[:8]
js_v = hashlib.md5((ROOT / "assets/app.js").read_bytes()).hexdigest()[:8]

def head(title, desc, path, depth):
    pre = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{BASE}{path}">
<meta name="color-scheme" content="light dark">
<script>(function(){{var d=document.documentElement,t=null;try{{t=localStorage.getItem('theme')}}catch(e){{}}if(t!=='light'&&t!=='dark'){{t=window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}}d.setAttribute('data-theme',t)}})();</script>
<link rel="icon" href="{pre}favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/atom+xml" title="{TITLE} (Atom feed)" href="{BASE}feed.xml">
<link rel="stylesheet" href="{pre}assets/site.css?v={css_v}">
<meta property="og:site_name" content="{TITLE}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{BASE}{path}">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="wrap top-in">
    <a class="brand" href="{pre or './'}"><span class="logo" aria-hidden="true">◆</span> {TITLE}</a>
    <nav>
      <a href="{pre or './'}#latest">Latest</a>
      <a href="{pre or './'}#topics">Topics</a>
      <a href="{pre or './'}?type=video#topics">Videos</a>
      <a href="{pre}archive/">Archive</a>
      <a href="{pre}about/">About</a>
      <button class="theme" type="button" aria-label="Toggle dark mode" onclick="(function(d){{var t=d.getAttribute('data-theme')==='dark'?'light':'dark';d.setAttribute('data-theme',t);try{{localStorage.setItem('theme',t)}}catch(e){{}}}})(document.documentElement)">◐</button>
    </nav>
  </div>
</header>
"""

def foot(depth):
    pre = "../" * depth
    return f"""<footer class="foot"><div class="wrap">
<p>{TITLE} is compiled from public posts and videos on X and YouTube. Each tip is paraphrased and links to its exact source. Last updated {e(last_run_label)}. <a href="{BASE}feed.xml">Atom feed</a> · <a href="{pre}data/tips.json">tips.json</a></p>
</div></footer>
</body></html>
"""

TYPE_LABEL = {"post": "Post", "article": "Article", "video": "Video", "thread": "Thread"}
def dur(s):
    d = s.get("duration_s")
    if not d: return ""
    m, sec = divmod(d, 60)
    return f"{m // 60}h {m % 60}m" if m >= 60 else f"{m}:{sec:02d}"

def tip_li(t, s, card_home):
    is_vid = s["type"] == "video" and t.get("video_timestamp")
    if is_vid and canonical(t["source_url"]).startswith("yt-"):
        lead = f'<a class="ts" href="{e(t["source_url"])}" target="_blank" rel="noopener" title="Watch from {e(t["video_timestamp"])}">▶ {e(t["video_timestamp"])}</a> '
    elif is_vid:
        lead = f'<span class="ts" title="Timestamp in the video">▶ {e(t["video_timestamp"])}</span> '
    else: lead = ""
    badges = ""
    if t.get("transcript_only"): badges += ' <span class="badge tr">from transcript</span>'
    if t["edition"] != s["edition"]: badges += f' <span class="badge ed">{e(dlabel(t["edition"], False))} edition</span>'
    if (t["topic"], t["subcategory"]) != card_home:
        badges += f' <a class="xsub" href="#sc-{slug(t["topic"])}-{slug(t["subcategory"])}">{e(t["topic"])} › {e(t["subcategory"])}</a>'
    credit = f' <span class="credit">{e(t["credit"])}</span>' if t.get("credit") else ""
    own = "" if canonical(t["source_url"]) in (s["id"], canonical(s.get("url")), canonical(s.get("posted_in"))) or (is_vid) \
        else f' <a class="tsrc" href="{e(t["source_url"])}" target="_blank" rel="noopener">source ↗</a>'
    rel = "".join(f' <a class="tsrc" href="{e(u)}" target="_blank" rel="noopener">related ↗</a>' for u in t.get("related_urls", []))
    search = " ".join([t["title"], t["tip"], t["author"], t["topic"], t["subcategory"], " ".join(t.get("tags", [])), t.get("credit") or ""]).lower()
    return f"""<li class="t" id="{e(t['id'])}" data-topic="{e(t['topic'])}" data-subcat="{e(t['topic'] + '|' + t['subcategory'])}" data-edition="{e(t['edition'])}" data-author="{e(t['author'])}" data-search="{e(search)}">{lead}<strong>{e(t['title'])}.</strong> {e(t['tip'])}{badges}{credit}{own}{rel} <a class="perma" href="#{e(t['id'])}" aria-label="Link to this tip">#</a></li>"""

def card(s, place=None):
    """One card per source. place=(topic, sub) renders a filter-only mirror holding just that subcategory's tips."""
    hm = place or s["_home"]
    ts = [t for t in by_src.get(s["id"], []) if not place or (t["topic"], t["subcategory"]) == place]
    typ = s["type"]
    label = TYPE_LABEL.get(typ, "Source") + (f" · {dur(s)}" if dur(s) else "")
    date = s["date"] if typ == "video" or not ts else min(t["date"] for t in ts)
    compact = len(ts) == 1 and not s.get("title") and not s.get("summary")
    title = s.get("title") or (ts[0]["title"] if len(ts) == 1 else f"Post by @{s['author']}")
    link_text = {"video": "Watch video", "article": "Read article", "post": "View post on X"}.get(typ, "Open source")
    summary = ""
    st = s.get("summary_status")
    if typ == "video":
        if st == "done" and s.get("summary"): summary = f'<p class="sum">{e(s["summary"])}</p>'
        elif st == "transcript" and s.get("summary"): summary = f'<p class="sum"><span class="badge tr">from transcript</span> {e(s["summary"])}</p>'
        elif st == "skipped": summary = f'<p class="sum"><span class="badge skip">Not summarized</span> {e(s.get("note"))}</p>'
        else: summary = '<p class="sum"><span class="badge wait">Video summary coming</span></p>'
        if s.get("note") and st != "skipped": summary += f'<p class="note">{e(s["note"])}</p>'
    elif s.get("summary"): summary = f'<p class="sum">{e(s["summary"])}</p>'
    shared = f' · <a href="{e(s["posted_in"])}" target="_blank" rel="noopener">shared in this post ↗</a>' if s.get("posted_in") and canonical(s["posted_in"]) != canonical(s["url"]) else ""
    head_search = " ".join([title, s["author"], s.get("summary") or "", label, hm[0], hm[1]]).lower()
    ident = f'data-mirror="s-{e(s["id"])}"' if place else f'id="s-{e(s["id"])}"'
    attrs = (f'{ident} class="card{" compact" if compact else ""}{" mirror" if place else ""}" data-type="{e(typ)}" data-author="{e(s["author"])}" '
             f'data-edition="{e(s["edition"])}" data-topic="{e(hm[0])}" data-subcat="{e(hm[0] + "|" + hm[1])}" data-head="{e(head_search)}" data-n="{len(ts)}"')
    meta = f'<div class="meta"><span class="type {e(typ)}">{e(label)}</span> <span>@{e(s["author"])}</span> <time datetime="{e(date)}">{dlabel(date)}</time> <span class="badge ed" title="Edition that first added this">{e(dlabel(s["edition"], False))} edition</span></div>'
    srcline = f'<p class="src"><a href="{e(s["url"])}" target="_blank" rel="noopener">{link_text} ↗</a>{shared}</p>'
    if compact:
        t = ts[0]
        li = tip_li(t, s, hm)
        body = li.replace('<li class="t"', '<p class="t one"', 1)[:-5] + "</p>"
        body = body.replace(f"<strong>{e(t['title'])}.</strong> ", "", 1)
        if place: body = re.sub(r' id="[^"]+"', "", body, count=1)
        return f"<article {attrs}{' hidden' if place else ''}>\n{meta}\n<h3>{e(t['title'])}</h3>\n{body}\n{srcline}\n</article>"
    others = Counter((t["topic"], t["subcategory"]) for t in ts if (t["topic"], t["subcategory"]) != hm)
    lis = "\n".join(tip_li(t, s, hm) for t in ts)
    if place: lis = re.sub(r'<li class="t" id="[^"]+"', '<li class="t"', lis)
    mirror_note = f'<p class="note">Part of a source filed under {e(s["_home"][0])} › {e(s["_home"][1])}; showing the {len(ts)} tip{"s" if len(ts) != 1 else ""} filed here.</p>' if place else ""
    ul = f'<ul class="tips">\n{lis}\n</ul>' if ts else ""
    count = f'<span class="n">{len(ts)} tip{"s" if len(ts) != 1 else ""}</span>' if ts else ""
    return f"""<article {attrs}{' hidden' if place else ''}>
{meta}
<h3><a href="{e(s['url'])}" target="_blank" rel="noopener">{e(title)} ↗</a> {count}</h3>
{mirror_note}{summary if not place else ""}
{ul}
{srcline}
</article>"""

# ---------- index ----------
see_also = defaultdict(list)   # (topic, sub) -> [(source, n)]
for s in sources.values():
    for k, n in Counter((t["topic"], t["subcategory"]) for t in by_src.get(s["id"], [])).items():
        if k != s["_home"]: see_also[k].append((s, n))
sections = ""
for tp in topics:
    subs_html = ""
    for sc in subs_of(tp):
        here = sorted([s for s in sources.values() if s["_home"] == (tp, sc)], key=sort_key, reverse=True)
        cards = "\n".join(card(s) for s in here)
        sa = "".join(f'<li data-src="s-{e(s["id"])}" data-subcat="{e(tp + "|" + sc)}"><a href="#s-{e(s["id"])}">{e(s.get("title") or by_src[s["id"]][0]["title"])}</a> <span>({n} tip{"s" if n != 1 else ""} here; card is under {e(s["_home"][0])} › {e(s["_home"][1])})</span></li>'
                     for s, n in sorted(see_also.get((tp, sc), []), key=lambda x: sort_key(x[0]), reverse=True))
        sa = f'<div class="seealso"><span>See also:</span><ul>{sa}</ul></div>' if sa else ""
        sa += "\n".join(card(s, (tp, sc)) for s, n in sorted(see_also.get((tp, sc), []), key=lambda x: sort_key(x[0]), reverse=True))
        subs_html += f'<section class="subcat" id="sc-{slug(tp)}-{slug(sc)}" data-subcat="{e(tp + "|" + sc)}"><h3 class="sch">{e(sc)} <span class="count">{tip_count[(tp, sc)] or "no tips yet"}</span></h3>\n{cards}\n{sa}\n</section>\n'
    sections += f'<section class="topic" id="t-{slug(tp)}" data-topic="{e(tp)}"><h2>{e(tp)} <span class="count">{topic_count[tp]}</span></h2>\n{subs_html}</section>\n'

toc = ""
for tp in topics:
    sub_li = "".join(f'<li><a href="#sc-{slug(tp)}-{slug(sc)}">{e(sc)}</a> <span>{tip_count[(tp, sc)]}</span></li>' for sc in subs_of(tp))
    toc += f'<li><a class="tt" href="#t-{slug(tp)}">{e(tp)}</a> <span>{topic_count[tp]}</span><ul>{sub_li}</ul></li>'

def edition_index(ed):
    """Compact topic → subcategory index of one edition's tips and sources, linking to cards."""
    out = ""
    for tp in topics:
        rows = ""
        for sc in subs_of(tp):
            items = []
            for s in sorted(sources.values(), key=sort_key, reverse=True):
                mine = [t for t in by_src.get(s["id"], []) if t["edition"] == ed and (t["topic"], t["subcategory"]) == (tp, sc)]
                if mine or (not by_src.get(s["id"]) and s["edition"] == ed and s["_home"] == (tp, sc)):
                    nm = s.get("title") or (mine[0]["title"] if mine else s["id"])
                    target = f"s-{s['id']}" if (len(mine) != 1 or s.get("title")) else mine[0]["id"]
                    items.append(f'<li><a href="#{e(target)}">{e(nm)}</a>{f" <span>{len(mine)}</span>" if len(mine) > 1 else ""}</li>')
            if items: rows += f'<div class="eisub"><h4>{e(sc)}</h4><ul>{"".join(items)}</ul></div>'
        if rows: out += f'<div class="eitopic"><h3>{e(tp)}</h3>{rows}</div>'
    return out
ed_tips = sum(1 for t in tips if t["edition"] == latest)
ed_srcs = sum(1 for s in sources.values() if s["edition"] == latest or any(t["edition"] == latest for t in by_src.get(s["id"], [])))
ed_runs = [r for r in D.get("runs", []) if r.get("edition", edition_of(r["at"])) == latest]
banner = f"""<section class="latest" id="latest" data-edition="{latest}">
  <p class="kicker">Latest edition</p>
  <h2>{dlabel(latest)} <span class="count">{ed_tips} tips · {ed_srcs} sources</span></h2>
  <p class="hint">Everything first added on {dlabel(latest)}{f" ({len(ed_runs)} runs)" if len(ed_runs) > 1 else ""}. Older editions stay in the topics below and in the edition menu.</p>
  <div class="latest-actions"><button type="button" class="btn" id="only-latest" data-edition="{latest}">Show only this edition</button></div>
  <details class="edindex"><summary>What's in this edition, by topic</summary>{edition_index(latest)}</details>
</section>"""

chips = "".join(f'<button type="button" class="chip" data-topic="{e(tp)}" aria-pressed="false">{e(tp)} <span>{topic_count[tp]}</span></button>' for tp in topics)
author_opts = "".join(f'<option value="{e(a)}">@{e(a)}</option>' for a in authors)
sub_opts = "".join(f'<optgroup label="{e(tp)}">' + "".join(f'<option value="{e(tp + "|" + sc)}">{e(sc)} ({tip_count[(tp, sc)]})</option>' for sc in subs_of(tp)) + "</optgroup>" for tp in topics)
ed_opts = "".join(f'<option value="{ed}">{dlabel(ed)}{" (latest)" if ed == latest else ""} · {sum(1 for t in tips if t["edition"] == ed)} tips</option>' for ed in editions)
type_counts = Counter(s["type"] for s in sources.values())
type_opts = "".join(f'<option value="{k}">{TYPE_LABEL[k]}s ({type_counts[k]})</option>' for k in ["post", "article", "video", "thread"] if type_counts[k])
desc = f"{len(tips)} tips from {len(sources)} sources across {len(topics)} topics on {SCOPE_SHORT}, each linked to its source."
index = head(f"{TITLE}: {TAGLINE}", desc, "", 0) + f"""
<main id="main" class="wrap">
<section class="hero">
  <h1>{TITLE}</h1>
  <p class="lede">{e(TAGLINE)}. Tips are grouped by the post, article or video they come from, and every one links to its exact source. Updated daily.</p>
  <p class="stats"><strong>{len(tips)}</strong> tips · <strong>{len(sources)}</strong> sources ({n_videos} videos) · <strong>{len(topics)}</strong> topics · updated {e(last_run_label)}</p>
</section>
{banner}
<div class="controls" role="search">
  <label class="sr" for="q">Search tips</label>
  <input id="q" type="search" placeholder="Search tips, e.g. lint, voice, meetings, routines" autocomplete="off">
  <div class="selects">
    <label class="sr" for="edition">Edition</label><select id="edition"><option value="">All editions</option>{ed_opts}</select>
    <label class="sr" for="subcat">Subcategory</label><select id="subcat"><option value="">All subcategories</option>{sub_opts}</select>
    <label class="sr" for="author">Author</label><select id="author"><option value="">All authors</option>{author_opts}</select>
    <label class="sr" for="type">Source type</label><select id="type"><option value="">All source types</option>{type_opts}</select>
  </div>
  <div class="chips" aria-label="Filter by topic">{chips}</div>
  <p id="status" class="status" aria-live="polite"></p>
</div>
<nav class="toc" id="topics" aria-label="Topics"><h2>Topics</h2><ul class="tocl">{toc}</ul>
<p class="hint">Counts are tips. <a href="?type=video#topics">Show only videos</a> ({n_videos}).</p></nav>
<div id="browse">
{sections}
</div>
<p id="none" class="empty" hidden>No tips match. Try fewer words or <button type="button" class="linkbtn" id="clear">clear all filters</button>.</p>
</main>
<script src="assets/app.js?v={js_v}" defer></script>
""" + foot(0)
(ROOT / "index.html").write_text(index)

# ---------- archive ----------
rows = ""
for t in tips:
    s = sources[t["source_id"]]
    rows += (f'<tr data-search="{e((t["title"]+" "+t["tip"]+" "+t["author"]+" "+t["topic"]+" "+t["subcategory"]+" "+t["edition"]+" "+(s.get("title") or "")).lower())}">'
             f'<td><time>{e(t["date"])}</time></td><td>{e(t["edition"])}</td><td>@{e(t["author"])}</td><td>{e(t["topic"])}</td><td>{e(t["subcategory"])}</td>'
             f'<td><a href="../#{e(t["id"])}">{e(t["title"])}</a></td>'
             f'<td><a href="{e(t["source_url"])}" target="_blank" rel="noopener">{TYPE_LABEL.get(s["type"], "source").lower()}{(" @ "+e(t["video_timestamp"])) if t.get("video_timestamp") else ""} ↗</a></td></tr>\n')
archive = head(f"Archive · {TITLE}", "Every tip, newest first.", "archive/", 1) + f"""
<main id="main" class="wrap wide">
<h1>Archive</h1>
<p class="lede">All {len(tips)} tips, newest first by post date. Editions: {len(editions)} (latest {dlabel(latest)}). Runs so far: {len(D.get('runs', []))}.</p>
<label class="sr" for="aq">Filter archive</label>
<input id="aq" type="search" placeholder="Filter the archive (try a date like {latest})" autocomplete="off" oninput="var q=this.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(function(r){{r.hidden=q&&r.dataset.search.indexOf(q)<0}})">
<div class="tablewrap"><table class="archive"><thead><tr><th>Posted</th><th>Edition</th><th>Author</th><th>Topic</th><th>Subcategory</th><th>Tip</th><th>Source</th></tr></thead><tbody>
{rows}</tbody></table></div>
</main>
""" + foot(1)
(ROOT / "archive").mkdir(exist_ok=True); (ROOT / "archive/index.html").write_text(archive)

# ---------- about ----------
accts = ", ".join(f'<a href="https://x.com/{a}" target="_blank" rel="noopener">@{a}</a>' for a in D["accounts"])
about = head(f"About · {TITLE}", f"What {TITLE} is and how it's made.", "about/", 1) + f"""
<main id="main" class="wrap prose">
<h1>About</h1>
<p>{TITLE} collects practical tips about {SCOPE_ABOUT} from a fixed list of builders on X: {accts}.</p>{("<p>" + e(SITE["scope_note"]) + "</p>") if SITE.get("scope_note") else ""}
<h2>How it works</h2>
<ul>
<li>A daily run reads these accounts' recent public posts (plus threads, quoted posts and linked videos), keeps only practical {SITE.get("keep_rule", "AI-tooling")} content, and merges new tips into <a href="../data/tips.json">data/tips.json</a>, deduplicated by source.</li>
<li>Tips are paraphrased, not quoted verbatim, and every one links to its exact source post, article or video (with a timestamp when it comes from a video). When an account shares someone else's post, the original author is credited.</li>
<li>Nothing is invented: no numbers or claims appear that aren't in the source. Video summaries are added only after a video has been watched; tips marked "from transcript" were written from auto-captions only.</li>
<li>Each topic is split into subcategories that come from the content. Tips from the same post, article or video are grouped into one card; when a source's tips span subcategories, the card sits in the subcategory holding most of its tips and the others get a "See also" link.</li>
<li>Every item belongs to an <strong>edition</strong>: the date (Mountain Time) of the daily run that first added it. The top of the home page shows the latest edition; use the edition menu to view any single edition.</li>
<li>Off-topic posts are skipped.</li>
</ul>
<p>Last updated {e(last_run_label)}.</p>
</main>
""" + foot(1)
(ROOT / "about").mkdir(exist_ok=True); (ROOT / "about/index.html").write_text(about)

# ---------- 404 ----------
nf = head(f"Not found · {TITLE}", "Page not found.", "404.html", 0).replace('href="favicon.svg"', f'href="{BASE}favicon.svg"').replace('href="assets/', f'href="{BASE}assets/').replace('href="archive/', f'href="{BASE}archive/').replace('href="about/', f'href="{BASE}about/').replace('href="./', f'href="{BASE}') + f"""
<main id="main" class="wrap prose"><h1>Not found</h1><p>That page doesn't exist. Try the <a href="{BASE}">tips index</a> or the <a href="{BASE}archive/">archive</a>.</p></main>
""" + foot(0)
(ROOT / "404.html").write_text(nf)

# ---------- sitemap, feed, robots ----------
(ROOT / "sitemap.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{BASE}</loc><lastmod>{last_run.date().isoformat()}</lastmod></url>
  <url><loc>{BASE}archive/</loc><lastmod>{last_run.date().isoformat()}</lastmod></url>
  <url><loc>{BASE}about/</loc></url>
</urlset>
""")
entries = ""
def src_updated(s): return max([s["added_at"]] + [t["added_at"] for t in by_src.get(s["id"], [])])
for s in sorted(sources.values(), key=lambda s: (src_updated(s), sort_key(s)), reverse=True)[:60]:
    ts = by_src.get(s["id"], [])
    title = s.get("title") or (ts[0]["title"] if ts else s["id"])
    body = (s.get("summary") or "") + "".join(f"\n• {(t.get('video_timestamp') + ' ') if t.get('video_timestamp') else ''}{t['title']}: {t['tip']}" for t in ts)
    entries += f"""  <entry>
    <title>{e(s['_home'][0])} › {e(s['_home'][1])}: {e(title)}</title>
    <link rel="alternate" type="text/html" href="{BASE}#s-{e(s['id'])}"/>
    <link rel="related" href="{e(s['url'])}"/>
    <id>{BASE}#s-{e(s['id'])}</id>
    <published>{e(min([t['posted_at'] for t in ts] or [s['date'] + 'T00:00:00Z']))}</published>
    <updated>{e(src_updated(s))}</updated>
    <author><name>@{e(s['author'])}</name></author>
    <category term="edition-{e(s['edition'])}"/>
    <summary>{e(body.strip())} (Source: {e(s['url'])})</summary>
  </entry>
"""
(ROOT / "feed.xml").write_text(f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{TITLE}</title>
  <subtitle>{e(TAGLINE)}</subtitle>
  <link rel="self" type="application/atom+xml" href="{BASE}feed.xml"/>
  <link rel="alternate" type="text/html" href="{BASE}"/>
  <id>{BASE}</id>
  <updated>{last_run.isoformat()}</updated>
  <author><name>{TITLE}</name></author>
{entries}</feed>
""")
(ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n")
(ROOT / ".nojekyll").write_text("")
print(f"built: {len(tips)} tips, {len(sources)} sources, {len(topics)} topics, {sum(len(subs_of(t)) for t in topics)} subcategories, editions {editions}")

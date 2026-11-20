"""Shared helpers for merge.py and build.py: source keys, editions, subcategory guessing."""
import re, json, datetime, pathlib
from zoneinfo import ZoneInfo

DEN = ZoneInfo("America/Denver")
ROOT = pathlib.Path(__file__).resolve().parent.parent

def canonical(url):
    """Stable key for a source URL (drops timestamps, tracking params, host variants)."""
    if not url: return None
    u = url.strip()
    m = re.search(r"(?:youtube\.com/(?:watch\?v=|live/)|youtu\.be/)([\w-]{11})", u)
    if m: return f"yt-{m.group(1)}"
    m = re.search(r"(?:x|twitter)\.com/i/broadcasts/(\w+)", u)
    if m: return f"x-broadcast-{m.group(1)}"
    m = re.search(r"(?:x|twitter)\.com/(?:[^/]+|i)/status/(\d+)", u)
    if m: return f"x-{m.group(1)}"
    m = re.search(r"(?:x|twitter)\.com/i/article/(\d+)", u)
    if m: return f"x-article-{m.group(1)}"
    u = re.sub(r"[?#].*$", "", u).rstrip("/")
    return "url-" + re.sub(r"[^a-z0-9]+", "-", u.lower().split("://", 1)[-1]).strip("-")

def edition_of(ts_iso):
    """Edition = America/Denver calendar date of the run that first added the item."""
    return datetime.datetime.fromisoformat(ts_iso).astimezone(DEN).date().isoformat()

def load_taxonomy():
    return json.loads((ROOT / "data/taxonomy.json").read_text())

def guess_subcategory(tip, taxonomy):
    """Pick a subcategory for tip['topic'] by keyword hits on title/tip/tags; falls back to the topic's last subcategory."""
    subs = taxonomy.get(tip["topic"], [])
    if not subs: return "General"
    text = " ".join([tip.get("title", ""), tip.get("tip", ""), " ".join(tip.get("tags", []))]).lower()
    best, score = subs[-1]["name"], 0
    for s in subs:
        n = sum(text.count(k) for k in s.get("keywords", []))
        if n > score: best, score = s["name"], n
    return best

def assign_source_id(tip, sources):
    """Group a tip with its source: explicit source_id wins; else a video whose page or sharing post
    matches the tip's link; else the tip's own canonical source URL."""
    if tip.get("source_id"): return tip["source_id"]
    key = canonical(tip["source_url"])
    for s in sources:
        if s["id"] == key or canonical(s.get("posted_in")) == key:
            return s["id"]
    return key

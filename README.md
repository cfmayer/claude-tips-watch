# Claude Tips Watch

Searchable reference of Claude and Claude Code tips from 16 accounts on X. Live at https://cfmayer.github.io/claude-tips-watch/

- `data/tips.json` (schema v2): `tips` and `sources`, plus `last_run` and a run log.
  - Tip: `id`, `date`, `posted_at`, `author`, `topic`, `subcategory`, `edition`, `source_id`, `tags`, `title`, `tip`, `credit`, `source_url`, `source_type`, `video_timestamp`, `transcript_only`, `related_urls`, `added_at`.
  - Source (post, article, video or thread): `id`, `type`, `title`, `author`, `url`, `posted_in`, `date`, `edition`, `summary`, `summary_status`, `duration_s`, `added_at`.
  - `edition` = America/Denver date of the run that first added the item.
- `data/taxonomy.json`: topics → ordered subcategories with keywords for auto-assignment.
- `scripts/merge.py new.json [--window A/B] [--edition YYYY-MM-DD]`: merge a daily run. Assigns edition, source grouping and (if missing) subcategory; dedupes by id and by source+title; strips "From the article…:"-style labels.
- `scripts/build.py`: regenerate `index.html` (latest-edition banner, topic → subcategory sections of source cards), `archive/`, `about/`, `404.html`, `sitemap.xml`, `feed.xml`.
- `scripts/sitelib.py`: shared helpers (canonical source keys, editions, subcategory guessing).

Daily run: collect, write `new.json`, then `python3 scripts/merge.py new.json && python3 scripts/build.py && git add -A && git commit -m "Daily update" && git push`.

Site text (title, tagline, scope) lives in `data/tips.json` → `site`. Sister sites: [Grok Bot Tips Watch](https://cfmayer.github.io/ai-tips-watch/), [Claude Tips Watch](https://cfmayer.github.io/claude-tips-watch/), [ChatGPT Tips Watch](https://cfmayer.github.io/chatgpt-tips-watch/).

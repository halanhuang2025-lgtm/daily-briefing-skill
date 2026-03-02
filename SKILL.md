---
name: daily-briefing
description: Daily news briefing aggregator that fetches and delivers content from 5 sources — Readhub (Chinese tech news), Karpathy-recommended RSS feeds (92 HN popular blogs), GitHub Trending, Hacker News top stories, and V2EX hot topics — with summaries for each item. Use when setting up a daily automated briefing, running an on-demand news digest, or configuring a morning push notification via cron. Triggers on "每日资讯", "daily briefing", "早报", "新闻推送", or requests to aggregate news from HN/GitHub/V2EX/Readhub.
---

# Daily Briefing Skill

Aggregates 5 news sources into a formatted daily digest with summaries. Designed for Telegram push via OpenClaw cron.

## Sources

| # | Source | API / Method |
|---|--------|-------------|
| 1 | **Readhub 早报** | `https://api.readhub.cn/daily` — Chinese tech news with full summaries |
| 2 | **Karpathy RSS** | 92 HN popular blogs OPML, concurrent fetch, latest posts with descriptions |
| 3 | **GitHub Trending** | Scrape `github.com/trending` + GitHub API for repo descriptions & stars |
| 4 | **Hacker News** | Firebase API `hacker-news.firebaseio.com/v0/topstories.json` |
| 5 | **V2EX 热帖** | `https://www.v2ex.com/api/topics/hot.json` |

## Quick Start

### Run once (on-demand)

```bash
python3 scripts/daily-briefing.py 2>/dev/null
```

Output is Markdown-formatted, suitable for direct Telegram send.

### Set up daily cron (08:00 CST)

```bash
openclaw cron add \
  --name "每日资讯早报" \
  --cron "0 8 * * *" \
  --session isolated \
  --announce \
  --channel telegram \
  --thinking low \
  --message "运行 python3 <workspace>/scripts/daily-briefing.py 2>/dev/null 并将完整输出分段发送到 Telegram 主群"
```

Replace `<workspace>` with actual path (e.g. `/Users/you/.openclaw/workspace-main`).

### Send output to Telegram (split by section)

The output is ~200 lines. Split into 4 messages by section (📰 / 🔖 / ⭐ / 🔥+💬) to stay under Telegram's 4096-char limit.

## Script Details

**File:** `scripts/daily-briefing.py`

- Pure Python stdlib only — no pip dependencies
- Concurrent fetching: 25 workers for RSS feeds, 10 for HN items, 8 for GitHub API
- Total runtime: ~25 seconds
- Karpathy OPML source: `https://gist.githubusercontent.com/emschwartz/e6d2bf860ccc367fe37ff953ba6de66b/raw/hn-popular-blogs-2025.opml`

## Customization

**Change number of items per section** — edit the `n=` parameter in each `get_*()` call in `main()`:
```python
readhub  = get_readhub(8)        # default 8
rss      = get_karpathy_rss(10)  # default 10
gh       = get_github_trending(8) # default 8
hn       = get_hn_top(8)         # default 8
v2       = get_v2ex_hot(8)       # default 8
```

**Disable a section** — comment out its block in `main()`.

**Change RSS feed list** — the script dynamically fetches the OPML from GitHub Gist on each run. To use a static local list instead, replace `load_opml_feeds()` return value with a hardcoded list.

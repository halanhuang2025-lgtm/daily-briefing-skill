# 📅 Daily Briefing Skill for OpenClaw

An OpenClaw agent skill that aggregates **5 news sources** into a formatted daily digest with summaries — designed for Telegram push via cron.

## Preview

```
📅 2026-03-02 每日资讯

📰 Readhub 早报
1. 多家航司公布涉中东机票退改方案
   > 受中东局势影响，国航、东航、南航等航空公司发布特殊处理方案…

🔖 Karpathy RSS 精选（92 博客最新）
1. How I Reversed Amazon's Kindle Web Obfuscation  `blog.pixelmelt.dev`
   > As it turns out they don't actually want you to do this…

⭐ GitHub Trending
1. microsoft/markitdown  ⭐89,046
   > Python tool for converting files and office documents to Markdown.

🔥 Hacker News 热门
1. Ghostty – Terminal Emulator  ↑621 💬279  `ghostty.org`

💬 V2EX 热帖
1. [程序员] Netcatty - 开源免费的 SSH 终端软件  💬51  by @BigcatChen
```

## Sources

| # | Source | Description |
|---|--------|-------------|
| 📰 | **Readhub 早报** | Chinese tech/business news with full summaries via official API |
| 🔖 | **Karpathy RSS** | Latest posts from [92 HN popular blogs](https://gist.github.com/emschwartz/e6d2bf860ccc367fe37ff953ba6de66b), curated by Andrej Karpathy |
| ⭐ | **GitHub Trending** | Today's trending repos with descriptions & star counts |
| 🔥 | **Hacker News** | Top stories ranked by score, via Firebase API |
| 💬 | **V2EX** | Hot topics with reply count & author |

## Installation

### Via clawhub

```bash
clawhub install daily-briefing
```

### Manual

Download `daily-briefing.skill` from [Releases](https://github.com/halanhuang2025-lgtm/daily-briefing-skill/releases) and install via OpenClaw.

## Usage

### Run once (on-demand)

```bash
python3 scripts/daily-briefing.py 2>/dev/null
```

### Set up daily cron (08:00 CST)

```bash
openclaw cron add \
  --name "每日资讯早报" \
  --cron "0 8 * * *" \
  --session isolated \
  --announce \
  --channel telegram \
  --thinking low \
  --message "运行 python3 /path/to/scripts/daily-briefing.py 2>/dev/null 并将完整输出分段发送到 Telegram 主群"
```

## Requirements

- Python 3.8+
- **Zero external dependencies** — pure stdlib only
- OpenClaw (for cron + Telegram delivery)

## Performance

- Total runtime: ~25 seconds
- Concurrent fetching: 25 workers for RSS, 10 for HN, 8 for GitHub API
- Karpathy RSS: fetches all 92 feeds in parallel, returns top 10 most recent posts

## Customization

Edit the `n=` parameters in `main()` to control items per section:

```python
readhub = get_readhub(8)         # Readhub items
rss     = get_karpathy_rss(10)   # RSS posts
gh      = get_github_trending(8) # GitHub repos
hn      = get_hn_top(8)          # HN stories
v2      = get_v2ex_hot(8)        # V2EX topics
```

## Credits

- Readhub API by [NoCode 无码科技](https://readhub.cn)
- Karpathy RSS list curated by [Andrej Karpathy](https://x.com/karpathy/status/2018043254986703167), OPML by [Evan Schwartz](https://gist.github.com/emschwartz/e6d2bf860ccc367fe37ff953ba6de66b)
- Inspired by [@discountifu](https://x.com/discountifu/status/2028023940636094475) on X

## License

MIT

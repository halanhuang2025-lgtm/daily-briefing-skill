#!/usr/bin/env python3
"""
每日资讯推送脚本（含摘要版）
包含: Readhub早报 / Karpathy推荐RSS(全92个) / GitHub Trending / HN热门 / V2EX热帖
"""

import json
import sys
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

CST = timezone(timedelta(hours=8))
TODAY = datetime.now(CST).strftime("%Y-%m-%d")
KARPATHY_OPML = "https://gist.githubusercontent.com/emschwartz/e6d2bf860ccc367fe37ff953ba6de66b/raw/hn-popular-blogs-2025.opml"


def fetch(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def clean(text, maxlen=120):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)          # strip HTML
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\[.*?\]', '', text).strip()  # strip markdown links
    return (text[:maxlen] + "…") if len(text) > maxlen else text


# ─── 1. Readhub 早报 ──────────────────────────────────────────────
def get_readhub(n=8):
    raw = fetch("https://api.readhub.cn/daily", {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://readhub.cn"
    })
    if not raw:
        return []
    try:
        d = json.loads(raw)
        items = d.get("data", {}).get("items", [])
        results = []
        for it in items[:n]:
            results.append({
                "title": it.get("title", ""),
                "summary": clean(it.get("summary", ""), 150),
                "url": f"https://readhub.cn/topic/{it.get('uid', '')}",
            })
        return results
    except Exception:
        return []


# ─── 2. Karpathy RSS List (全部 92 个 HN Popular Blogs) ──────────
def load_opml_feeds():
    raw = fetch(KARPATHY_OPML, timeout=12)
    if not raw:
        return []
    try:
        root = ET.fromstring(raw)
        return [o.get("xmlUrl") for o in root.findall('.//outline[@xmlUrl]') if o.get("xmlUrl")]
    except Exception:
        return []

def parse_feed_entries(raw, feed_url):
    ns = {"atom": "http://www.w3.org/2005/Atom",
          "content": "http://purl.org/rss/1.0/modules/content/"}
    try:
        root = ET.fromstring(raw)
    except Exception:
        return []
    entries = (root.findall(".//atom:entry", ns)
               or root.findall(".//entry")
               or root.findall(".//item"))
    blog = re.sub(r'^www\.', '', feed_url.split("/")[2]) if len(feed_url.split("/")) > 2 else feed_url
    results = []
    for entry in entries[:1]:
        def first(*tags, _e=entry, _ns=ns):
            for tag in tags:
                el = _e.find(tag, _ns) if (":" in tag and not tag.startswith("{")) else _e.find(tag)
                if el is not None:
                    return el
            return None

        title_el = first("title", "atom:title")
        link_el  = first("link",  "atom:link")
        pub_el   = first("published", "atom:published", "updated", "atom:updated", "pubDate")
        # 摘要：优先 summary，其次 description，再次 content
        desc_el  = first("summary", "atom:summary", "description", "atom:content", "content:encoded")

        title = (title_el.text or "").strip() if title_el is not None else ""
        link  = ((link_el.get("href") or link_el.text or "").strip()) if link_el is not None else ""
        pub   = (pub_el.text or "").strip() if pub_el is not None else ""
        desc  = ""
        if desc_el is not None:
            desc = clean(desc_el.text or desc_el.get("src", ""), 130)

        if title and link:
            results.append({"title": title, "url": link, "pub": pub, "blog": blog, "desc": desc})
    return results

def fetch_one_feed(url):
    raw = fetch(url, timeout=8)
    if not raw:
        return []
    return parse_feed_entries(raw, url)

def get_karpathy_rss(total=10):
    feeds = load_opml_feeds()
    if not feeds:
        return []
    all_entries = []
    with ThreadPoolExecutor(max_workers=25) as ex:
        futs = {ex.submit(fetch_one_feed, url): url for url in feeds}
        for fut in as_completed(futs, timeout=20):
            try:
                all_entries.extend(fut.result())
            except Exception:
                pass
    all_entries.sort(key=lambda x: x["pub"], reverse=True)
    seen, results = set(), []
    for item in all_entries:
        if item["title"] not in seen:
            seen.add(item["title"])
            results.append(item)
        if len(results) >= total:
            break
    return results


# ─── 3. GitHub Trending ───────────────────────────────────────────
def get_github_trending(n=8):
    raw = fetch("https://github.com/trending")
    if not raw:
        return []
    repos = re.findall(r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', raw)
    descs_raw = re.findall(r'<p class="col-9 color-fg-muted my-1 pr-4">\s*(.*?)\s*</p>', raw, re.DOTALL)
    stars_raw = re.findall(r'<span[^>]*>\s*([\d,]+)\s*</span>\s*\n.*?star', raw, re.DOTALL)
    skip = {"trending", "explore", "login", "topics", "collections", "events",
            "sponsors", "features", "pricing", "about", "contact"}
    seen = []
    for r in repos:
        parts = r.split("/")
        if len(parts) == 2 and parts[0] not in skip and r not in seen:
            seen.append(r)
        if len(seen) >= n:
            break

    # 用 GitHub API 补充 description（并发）
    def fetch_repo_info(repo):
        api_raw = fetch(f"https://api.github.com/repos/{repo}",
                        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github.v3+json"},
                        timeout=6)
        if not api_raw:
            return repo, "", ""
        try:
            d = json.loads(api_raw)
            return repo, d.get("description") or "", f"⭐{d.get('stargazers_count', 0):,}"
        except Exception:
            return repo, "", ""

    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_repo_info, r): r for r in seen[:n]}
        info_map = {}
        for fut in as_completed(futs, timeout=12):
            try:
                repo, desc, stars = fut.result()
                info_map[repo] = (desc, stars)
            except Exception:
                pass

    for r in seen[:n]:
        desc, stars = info_map.get(r, ("", ""))
        if not desc and descs_raw:
            desc = re.sub(r'\s+', ' ', descs_raw.pop(0)).strip()
        results.append({"repo": r, "desc": clean(desc, 100), "stars": stars, "url": f"https://github.com/{r}"})
    return results


# ─── 4. Hacker News 热门 ─────────────────────────────────────────
def get_hn_top(n=8):
    raw = fetch("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not raw:
        return []
    ids = json.loads(raw)[:n * 2]

    def fetch_item(id_):
        r = fetch(f"https://hacker-news.firebaseio.com/v0/item/{id_}.json", timeout=6)
        return json.loads(r) if r else None

    results = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        for fut in as_completed([ex.submit(fetch_item, i) for i in ids], timeout=15):
            try:
                item = fut.result()
                if item and item.get("type") == "story" and item.get("title"):
                    results.append({
                        "title": item["title"],
                        "score": item.get("score", 0),
                        "comments": item.get("descendants", 0),
                        "url": item.get("url") or f"https://news.ycombinator.com/item?id={item['id']}",
                        "domain": re.sub(r'^www\.', '', item.get("url", "").split("/")[2]) if item.get("url") and len(item["url"].split("/")) > 2 else "news.ycombinator.com",
                    })
            except Exception:
                pass
    return sorted(results, key=lambda x: -x["score"])[:n]


# ─── 5. V2EX 热帖 ─────────────────────────────────────────────────
def get_v2ex_hot(n=8):
    raw = fetch("https://www.v2ex.com/api/topics/hot.json")
    if not raw:
        return []
    try:
        items = json.loads(raw)
        return [{
            "title": it.get("title", ""),
            "replies": it.get("replies", 0),
            "url": f"https://www.v2ex.com/t/{it.get('id', '')}",
            "node": it.get("node", {}).get("title", ""),
            "member": it.get("member", {}).get("username", ""),
        } for it in items[:n]]
    except Exception:
        return []


# ─── 主函数 ───────────────────────────────────────────────────────
def main():
    now_str = datetime.now(CST).strftime("%H:%M CST")
    print(f"📅 **{TODAY} 每日资讯**\n")

    # 1. Readhub
    print("⏳ Readhub...", file=sys.stderr)
    readhub = get_readhub(8)
    print("📰 **Readhub 早报**")
    for i, it in enumerate(readhub or [{"title": "获取失败", "summary": "", "url": ""}], 1):
        print(f"\n**{i}. [{it['title']}]({it['url']})**")
        if it.get('summary'):
            print(f"> {it['summary']}")
    print()

    # 2. Karpathy RSS
    print("⏳ Karpathy RSS (92 feeds)...", file=sys.stderr)
    rss = get_karpathy_rss(10)
    print("🔖 **Karpathy RSS 精选**（92 博客最新）")
    for i, it in enumerate(rss or [{"title": "获取失败", "url": "", "blog": "", "desc": ""}], 1):
        print(f"\n**{i}. [{it['title']}]({it['url']})** `{it['blog']}`")
        if it.get('desc'):
            print(f"> {it['desc']}")
    print()

    # 3. GitHub Trending
    print("⏳ GitHub Trending...", file=sys.stderr)
    gh = get_github_trending(8)
    print("⭐ **GitHub Trending**")
    for i, it in enumerate(gh or [{"repo": "获取失败", "url": "", "desc": "", "stars": ""}], 1):
        stars = f" {it['stars']}" if it.get('stars') else ""
        print(f"\n**{i}. [{it['repo']}]({it['url']})**{stars}")
        if it.get('desc'):
            print(f"> {it['desc']}")
    print()

    # 4. HN
    print("⏳ Hacker News...", file=sys.stderr)
    hn = get_hn_top(8)
    print("🔥 **Hacker News 热门**")
    for i, it in enumerate(hn or [{"title": "获取失败", "url": "", "score": 0, "comments": 0, "domain": ""}], 1):
        print(f"\n**{i}. [{it['title']}]({it['url']})**")
        print(f"> ↑{it['score']} 💬{it['comments']}  `{it['domain']}`")
    print()

    # 5. V2EX
    print("⏳ V2EX...", file=sys.stderr)
    v2 = get_v2ex_hot(8)
    print("💬 **V2EX 热帖**")
    for i, it in enumerate(v2 or [{"title": "获取失败", "url": "", "replies": 0, "node": "", "member": ""}], 1):
        node = f"[{it['node']}] " if it['node'] else ""
        print(f"\n**{i}. {node}[{it['title']}]({it['url']})**")
        print(f"> 💬{it['replies']} 回复  by @{it['member']}")

    print(f"\n_更新于 {now_str}_")


if __name__ == "__main__":
    main()

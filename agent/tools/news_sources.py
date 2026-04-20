"""Extra news sources beyond yfinance.

Layered free sources. Each one fails soft — if a provider is down or
rate-limited, it contributes zero items and the others still work.

    stocktwits_messages   StockTwits public stream for $TICKER (sentiment)
    reddit_posts          r/wallstreetbets + r/investing + r/stocks (RSS)
    yahoo_rss             Yahoo Finance ticker RSS
    newsapi_headlines     NewsAPI.org (free tier 100/day, needs NEWSAPI_KEY)

The aggregated tool `get_deep_news(ticker)` fans out to all of them and
returns a single deduped, time-sorted list.
"""
from __future__ import annotations

import os
import time
from datetime import datetime

import feedparser
import httpx


def _ts(s: str | None) -> int | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return int(datetime.strptime(s, fmt).timestamp())
        except Exception:
            continue
    return None


def stocktwits_messages(ticker: str, limit: int = 10) -> list[dict]:
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker.upper()}.json"
    try:
        r = httpx.get(url, timeout=10, headers={"User-Agent": "stockagent/1.0"})
        if r.status_code != 200:
            return []
        msgs = r.json().get("messages") or []
    except Exception:
        return []
    out: list[dict] = []
    for m in msgs[:limit]:
        sent = ((m.get("entities") or {}).get("sentiment") or {}).get("basic")
        out.append({
            "source": "stocktwits",
            "title": (m.get("body") or "").strip()[:240],
            "ts": _ts(m.get("created_at")),
            "url": f"https://stocktwits.com/message/{m.get('id')}",
            "sentiment": sent,
        })
    return out


def reddit_posts(ticker: str, limit: int = 10) -> list[dict]:
    subs = ("wallstreetbets", "investing", "stocks")
    out: list[dict] = []
    for sub in subs:
        url = f"https://www.reddit.com/r/{sub}/search.rss?q={ticker}&restrict_sr=1&sort=new"
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for e in feed.entries[: max(1, limit // len(subs))]:
            out.append({
                "source": f"reddit/{sub}",
                "title": getattr(e, "title", "")[:240],
                "ts": int(time.mktime(e.published_parsed)) if getattr(e, "published_parsed", None) else None,
                "url": getattr(e, "link", None),
            })
    return out


def yahoo_rss(ticker: str, limit: int = 10) -> list[dict]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker.upper()}&region=US&lang=en-US"
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    out: list[dict] = []
    for e in feed.entries[:limit]:
        out.append({
            "source": "yahoo_rss",
            "title": getattr(e, "title", "")[:240],
            "ts": int(time.mktime(e.published_parsed)) if getattr(e, "published_parsed", None) else None,
            "url": getattr(e, "link", None),
        })
    return out


def newsapi_headlines(ticker: str, limit: int = 10) -> list[dict]:
    key = os.environ.get("NEWSAPI_KEY")
    if not key:
        return []
    try:
        r = httpx.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": ticker,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": limit,
            },
            headers={"X-Api-Key": key},
            timeout=15,
        )
        r.raise_for_status()
        arts = r.json().get("articles") or []
    except Exception:
        return []
    out: list[dict] = []
    for a in arts:
        out.append({
            "source": f"newsapi/{(a.get('source') or {}).get('name')}",
            "title": (a.get("title") or "")[:240],
            "ts": _ts(a.get("publishedAt")),
            "url": a.get("url"),
        })
    return out


def get_deep_news(ticker: str, limit: int = 20) -> list[dict]:
    items: list[dict] = []
    items.extend(yahoo_rss(ticker, limit=10))
    items.extend(stocktwits_messages(ticker, limit=8))
    items.extend(reddit_posts(ticker, limit=9))
    items.extend(newsapi_headlines(ticker, limit=10))
    seen: set[str] = set()
    unique: list[dict] = []
    for it in items:
        key = (it.get("title") or "") + (it.get("url") or "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)
    unique.sort(key=lambda x: x.get("ts") or 0, reverse=True)
    return unique[:limit]

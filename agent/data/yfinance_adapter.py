"""yfinance-backed adapter (default).

Notes:
  * yfinance scrapes Yahoo; it breaks periodically (Yahoo throttling or HTML
    changes). We wrap every outbound call in tenacity with a modest backoff
    so a single 429 doesn't sink a whole run.
  * The nightly OHLCV cache (see `ohlcv_cache.py`) means the 15:50 screening
    job reads from SQLite rather than calling this adapter hundreds of
    times at once.
  * `fundamentals` pulls from `.info` which is the slowest / most fragile
    surface. Use sparingly.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

import yfinance as yf
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from agent.data.base import (
    Fundamentals,
    NewsItem,
    OhlcvBar,
    Quote,
    StockDataAdapter,
)

log = logging.getLogger(__name__)

_RETRY = dict(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)


def _f(v) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


class YFinanceAdapter(StockDataAdapter):
    name = "yfinance"

    def quote(self, symbol: str) -> Quote:
        try:
            return self._quote_inner(symbol)
        except Exception as e:
            log.info("yfinance quote failed for %s: %s", symbol, e)
            return Quote(
                symbol=symbol.upper(),
                price=0.0,
                prev_close=None,
                change_pct=None,
                day_low=None,
                day_high=None,
                volume=None,
                currency=None,
            )

    @retry(**_RETRY)
    def _quote_inner(self, symbol: str) -> Quote:
        t = yf.Ticker(symbol)
        fi = getattr(t, "fast_info", {}) or {}
        price = _f(fi.get("last_price") or fi.get("lastPrice"))
        prev = _f(fi.get("previous_close") or fi.get("previousClose"))
        change_pct = None
        if price is not None and prev:
            change_pct = (price - prev) / prev * 100.0
        return Quote(
            symbol=symbol.upper(),
            price=price or 0.0,
            prev_close=prev,
            change_pct=change_pct,
            day_low=_f(fi.get("day_low") or fi.get("dayLow")),
            day_high=_f(fi.get("day_high") or fi.get("dayHigh")),
            volume=_f(fi.get("last_volume") or fi.get("lastVolume")),
            currency=fi.get("currency"),
        )

    def fundamentals(self, symbol: str) -> Fundamentals:
        try:
            return self._fundamentals_inner(symbol)
        except Exception as e:
            log.info("yfinance fundamentals failed for %s: %s", symbol, e)
            return Fundamentals(
                symbol=symbol.upper(),
                market_cap=None, pe_ratio=None, eps=None,
                dividend_yield=None, sector=None, industry=None,
                next_earnings=None, beta=None,
            )

    @retry(**_RETRY)
    def _fundamentals_inner(self, symbol: str) -> Fundamentals:
        t = yf.Ticker(symbol)
        info = {}
        try:
            info = t.get_info() or {}
        except Exception:
            info = getattr(t, "info", {}) or {}
        next_earn = None
        try:
            cal = t.calendar
            if hasattr(cal, "get"):
                d = cal.get("Earnings Date")
                if isinstance(d, list) and d:
                    d0 = d[0]
                    if isinstance(d0, datetime):
                        next_earn = d0.date()
                    elif isinstance(d0, date):
                        next_earn = d0
        except Exception:
            pass
        return Fundamentals(
            symbol=symbol.upper(),
            market_cap=_f(info.get("marketCap")),
            pe_ratio=_f(info.get("trailingPE") or info.get("forwardPE")),
            eps=_f(info.get("trailingEps")),
            dividend_yield=_f(info.get("dividendYield")),
            sector=info.get("sector"),
            industry=info.get("industry"),
            next_earnings=next_earn,
            beta=_f(info.get("beta") or info.get("beta3Year")),
        )

    def news(self, symbol: str, limit: int = 5) -> list[NewsItem]:
        try:
            return self._news_inner(symbol, limit)
        except Exception as e:
            log.info("yfinance news failed for %s: %s", symbol, e)
            return []

    @retry(**_RETRY)
    def _news_inner(self, symbol: str, limit: int = 5) -> list[NewsItem]:
        t = yf.Ticker(symbol)
        items = []
        try:
            items = t.news or []
        except Exception:
            items = []
        out: list[NewsItem] = []
        for n in items[:limit]:
            # yfinance news schema changed in 2024/2025; support both shapes.
            content = n.get("content") if isinstance(n, dict) else None
            if content:
                title = content.get("title")
                publisher = (content.get("provider") or {}).get("displayName")
                url = (content.get("canonicalUrl") or {}).get("url")
                ts_raw = content.get("pubDate")
                ts = None
                if ts_raw:
                    try:
                        ts = int(datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).timestamp())
                    except Exception:
                        ts = None
            else:
                title = n.get("title")
                publisher = n.get("publisher")
                url = n.get("link")
                ts = int(n.get("providerPublishTime") or 0) or None
            if title:
                out.append(NewsItem(title=title, publisher=publisher, url=url, ts=ts))
        return out

    def ohlcv(self, symbol: str, days: int = 260) -> list[OhlcvBar]:
        try:
            return self._ohlcv_inner(symbol, days)
        except Exception as e:
            log.info("yfinance ohlcv failed for %s: %s", symbol, e)
            return []

    @retry(**_RETRY)
    def _ohlcv_inner(self, symbol: str, days: int = 260) -> list[OhlcvBar]:
        # `period` strings keep us away from date arithmetic & Yahoo's
        # varying calendar handling.
        period = "1y" if days <= 260 else "2y"
        df = yf.download(
            symbol,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if df is None or df.empty:
            return []
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)
        out: list[OhlcvBar] = []
        for idx, row in df.iterrows():
            d = idx.date().isoformat() if hasattr(idx, "date") else str(idx)[:10]
            out.append(
                OhlcvBar(
                    date=d,
                    open=_f(row.get("Open")) or 0.0,
                    high=_f(row.get("High")) or 0.0,
                    low=_f(row.get("Low")) or 0.0,
                    close=_f(row.get("Close")) or 0.0,
                    adj_close=_f(row.get("Adj Close")) or _f(row.get("Close")) or 0.0,
                    volume=_f(row.get("Volume")) or 0.0,
                )
            )
        return out[-days:]

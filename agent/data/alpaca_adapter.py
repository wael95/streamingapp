"""Alpaca Markets data adapter.

Free tier gives IEX realtime quotes and full historical bars for US
equities. Sign up at https://alpaca.markets/, get API key + secret,
put into `.env`:

    ALPACA_API_KEY=...
    ALPACA_API_SECRET=...
    ALPACA_DATA_URL=https://data.alpaca.markets     # default
    DATA_ADAPTER=alpaca

Note: Alpaca doesn't ship fundamentals or earnings calendars. We fall
back to yfinance for `fundamentals()` and `news()`; only `quote()` and
`ohlcv()` come from Alpaca. This keeps the realtime advantage for quotes
without losing fundamentals coverage.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from agent.data.base import (
    Fundamentals,
    NewsItem,
    OhlcvBar,
    Quote,
    StockDataAdapter,
)
from agent.data.yfinance_adapter import YFinanceAdapter


_DEFAULT_URL = "https://data.alpaca.markets"
_RETRY = dict(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)


def _headers() -> dict:
    key = os.environ.get("ALPACA_API_KEY", "")
    secret = os.environ.get("ALPACA_API_SECRET", "")
    if not key or not secret:
        raise RuntimeError("ALPACA_API_KEY / ALPACA_API_SECRET missing in .env")
    return {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
    }


class AlpacaAdapter(StockDataAdapter):
    name = "alpaca"

    def __init__(self) -> None:
        self._base = os.environ.get("ALPACA_DATA_URL", _DEFAULT_URL).rstrip("/")
        self._yf = YFinanceAdapter()  # used only for fundamentals + news

    @retry(**_RETRY)
    def quote(self, symbol: str) -> Quote:
        r = httpx.get(
            f"{self._base}/v2/stocks/{symbol.upper()}/quotes/latest",
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
        q = (r.json() or {}).get("quote") or {}
        bid = q.get("bp")
        ask = q.get("ap")
        mid = (bid + ask) / 2 if bid and ask else (bid or ask)

        # Pull previous close from the daily bar for change_pct.
        prev_close = None
        try:
            pr = httpx.get(
                f"{self._base}/v2/stocks/{symbol.upper()}/bars",
                params={"timeframe": "1Day", "limit": 2},
                headers=_headers(),
                timeout=10,
            )
            pr.raise_for_status()
            bars = (pr.json() or {}).get("bars") or []
            if len(bars) >= 2:
                prev_close = float(bars[-2].get("c"))
            elif bars:
                prev_close = float(bars[-1].get("c"))
        except Exception:
            pass

        change_pct = None
        if mid and prev_close:
            change_pct = (mid - prev_close) / prev_close * 100.0

        return Quote(
            symbol=symbol.upper(),
            price=float(mid or 0.0),
            prev_close=prev_close,
            change_pct=change_pct,
            day_low=None,
            day_high=None,
            volume=None,
            currency="USD",
        )

    def fundamentals(self, symbol: str) -> Fundamentals:
        return self._yf.fundamentals(symbol)

    def news(self, symbol: str, limit: int = 5) -> list[NewsItem]:
        return self._yf.news(symbol, limit)

    @retry(**_RETRY)
    def ohlcv(self, symbol: str, days: int = 260) -> list[OhlcvBar]:
        end = datetime.utcnow().date()
        start = end - timedelta(days=int(days * 1.6))  # buffer for weekends/holidays
        r = httpx.get(
            f"{self._base}/v2/stocks/{symbol.upper()}/bars",
            params={
                "timeframe": "1Day",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "adjustment": "raw",
                "limit": 10000,
            },
            headers=_headers(),
            timeout=20,
        )
        r.raise_for_status()
        bars = (r.json() or {}).get("bars") or []
        out: list[OhlcvBar] = []
        for b in bars:
            ts = (b.get("t") or "")[:10]
            out.append(
                OhlcvBar(
                    date=ts,
                    open=float(b.get("o", 0) or 0),
                    high=float(b.get("h", 0) or 0),
                    low=float(b.get("l", 0) or 0),
                    close=float(b.get("c", 0) or 0),
                    adj_close=float(b.get("c", 0) or 0),
                    volume=float(b.get("v", 0) or 0),
                )
            )
        return out[-days:]

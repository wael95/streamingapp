"""Finnhub adapter (stub).

Not wired up yet. When you want to use it, set `FINNHUB_API_KEY` in `.env`,
set `DATA_ADAPTER=finnhub`, and implement the four methods below using the
Finnhub REST API. Endpoints you'll want:
  /quote, /stock/profile2, /stock/metric?metric=all, /company-news, /stock/candle
"""
from __future__ import annotations

from agent.data.base import (
    Fundamentals,
    NewsItem,
    OhlcvBar,
    Quote,
    StockDataAdapter,
)


class FinnhubAdapter(StockDataAdapter):
    name = "finnhub"

    def quote(self, symbol: str) -> Quote:
        raise NotImplementedError("finnhub adapter not implemented yet")

    def fundamentals(self, symbol: str) -> Fundamentals:
        raise NotImplementedError

    def news(self, symbol: str, limit: int = 5) -> list[NewsItem]:
        raise NotImplementedError

    def ohlcv(self, symbol: str, days: int = 260) -> list[OhlcvBar]:
        raise NotImplementedError

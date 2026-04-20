"""Alpha Vantage adapter (stub). See finnhub_adapter.py for the pattern."""
from __future__ import annotations

from agent.data.base import (
    Fundamentals,
    NewsItem,
    OhlcvBar,
    Quote,
    StockDataAdapter,
)


class AlphaVantageAdapter(StockDataAdapter):
    name = "alpha_vantage"

    def quote(self, symbol: str) -> Quote:
        raise NotImplementedError("alpha_vantage adapter not implemented yet")

    def fundamentals(self, symbol: str) -> Fundamentals:
        raise NotImplementedError

    def news(self, symbol: str, limit: int = 5) -> list[NewsItem]:
        raise NotImplementedError

    def ohlcv(self, symbol: str, days: int = 260) -> list[OhlcvBar]:
        raise NotImplementedError

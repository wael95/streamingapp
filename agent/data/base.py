"""Stock data adapter interface.

Each concrete adapter implements the same narrow surface. Everything that
needs prices, fundamentals, or news goes through these methods so providers
can be swapped without touching agent code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class Quote:
    symbol: str
    price: float
    prev_close: float | None
    change_pct: float | None
    day_low: float | None
    day_high: float | None
    volume: float | None
    currency: str | None


@dataclass
class Fundamentals:
    symbol: str
    market_cap: float | None
    pe_ratio: float | None
    eps: float | None
    dividend_yield: float | None
    sector: str | None
    industry: str | None
    next_earnings: date | None
    beta: float | None = None


@dataclass
class NewsItem:
    title: str
    publisher: str | None
    url: str | None
    ts: int | None


@dataclass
class OhlcvBar:
    date: str  # ISO yyyy-mm-dd
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: float


class StockDataAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def quote(self, symbol: str) -> Quote: ...

    @abstractmethod
    def fundamentals(self, symbol: str) -> Fundamentals: ...

    @abstractmethod
    def news(self, symbol: str, limit: int = 5) -> list[NewsItem]: ...

    @abstractmethod
    def ohlcv(self, symbol: str, days: int = 260) -> list[OhlcvBar]: ...

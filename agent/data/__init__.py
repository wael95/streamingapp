"""Market data layer.

`get_adapter(name)` returns a concrete `StockDataAdapter`. The rest of the
code never imports a specific provider module; swapping providers is a
matter of editing `.env` (`DATA_ADAPTER=yfinance|finnhub|alpha_vantage`).
"""
from __future__ import annotations

from agent.data.base import StockDataAdapter


def get_adapter(name: str) -> StockDataAdapter:
    name = (name or "yfinance").lower()
    if name == "yfinance":
        from agent.data.yfinance_adapter import YFinanceAdapter
        return YFinanceAdapter()
    if name == "finnhub":
        from agent.data.finnhub_adapter import FinnhubAdapter
        return FinnhubAdapter()
    if name == "alpha_vantage":
        from agent.data.alpha_vantage_adapter import AlphaVantageAdapter
        return AlphaVantageAdapter()
    raise ValueError(f"unknown DATA_ADAPTER: {name}")

from __future__ import annotations

from agent.config import Settings
from agent.data import get_adapter


def get_fundamentals(settings: Settings, ticker: str) -> dict:
    adapter = get_adapter(settings.data_adapter)
    f = adapter.fundamentals(ticker)
    return {
        "symbol": f.symbol,
        "market_cap": f.market_cap,
        "pe_ratio": f.pe_ratio,
        "eps": f.eps,
        "dividend_yield": f.dividend_yield,
        "sector": f.sector,
        "industry": f.industry,
        "next_earnings": f.next_earnings.isoformat() if f.next_earnings else None,
    }

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
        "beta": f.beta,
        "shares_outstanding": f.shares_outstanding,
        "float_shares": f.float_shares,
        "insider_ownership_pct": (round(f.insider_ownership * 100, 2) if f.insider_ownership else None),
        "institutional_ownership_pct": (round(f.institutional_ownership * 100, 2) if f.institutional_ownership else None),
        "last_split_date": f.last_split_date,
        "last_split_ratio": f.last_split_ratio,
    }

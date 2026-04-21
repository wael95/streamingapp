"""Sector performance tool.

Returns whether each US sector is green or red in the current session.
Uses sector ETFs (SPDR Select Sector) as proxies — they track ~$100B+
each and are liquid enough that their daily change faithfully
represents the sector.

    XLK  Technology
    XLF  Financials
    XLV  Healthcare
    XLE  Energy
    XLI  Industrials
    XLY  Consumer Discretionary
    XLP  Consumer Staples
    XLU  Utilities
    XLRE Real Estate
    XLB  Materials
    XLC  Communication Services

get_sector_performance(ticker?) — if `ticker` given, only returns that
ticker's sector status; otherwise returns all sectors.

The mapping from a ticker's GICS sector name (from yfinance fundamentals)
to its ETF lives in `_SECTOR_ETF`.
"""
from __future__ import annotations

from agent.config import Settings
from agent.data import get_adapter


_SECTOR_ETF: dict[str, str] = {
    "Technology": "XLK",
    "Information Technology": "XLK",
    "Financial Services": "XLF",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Health Care": "XLV",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Consumer Cyclical": "XLY",
    "Consumer Discretionary": "XLY",
    "Consumer Defensive": "XLP",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB",
    "Materials": "XLB",
    "Communication Services": "XLC",
}


def _sector_change(settings: Settings, etf: str) -> float | None:
    try:
        q = get_adapter(settings.data_adapter).quote(etf)
        return q.change_pct
    except Exception:
        return None


def get_sector_performance(settings: Settings, ticker: str | None = None) -> dict:
    adapter = get_adapter(settings.data_adapter)
    if ticker:
        f = adapter.fundamentals(ticker)
        sector = f.sector or ""
        etf = _SECTOR_ETF.get(sector)
        if not etf:
            return {
                "ticker": ticker.upper(),
                "sector": sector or "unknown",
                "etf": None,
                "change_pct": None,
                "green": None,
                "note": f"no ETF mapping for sector '{sector}'",
            }
        change = _sector_change(settings, etf)
        return {
            "ticker": ticker.upper(),
            "sector": sector,
            "etf": etf,
            "change_pct": round(change, 2) if change is not None else None,
            "green": bool(change is not None and change > 0),
        }

    out: dict[str, Any] = {}
    for sector, etf in sorted(set((s, e) for s, e in _SECTOR_ETF.items())):
        change = _sector_change(settings, etf)
        out[sector] = {
            "etf": etf,
            "change_pct": round(change, 2) if change is not None else None,
            "green": bool(change is not None and change > 0),
        }
    return out

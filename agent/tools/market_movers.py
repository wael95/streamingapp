"""Market movers (top gainers / pre-market gainers).

Implements the Scan mode's first step: find candidates that are moving
the most today. Works across the ENTIRE US market (not just our static
CSV universe) by calling an external screener.

Providers, tried in order:
    1. Financial Modeling Prep (FMP) — needs FMP_API_KEY (free 250/day)
       endpoints: /gainers, /pre-market-gainers
    2. Finviz via finvizfinance — scraped, no key needed, fragile
       filters: price < 5, change > 20%
    3. yfinance Screener — predefined 'day_gainers' body

Returns a pre-filtered list of tickers matching the strategy's hard
filters (price<$5, up >=20%). Claude then enriches each candidate with
get_quote / get_fundamentals / get_news / get_sector_performance etc.

Keeps the Claude turn count bounded: instead of having the model iterate
over thousands of tickers, the external screener pre-filters to ~5-40
candidates, and Claude only evaluates those.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)


def _fmp_movers(premarket: bool) -> list[dict]:
    key = os.environ.get("FMP_API_KEY")
    if not key:
        return []
    path = "/api/v3/pre-market-gainers" if premarket else "/api/v3/gainers"
    try:
        r = httpx.get(
            f"https://financialmodelingprep.com{path}",
            params={"apikey": key},
            timeout=15,
        )
        r.raise_for_status()
        rows = r.json() or []
    except Exception as e:
        log.info("FMP movers failed: %s", e)
        return []
    out: list[dict] = []
    for row in rows:
        try:
            price = float(row.get("price") or 0)
            change_pct = float(row.get("changesPercentage") or row.get("change_percent") or 0)
            out.append({
                "symbol": (row.get("symbol") or row.get("ticker") or "").upper(),
                "price": price,
                "change_pct": change_pct,
                "name": row.get("name"),
                "volume": row.get("volume"),
                "source": "fmp",
            })
        except Exception:
            continue
    return out


def _finviz_movers() -> list[dict]:
    try:
        from finvizfinance.screener.overview import Overview
    except Exception:
        return []
    try:
        fo = Overview()
        # Price < $5, change > 20%, avg volume > 100k (liquid enough).
        fo.set_filter(
            filters_dict={
                "Price": "Under $5",
                "Change": "Up 20%",
                "Average Volume": "Over 100K",
            }
        )
        df = fo.screener_view()
    except Exception as e:
        log.info("Finviz screener failed: %s", e)
        return []
    if df is None or df.empty:
        return []
    out: list[dict] = []
    for _, row in df.iterrows():
        try:
            out.append({
                "symbol": str(row.get("Ticker")).upper(),
                "price": float(row.get("Price")),
                "change_pct": float(str(row.get("Change")).replace("%", "")),
                "name": row.get("Company"),
                "volume": row.get("Volume"),
                "sector": row.get("Sector"),
                "source": "finviz",
            })
        except Exception:
            continue
    return out


def _yf_screener() -> list[dict]:
    try:
        import yfinance as yf
        s = yf.Screener()
        s.set_predefined_body("day_gainers")
        body = s.response
    except Exception as e:
        log.info("yfinance screener failed: %s", e)
        return []
    rows = []
    if isinstance(body, dict):
        rows = ((body.get("finance") or {}).get("result") or [{}])[0].get("quotes", [])
    out: list[dict] = []
    for q in rows or []:
        try:
            out.append({
                "symbol": str(q.get("symbol") or "").upper(),
                "price": float(q.get("regularMarketPrice") or 0),
                "change_pct": float(q.get("regularMarketChangePercent") or 0),
                "name": q.get("shortName"),
                "volume": q.get("regularMarketVolume"),
                "source": "yfinance",
            })
        except Exception:
            continue
    return out


def get_top_gainers(
    max_price: float | None = 5.0,
    min_change_pct: float | None = 20.0,
    premarket: bool = True,
    limit: int = 40,
) -> list[dict]:
    """Return pre-filtered gainers matching the strategy's hard filters.

    Pre-market is preferred during the 15:30 Riyadh run (US pre-market
    is active). If no provider returns pre-market data, falls back to
    regular-session gainers.
    """
    candidates: list[dict] = []
    if premarket:
        candidates = _fmp_movers(premarket=True)
    if not candidates:
        candidates = _fmp_movers(premarket=False)
    if not candidates:
        candidates = _finviz_movers()
    if not candidates:
        candidates = _yf_screener()

    filtered: list[dict] = []
    for c in candidates:
        if not c.get("symbol"):
            continue
        if max_price is not None and c.get("price", 0) > max_price:
            continue
        if min_change_pct is not None and c.get("change_pct", 0) < min_change_pct:
            continue
        filtered.append(c)

    filtered.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
    return filtered[:limit]

"""YAML-driven stock screener.

`config/rules.yml` defines:
  universe: sp500 | sp500_plus_watchlist | watchlist
  lookback_days: int
  conditions: [{metric, op, value}]
  max_results: int

Supported metrics:
  market_cap, pe_ratio, avg_volume_30d, rsi_14, sma_cross,
  price_vs_sma200, change_pct_5d, change_pct_1d, price

Supported ops:
  ==, !=, >, >=, <, <=, between (value is [lo, hi])

The engine pulls price history from the OHLCV cache (populated nightly by
`ohlcv_cache.refresh_universe`) and fundamentals on demand from the
active adapter. Unknown metrics simply drop the ticker. Sorting is a
simple composite: lower RSI is better, higher 5d momentum is better, tie
break on market cap descending.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from agent.config import Settings
from agent.data import get_adapter
from agent.data.universe import build_universe
from agent.db import store
from agent.screening import indicators as ind

log = logging.getLogger(__name__)


@dataclass
class ScreenedTicker:
    symbol: str
    price: float | None
    change_pct_5d: float | None
    rsi_14: float | None
    market_cap: float | None
    pe_ratio: float | None
    sector: str | None
    reasons: list[str]


def _cmp(op: str, x, y) -> bool:
    if x is None:
        return False
    if op == "between":
        lo, hi = y
        return lo <= x <= hi
    if op == "==":
        return x == y
    if op == "!=":
        return x != y
    if op == ">":
        return x > y
    if op == ">=":
        return x >= y
    if op == "<":
        return x < y
    if op == "<=":
        return x <= y
    return False


def _closes_volumes(symbol: str, days: int) -> tuple[np.ndarray, np.ndarray]:
    rows = store.read_ohlcv(symbol, limit=days)  # DESC
    if not rows:
        return np.array([]), np.array([])
    rows = list(reversed(rows))
    closes = np.array([r[4] for r in rows], dtype=float)  # close
    vols = np.array([r[6] for r in rows], dtype=float)  # volume
    return closes, vols


def _metric_value(metric: str, symbol: str, closes, vols, fundamentals) -> Any:
    if metric == "price":
        return float(closes[-1]) if closes.size else None
    if metric == "change_pct_1d":
        return ind.change_pct(closes, 1)
    if metric == "change_pct_5d":
        return ind.change_pct(closes, 5)
    if metric == "rsi_14":
        return ind.rsi(closes, 14)
    if metric == "avg_volume_30d":
        return ind.avg_volume(vols, 30)
    if metric == "sma_cross":
        return "50_over_200" if ind.golden_cross(closes, 50, 200, 20) else "none"
    if metric == "price_vs_sma200":
        s = ind.sma(closes, 200)
        if s is None or closes.size == 0:
            return None
        return float(closes[-1] / s)
    if metric == "market_cap":
        return fundamentals.market_cap if fundamentals else None
    if metric == "pe_ratio":
        return fundamentals.pe_ratio if fundamentals else None
    return None


def run_screen(settings: Settings, rules_override: dict | None = None) -> list[dict]:
    rules = rules_override or settings.rules or {}
    universe_setting = rules.get("universe", "sp500_plus_watchlist")
    lookback = int(rules.get("lookback_days", 260))
    conditions = rules.get("conditions", []) or []
    max_results = int(rules.get("max_results", 15))

    tickers = build_universe(universe_setting, settings.watchlist_tickers)
    if not tickers:
        log.warning("screener: universe is empty")
        return []

    # Only touch fundamentals when a rule needs them.
    needs_fund = any(
        c.get("metric") in ("market_cap", "pe_ratio") for c in conditions
    )
    adapter = get_adapter(settings.data_adapter) if needs_fund else None

    passed: list[ScreenedTicker] = []
    for sym in tickers:
        closes, vols = _closes_volumes(sym, lookback)
        if closes.size < 30:
            continue
        fundamentals = None
        if needs_fund and adapter is not None:
            try:
                fundamentals = adapter.fundamentals(sym)
            except Exception:
                fundamentals = None

        reasons: list[str] = []
        ok = True
        for c in conditions:
            m, op, val = c.get("metric"), c.get("op"), c.get("value")
            x = _metric_value(m, sym, closes, vols, fundamentals)
            if not _cmp(op, x, val):
                ok = False
                break
            reasons.append(f"{m} {op} {val} (={_fmt(x)})")
        if not ok:
            continue

        passed.append(
            ScreenedTicker(
                symbol=sym,
                price=float(closes[-1]) if closes.size else None,
                change_pct_5d=ind.change_pct(closes, 5),
                rsi_14=ind.rsi(closes, 14),
                market_cap=fundamentals.market_cap if fundamentals else None,
                pe_ratio=fundamentals.pe_ratio if fundamentals else None,
                sector=fundamentals.sector if fundamentals else None,
                reasons=reasons,
            )
        )

    passed.sort(
        key=lambda t: (
            t.rsi_14 if t.rsi_14 is not None else 100,
            -(t.change_pct_5d or 0),
            -(t.market_cap or 0),
        )
    )
    top = passed[:max_results]
    return [t.__dict__ for t in top]


def _fmt(x):
    if x is None:
        return "n/a"
    if isinstance(x, float):
        if abs(x) >= 1e9:
            return f"{x/1e9:.2f}B"
        if abs(x) >= 1e6:
            return f"{x/1e6:.2f}M"
        return f"{x:.2f}"
    return str(x)

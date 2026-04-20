"""Nightly OHLCV pre-fetch.

At 03:00 Riyadh (Mon-Fri) the scheduler calls `refresh_universe()`. It
pulls a year of daily bars for every ticker in the screening universe and
writes them into `ohlcv_cache` in SQLite. The 15:50 screener then reads
only from SQLite, so a full 500-name screen takes seconds and doesn't
touch Yahoo at all.

We sleep a small jittered interval between pulls to stay under yfinance's
rate limits. If a single symbol fails we log and continue rather than
aborting the whole refresh.
"""
from __future__ import annotations

import logging
import random
import time

from agent.data import get_adapter
from agent.data.universe import build_universe
from agent.db import store

log = logging.getLogger(__name__)


def refresh_universe(
    adapter_name: str,
    universe_setting: str,
    watchlist: list[str],
    days: int = 260,
    sleep_min: float = 0.15,
    sleep_max: float = 0.45,
) -> dict:
    adapter = get_adapter(adapter_name)
    tickers = build_universe(universe_setting, watchlist)
    ok, fail = 0, 0
    for sym in tickers:
        try:
            bars = adapter.ohlcv(sym, days=days)
            rows = [
                (sym, b.date, b.open, b.high, b.low, b.close, b.adj_close, b.volume)
                for b in bars
            ]
            if rows:
                store.upsert_ohlcv(rows)
                ok += 1
            else:
                fail += 1
        except Exception as e:
            fail += 1
            log.warning("ohlcv refresh failed for %s: %s", sym, e)
        time.sleep(random.uniform(sleep_min, sleep_max))
    summary = {"ok": ok, "fail": fail, "universe": len(tickers)}
    log.info("ohlcv refresh done: %s", summary)
    store.log_report("ohlcv_refresh", None, summary)
    return summary

"""Screening universe loader.

V1 universe: S&P 500 (shipped as a static CSV) union the user's watchlist.
We don't scrape Wikipedia at runtime; the static file is good enough for a
daily 3:50 PM screener and is easy to refresh manually.

To refresh the CSV, edit `agent/data/sp500.csv` (one ticker per line). If
Yahoo's symbol differs (e.g. `BRK-B` vs `BRK.B`), match Yahoo's convention.
"""
from __future__ import annotations

from pathlib import Path


_SP500_CSV = Path(__file__).parent / "sp500.csv"


def sp500_tickers() -> list[str]:
    if not _SP500_CSV.exists():
        return []
    lines = _SP500_CSV.read_text(encoding="utf-8").splitlines()
    return [ln.strip().upper() for ln in lines if ln.strip() and not ln.startswith("#")]


def build_universe(setting: str, watchlist: list[str]) -> list[str]:
    setting = (setting or "sp500_plus_watchlist").lower()
    wl = [t.upper() for t in watchlist]
    if setting == "watchlist":
        return sorted(set(wl))
    if setting == "sp500":
        return sorted(set(sp500_tickers()))
    # default: sp500 ∪ watchlist
    return sorted(set(sp500_tickers()) | set(wl))

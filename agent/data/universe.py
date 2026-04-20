"""Screening universe loader.

Universes are plain CSV files under `agent/data/`, one ticker per line.
Comments (`#`) and blank lines are ignored. Drop in new CSVs any time —
they are auto-discovered by the `auto` option.

Shipped:
  - sp500.csv         starter S&P 500 subset (expand freely)
  - nasdaq100.csv     full Nasdaq 100

Add your own (e.g. `russell1000.csv`) by creating the file and setting
`universe: russell1000` in rules.yml.

`rules.yml` `universe:` values:
  watchlist             only the user's watchlist.yml tickers
  sp500                 sp500.csv
  nasdaq100             nasdaq100.csv
  sp500_plus_watchlist  default; sp500.csv ∪ watchlist
  russell1000           russell1000.csv (create this file yourself)
  all                   union of every *.csv in agent/data/ ∪ watchlist
  <any filename stem>   e.g. "tadawul" will load tadawul.csv
"""
from __future__ import annotations

from pathlib import Path


_DATA_DIR = Path(__file__).parent


def _read_csv(path: Path) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        out.append(t.upper())
    return out


def load_csv(stem: str) -> list[str]:
    return _read_csv(_DATA_DIR / f"{stem}.csv")


def sp500_tickers() -> list[str]:
    return load_csv("sp500")


def all_csvs() -> list[str]:
    seen: set[str] = set()
    for csv in sorted(_DATA_DIR.glob("*.csv")):
        for t in _read_csv(csv):
            seen.add(t)
    return sorted(seen)


def build_universe(setting: str, watchlist: list[str]) -> list[str]:
    setting = (setting or "sp500_plus_watchlist").lower()
    wl = [t.upper() for t in watchlist]
    if setting == "watchlist":
        return sorted(set(wl))
    if setting == "all":
        return sorted(set(all_csvs()) | set(wl))
    if setting == "sp500_plus_watchlist":
        return sorted(set(load_csv("sp500")) | set(wl))
    # Any other value: look up a CSV by that name.
    tickers = load_csv(setting)
    if not tickers:
        return sorted(set(wl))
    return sorted(set(tickers) | set(wl))

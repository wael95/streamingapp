from __future__ import annotations

from agent.config import Settings
from agent.data import get_adapter


def get_quote(settings: Settings, ticker: str) -> dict:
    adapter = get_adapter(settings.data_adapter)
    q = adapter.quote(ticker)
    return {
        "symbol": q.symbol,
        "price": q.price,
        "prev_close": q.prev_close,
        "change_pct": round(q.change_pct, 2) if q.change_pct is not None else None,
        "day_low": q.day_low,
        "day_high": q.day_high,
        "volume": q.volume,
        "currency": q.currency,
    }

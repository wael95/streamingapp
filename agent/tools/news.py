from __future__ import annotations

from agent.config import Settings
from agent.data import get_adapter


def get_news(settings: Settings, ticker: str, limit: int = 5) -> list[dict]:
    adapter = get_adapter(settings.data_adapter)
    items = adapter.news(ticker, limit)
    return [
        {
            "title": n.title,
            "publisher": n.publisher,
            "url": n.url,
            "ts": n.ts,
        }
        for n in items
    ]

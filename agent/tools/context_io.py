from __future__ import annotations

from agent.config import Settings
from agent.db import store


def read_context(settings: Settings) -> str:
    p = settings.context_md_path
    if not p.exists():
        return "(no context.md file; user has not defined a strategy yet)"
    return p.read_text(encoding="utf-8")


def log_report(kind: str | None, ticker: str | None, payload: dict) -> None:
    store.log_report(kind or "chat", ticker, payload)

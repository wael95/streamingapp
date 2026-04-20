from __future__ import annotations

from agent.config import Settings
from agent.screening.engine import run_screen


def screen_stocks(settings: Settings, rules_override: dict | None = None) -> list[dict]:
    return run_screen(settings, rules_override)

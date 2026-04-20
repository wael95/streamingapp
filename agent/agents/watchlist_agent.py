"""Agent A — daily watchlist digest at 15:50 Riyadh.

For every ticker in the user's watchlist, fetch quote + recent news + any
earnings within the next 7 days, and send a single compact WhatsApp
message (one line per ticker). Uses Sonnet for cost/speed.
"""
from __future__ import annotations

import logging

from agent.claude_client import run_agent
from agent.config import Settings
from agent.bridge_client import BridgeClient

log = logging.getLogger(__name__)

INSTRUCTIONS = """You are running the DAILY WATCHLIST UPDATE.

Steps:
  1. For each ticker in the cached Default watchlist, call get_quote and
     briefly scan get_news (1-2 headlines, only if relevant).
  2. For each, produce ONE line in this format:
       <TICKER>: $<price> (<signed change_pct>%) — <one clause: news or n/a>
  3. After all tickers, add a one-line summary: "Market vibe: <bullish/mixed/bearish> based on <reason>."
  4. Call send_whatsapp once with the final formatted message.
  5. Call log_report(kind='watchlist', payload={ ... }) with the tickers and prices."""


def run(settings: Settings, bridge: BridgeClient) -> str:
    tickers = settings.watchlist_tickers
    if not tickers:
        log.warning("watchlist agent: watchlist.yml is empty; skipping")
        return ""
    user_msg = f"Run the daily watchlist update now for: {', '.join(tickers)}."
    return run_agent(
        settings,
        bridge,
        model=settings.sonnet_model,
        role_instructions=INSTRUCTIONS,
        user_message=user_msg,
    )

"""Agent A — daily watchlist digest at 15:50 Riyadh.

For every ticker in the user's watchlist (or a caller-supplied list),
fetch quote + news + any earnings within the next 7 days, and send a
single compact WhatsApp message (one line per ticker). Uses Sonnet for
cost/speed.

Output language: Arabic. All internal reasoning stays in English; only
the outbound WhatsApp message is translated.
"""
from __future__ import annotations

import logging

from agent.claude_client import run_agent
from agent.config import Settings
from agent.bridge_client import BridgeClient

log = logging.getLogger(__name__)

INSTRUCTIONS = """You are running the DAILY WATCHLIST UPDATE.

Steps:
  1. For each ticker the user asks about, call get_quote and briefly
     scan get_news (1-2 headlines, only if relevant).
  2. For each, produce ONE line in this structure (translate to Arabic):
       <TICKER>: $<price> (<signed change_pct>%) — <short clause: news or n/a>
  3. After all tickers, add a one-line market-vibe summary.
  4. Call send_whatsapp ONCE with the final formatted message.
  5. Call log_report(kind='watchlist', payload={...}) with the data.

CRITICAL — OUTPUT LANGUAGE:
  The text passed to send_whatsapp MUST be in Arabic (العربية). Ticker
  symbols (AAPL, NVDA...) and numbers stay as-is. Use natural Modern
  Standard Arabic for everything else. Keep it mobile-friendly."""


def run(
    settings: Settings,
    bridge: BridgeClient,
    tickers: list[str] | None = None,
    broadcast: bool = True,
) -> str:
    tickers = tickers or settings.watchlist_tickers
    if not tickers:
        log.warning("watchlist agent: no tickers supplied; skipping")
        return ""
    user_msg = f"Run the daily watchlist update now for: {', '.join(tickers)}."
    return run_agent(
        settings,
        bridge,
        model=settings.sonnet_model,
        role_instructions=INSTRUCTIONS,
        user_message=user_msg,
        broadcast=broadcast,
    )

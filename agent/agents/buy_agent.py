"""Agent B — "what to buy today" at 15:50 Riyadh.

Flow:
  1. Run the rule-based screener (screen_stocks) using config/rules.yml.
  2. Claude ranks the shortlist using the cached context.md preferences.
  3. Claude picks top 5 with a 2-sentence rationale each.
  4. Claude sends the message via send_whatsapp.

Uses Opus because the ranking step benefits from stronger reasoning and
the shortlist is small (≤15 tickers), so cost stays bounded.
"""
from __future__ import annotations

import logging

from agent.claude_client import run_agent
from agent.config import Settings
from agent.bridge_client import BridgeClient

log = logging.getLogger(__name__)

INSTRUCTIONS = """You are running the DAILY BUY IDEAS job.

Steps:
  1. Call screen_stocks() to get today's shortlist.
  2. If the list is empty, send_whatsapp("No stocks passed today's screen.")
     and stop.
  3. Otherwise pick the TOP 5 using the user's cached context (holdings,
     risk tolerance, sector views). You may also call get_quote /
     get_fundamentals / get_news on candidates before ranking.
  4. Produce a WhatsApp message in this exact format:

     Buy ideas — <date>
     1. <TICKER> @ $<price> — <2-sentence rationale grounded in user context>
     2. ...
     (up to 5)
     Disclaimer: not financial advice.

  5. Call send_whatsapp with the message, then log_report(kind='buy', payload={picks:[...]})."""


def run(settings: Settings, bridge: BridgeClient) -> str:
    return run_agent(
        settings,
        bridge,
        model=settings.opus_model,
        role_instructions=INSTRUCTIONS,
        user_message="Generate today's buy ideas now.",
    )

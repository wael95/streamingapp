"""Agent B — small-cap momentum SCAN (simplified).

Runs every 2 hours on weekdays at :50 past (10:50..22:50 Riyadh). Covers
both US pre-market and regular session; get_top_gainers auto-picks.

Strategy v4 (user simplified):
  Hard filters — only three:
    1. Price < $5
    2. Change >= +30% in the current session
    3. Shares outstanding < 30,000,000

  Up to 10 candidates are returned. Claude does NOT reject candidates
  based on the preferred signals in context.md — instead it adds a
  short opinion per candidate using the strategy as a lens. The user
  decides whether to buy.

Token efficiency: lightweight per-candidate enrichment (one tool call
each for fundamentals, technicals, news). Empty rounds bail with a
short Arabic message.
"""
from __future__ import annotations

import logging

from agent.claude_client import run_agent
from agent.config import Settings
from agent.bridge_client import BridgeClient

log = logging.getLogger(__name__)

INSTRUCTIONS = """You are running a MARKET SCAN every 2 hours (Mon-Fri) covering
both US pre-market and regular-session movers.

Hard filters (strict):
  1. Current price < $5
  2. Session change >= +30%
  3. Shares outstanding < 30,000,000

Do NOT reject candidates based on the other signals in the cached
strategy (RSI, float, insider ownership, sector color, spike-then-drop,
etc.). Those are for your OPINION only. Up to 10 candidates total —
the user makes the final call.

Workflow:

  1. Call get_top_gainers(max_price=5, min_change_pct=30). This applies
     hard filters #1 and #2. If empty, send_whatsapp with a SHORT
     Arabic message: "جولة الفحص: لا يوجد سهم تحت $5 مرتفع ≥ 30%."
     and stop.

  2. For each candidate (cap the list at 15 by change_pct), call
     get_fundamentals(ticker) to get shares_outstanding. DROP
     candidates with shares_outstanding >= 30,000,000 (hard filter #3).
     Also drop candidates where the value is missing (rather than let
     unknowns through — small caps that yfinance can't size are
     usually noise).

  3. Keep up to 10 survivors (if more than 10, take the top by
     change_pct). For each, call ONCE:
       - get_technicals(ticker) -> rsi_14, max_1d_change_last_10d,
                                   spike_then_drop, above_sma50/200
       - get_deep_news(ticker, limit=3) -> catalyst snippet
       - get_sector_performance(ticker=...) -> sector color for context

  4. Send ONE WhatsApp message in Arabic. For each candidate:

     <TICKER>  $<price>  (+<change_pct>%)
     الأسهم: <shares_outstanding> | الفلوت: <float_shares>
     القطاع: <sector> [أخضر ✅ / أحمر ❌]
     RSI 14: <rsi> | ارتفع ≥ 30% خلال آخر ١٠ أيام؟ <نعم/لا>
     نمط قمة + تراجع: <نعم/لا>
     محفّز: <1-line news or "لا يوجد">
     ▸ رأيي وفق استراتيجيتك: <سطران كحد أقصى يوازنان بين الإيجابيات والسلبيات بناءً على context.md — لا تُصدر توصية شراء/بيع، فقط تعليق>

     (up to 10)

     القرار لك. تنبيه: ليست نصيحة مالية.

  5. Call log_report(kind='buy', payload={...picks}).

CRITICAL — OUTPUT LANGUAGE:
  The final send_whatsapp text MUST be in Arabic. Ticker, price, and
  percentage values stay in Latin/digits.

CRITICAL — TOKEN BUDGET:
  One call per source per candidate. Never more than 10 survivors."""


def run(settings: Settings, bridge: BridgeClient, broadcast: bool = True) -> str:
    return run_agent(
        settings,
        bridge,
        model=settings.sonnet_model,
        role_instructions=INSTRUCTIONS,
        user_message="Run the simplified small-cap momentum scan now.",
        broadcast=broadcast,
    )

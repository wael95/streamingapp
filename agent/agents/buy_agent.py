"""Agent B — daily small-cap momentum SCAN at 15:30 Riyadh (pre-market).

Implements Mode 1 from config/context.md: scan the US market for pre-
market gainers matching the hard filters (price < $5, change >= +20%,
sector is green), then score each candidate on the preferred/negative
signals and produce a ranked list in Arabic.

Token efficiency: we do NOT have Claude iterate over thousands of
tickers. get_top_gainers returns a pre-filtered list of ~5-30
candidates, and Claude only evaluates those.

Uses Sonnet to keep the cost low (see `SONNET_MODEL` in .env). Switch
back to Opus if ranking quality matters more than cost.
"""
from __future__ import annotations

import logging

from agent.claude_client import run_agent
from agent.config import Settings
from agent.bridge_client import BridgeClient

log = logging.getLogger(__name__)

INSTRUCTIONS = """You are running the DAILY SCAN (Mode 1 from the cached strategy).

Step-by-step workflow:

  1. Call get_top_gainers(max_price=5, min_change_pct=20, premarket=True).
     This returns the candidates that pass the hard price/change filter.
     If empty, call send_whatsapp with "لا توجد فرص اليوم تطابق المعايير." and stop.

  2. Call get_sector_performance() ONCE to know which sectors are green.
     A candidate is only eligible if its sector is green today.
     (You'll see the sector for each candidate after the next step.)

  3. For each remaining candidate (cap at the top 8 by change_pct),
     call get_fundamentals(ticker) to collect:
       - sector (to confirm it's green)
       - market_cap, float_shares, shares_outstanding
       - insider_ownership_pct + institutional_ownership_pct
         (major shareholder ownership = sum of these two, rough proxy)
       - last_split_date / last_split_ratio
     Drop candidates whose sector is NOT green.

  4. For each surviving candidate, ALSO call:
       - get_technicals(ticker) -> RSI, volume context
       - get_deep_news(ticker, limit=5) -> is there a catalyst?
     Keep it to ONE call of each per ticker to save tokens.

  5. Score each candidate out of 10 using the strategy:
       Preferred signals (each +1, except major shareholder which is +2):
         - Low float (float_shares low relative to shares_outstanding)
         - Major shareholder ownership > 30%  (weight x2)
         - Volume >= 10x avg daily volume
         - RSI < 30
         - News catalyst present
       Negative signals (each -1):
         - Shares outstanding > 30M
       Clip to 0..10.
     Recommendation:
       score >= 7  -> شراء
       score 4..6  -> مراقبة
       else        -> تجاهل

  6. Send one WhatsApp message in Arabic. Structure:

     فحص السوق — <date pre-market>
     <for each candidate, highest score first>

     <TICKER>  السعر $<price>  (+<change_pct>%)
     القطاع: <sector> [✅ أخضر / ❌ أحمر]
     السيولة: <volume> (×<rel vs avg> المعدل اليومي)
     الفلوت: <float_shares>  |  الأسهم الكلية: <shares_outstanding>
     حصة المساهمين الأساسيين: <insider_ownership + institutional_ownership>%
     RSI 14: <rsi>
     محفّز: <1-line news or "لا يوجد">
     آخر تقسيم: <date + ratio, or "لا يوجد">
     التقييم: <score>/10  →  <شراء/مراقبة/تجاهل>

     (repeat for each)

     تنبيه: ليست نصيحة مالية.

  7. Call log_report(kind='buy', payload={...picks}).

CRITICAL — OUTPUT LANGUAGE:
  The final send_whatsapp text MUST be in Arabic. Tickers/numbers stay in
  Latin/digits. Never invent numbers; if a field is missing from tools,
  write "—" and skip its score contribution.

CRITICAL — TOKEN BUDGET:
  Do not call any tool more than once per ticker. Do not scan more than
  8 candidates end-to-end."""


def run(settings: Settings, bridge: BridgeClient, broadcast: bool = True) -> str:
    return run_agent(
        settings,
        bridge,
        model=settings.sonnet_model,  # was opus; strategy keeps scan cheap
        role_instructions=INSTRUCTIONS,
        user_message="Run the pre-market small-cap momentum scan now.",
        broadcast=broadcast,
    )

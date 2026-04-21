"""Agent B — daily small-cap momentum SCAN at 15:30 Riyadh (pre-market).

Implements Mode 1 from config/context.md: scan the US market for pre-
market gainers matching the hard filters (price < $5, change >= +20%),
then score each candidate on the preferred/negative signals (including
sector-green as a bonus and shares-outstanding range preference) and
produce a ranked list in Arabic.

Token efficiency: we do NOT have Claude iterate over thousands of
tickers. get_top_gainers returns a pre-filtered list of ~5-30
candidates, and Claude only evaluates those.

Uses Sonnet to keep the cost low. Switch back to Opus via SONNET_MODEL
override if ranking quality matters more than cost.
"""
from __future__ import annotations

import logging

from agent.claude_client import run_agent
from agent.config import Settings
from agent.bridge_client import BridgeClient

log = logging.getLogger(__name__)

INSTRUCTIONS = """You are running the DAILY PRE-MARKET SCAN (Mode 1 from the cached
strategy).

CRITICAL — DATA SOURCE:
  All price/move data must come from the CURRENT DAY'S PRE-MARKET
  session, not yesterday's close. Always call get_top_gainers with
  premarket=True. If the tool returns data that looks like yesterday's
  session (e.g., negligible changes across the board while the market
  is closed), note it in the report but still run the scan.

Step-by-step workflow:

  1. Call get_top_gainers(max_price=5, min_change_pct=20, premarket=True).
     HARD FILTERS (initial): price<$5 and change>=+20% TODAY (pre-market).
     If empty, send_whatsapp("لا توجد فرص اليوم تطابق المعايير في ما قبل السوق.") and stop.

  2. Call get_sector_performance() ONCE (all sectors) so you know which
     sectors are green. Sector-green is a BONUS signal (not a hard filter).

  3. Cap the list to the TOP 12 candidates by change_pct (we'll drop some
     in step 5).

  4. For each candidate, call ONCE each:
       - get_fundamentals(ticker)     -> sector, shares_outstanding,
                                         float_shares, insider_ownership_pct,
                                         institutional_ownership_pct,
                                         last_split_date/ratio
       - get_technicals(ticker)        -> rsi_14, avg volume context,
                                         max_1d_change_last_10d,
                                         spike_then_drop, pct_below_60d_peak
       - get_deep_news(ticker, limit=5) -> catalyst check
     Do NOT call any of these twice. If a field is missing, write "—".

  5. ADDITIONAL HARD FILTER (cleanliness):
     If technicals.max_1d_change_last_10d > 30, DROP the candidate. We
     don't want stocks that already exploded in the last 10 trading
     days — only fresh setups.
     Cap survivors to top 8 by score after applying this filter.

  6. Score each candidate out of 10:
       Preferred signals (+1 each unless noted):
         - Sector is green today              +1
         - Low float (float_shares small)     +1
         - Major shareholder ownership > 30%  +2  (weight x2, most important)
           (major = insider_ownership_pct + institutional_ownership_pct)
         - Volume >= 2-3x avg daily volume    +1
         - RSI_14 < 30                        +1
         - News catalyst in last 48h          +1
         - Shares outstanding in [1M, 30M]    +1
         - Spike-then-drop pattern (technicals.spike_then_drop = true)
                                              +1
       Negative signals (-1 each):
         - Shares outstanding > 30M
         - Shares outstanding < 1M
       Max bonus = 9. Normalize to /10 by scaling
       (final = round(raw * 10 / 9), clipped to 0..10).

     Recommendation by score:
         >= 7  -> شراء
         4..6  -> مراقبة
         else  -> تجاهل

  6. Send ONE WhatsApp message in Arabic, highest score first:

     فحص ما قبل السوق — <date>

     <for each candidate>
     <TICKER>  السعر $<price>  (+<change_pct>%)
     القطاع: <sector>  [أخضر ✅ / أحمر ❌]
     السيولة: <volume> (×<rel vs avg> المعدل)
     الفلوت: <float_shares>  |  الأسهم الكلية: <shares_outstanding>
     حصة المساهمين الأساسيين: <insider+institutional>%
     RSI 14: <rsi>
     أعلى ارتفاع يومي خلال آخر ١٠ أيام: <max_1d_change_last_10d>%
     النمط: <spike_then_drop ? "قمة ثم تراجع ✅" : "لا يوجد نمط واضح">
     محفّز: <1-line news or "لا يوجد">
     آخر تقسيم: <date + ratio, or "لا يوجد">
     التقييم: <score>/10  →  <شراء/مراقبة/تجاهل>

     (repeat for each)

     تنبيه: ليست نصيحة مالية.

  7. Call log_report(kind='buy', payload={...picks}).

CRITICAL — OUTPUT LANGUAGE:
  The final send_whatsapp text MUST be in Arabic. Tickers, prices,
  percentages, and dates stay in Latin/digits. Never invent numbers.

CRITICAL — TOKEN BUDGET:
  One call per source per ticker. No more than 8 candidates end-to-end."""


def run(settings: Settings, bridge: BridgeClient, broadcast: bool = True) -> str:
    return run_agent(
        settings,
        bridge,
        model=settings.sonnet_model,
        role_instructions=INSTRUCTIONS,
        user_message="Run the pre-market small-cap momentum scan now.",
        broadcast=broadcast,
    )

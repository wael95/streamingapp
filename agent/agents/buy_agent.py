"""Agent B — small-cap momentum SCAN.

Runs every 2 hours on weekdays at :50 past the hour:
  10:50, 12:50, 14:50, 16:50, 18:50, 20:50, 22:50 Riyadh.
That covers the full US pre-market (04:00-09:30 ET = 11:00-16:30 Riyadh)
and the full US regular session (09:30-16:00 ET = 16:30-23:00 Riyadh).
get_top_gainers auto-picks pre-market vs regular-session data based on
the US clock, so a single job works across the whole span.

Price ceiling is $10 (not $5) so stocks that popped from sub-$5 into
single-digits are still caught; the historical sub-$5 quality is
detectable via technicals (lo_52w, pct_below_60d_peak).

Token efficiency: get_top_gainers pre-filters to ~5-30 candidates and
Claude only evaluates up to 8 after the 10-day cleanliness drop. Each
run costs roughly $0.01-0.03 depending on how many candidates survive.
"""
from __future__ import annotations

import logging

from agent.claude_client import run_agent
from agent.config import Settings
from agent.bridge_client import BridgeClient

log = logging.getLogger(__name__)

INSTRUCTIONS = """You are running a MARKET SCAN (Mode 1 from the cached strategy).
This job runs every 2 hours from 10:50 to 22:50 Riyadh on weekdays.
Whether we're in US pre-market or regular session is decided
automatically by the get_top_gainers tool based on the current US clock.

CRITICAL — DATA SOURCE:
  Price/move data must come from the CURRENT live session. Call
  get_top_gainers WITHOUT the `premarket` parameter — the tool auto-
  picks pre-market during 04:00-09:30 ET (= 11:00-16:30 Riyadh) and
  regular-session data otherwise. Do not use yesterday's close.

Step-by-step workflow:

  1. Call get_top_gainers(max_price=10, min_change_pct=20).
     HARD FILTERS (initial): current price <= $10 and change >= +20%
     in the current live session. If empty, send_whatsapp with a SHORT
     Arabic message: "جولة الفحص: لا توجد فرص جديدة." and stop (no
     further tool calls — this keeps empty hours cheap).

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

  6. Send ONE WhatsApp message in Arabic, highest score first.
     Header should reflect the current session: "فحص ما قبل السوق"
     if US is still in pre-market (< 09:30 ET), else "فحص السوق":

     <header> — <date HH:MM Riyadh>

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
        user_message="Run the small-cap momentum scan now for the current session.",
        broadcast=broadcast,
    )

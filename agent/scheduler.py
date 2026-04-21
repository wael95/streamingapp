"""APScheduler wiring.

Three cron triggers, all in Asia/Riyadh (no DST), weekdays only:
  03:00  refresh_universe  (nightly OHLCV cache)
  15:50  watchlist_agent   (Agent A - Sonnet)
  15:50  buy_agent         (Agent B - Opus)

We use `BackgroundScheduler` because we also want the main thread free
for the inbound WhatsApp poll loop.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from agent.agents import buy_agent, watchlist_agent
from agent.bridge_client import BridgeClient
from agent.config import Settings
from agent.data import ohlcv_cache

log = logging.getLogger(__name__)


def build_scheduler(settings: Settings, bridge: BridgeClient) -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone=settings.tz)

    def _refresh():
        log.info("job_fired: refresh_universe")
        rules = settings.rules or {}
        ohlcv_cache.refresh_universe(
            adapter_name=settings.data_adapter,
            universe_setting=rules.get("universe", "sp500_plus_watchlist"),
            watchlist=settings.watchlist_tickers,
            days=int(rules.get("lookback_days", 260)),
        )

    def _watchlist():
        log.info("job_fired: watchlist_agent")
        try:
            watchlist_agent.run(settings, bridge)
        except Exception:
            log.exception("watchlist_agent failed")

    def _buy():
        log.info("job_fired: buy_agent")
        try:
            buy_agent.run(settings, bridge)
        except Exception:
            log.exception("buy_agent failed")

    # Schedule (Asia/Riyadh, weekdays):
    #   03:00  nightly OHLCV refresh (no API/WhatsApp, just cache warm-up)
    #   15:30  buy scan (Mode 1 per context.md — pre-market gainers scan)
    #   15:50  watchlist digest (the 7 small-caps in watchlist.yml)
    # US pre-market runs 04:00-09:30 ET; 15:30 Riyadh = 08:30 ET (mid-pre-market),
    # 15:50 Riyadh = 08:50 ET (40 min before US open).
    sched.add_job(
        _refresh, CronTrigger(day_of_week="mon-fri", hour=3, minute=0),
        id="refresh_universe", replace_existing=True,
    )
    sched.add_job(
        _buy, CronTrigger(day_of_week="mon-fri", hour=15, minute=30),
        id="buy_agent", replace_existing=True,
    )
    sched.add_job(
        _watchlist, CronTrigger(day_of_week="mon-fri", hour=15, minute=50),
        id="watchlist_agent", replace_existing=True,
    )
    return sched

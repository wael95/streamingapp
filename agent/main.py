"""Agent entrypoint.

Without arguments: starts the long-running process — scheduler + inbound
WhatsApp poll loop. Used by launchd.

With `--run <name>`: runs a single job and exits. Useful for verification.
  python -m agent.main --run watchlist
  python -m agent.main --run buy
  python -m agent.main --run refresh
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

from agent.agents import buy_agent, chat_agent, watchlist_agent
from agent.bridge_client import BridgeClient
from agent.config import load_settings
from agent.data import ohlcv_cache
from agent.db import store
from agent.logging_conf import configure
from agent.scheduler import build_scheduler

log = logging.getLogger(__name__)


def _oneshot(name: str, settings, bridge: BridgeClient) -> int:
    if name == "watchlist":
        watchlist_agent.run(settings, bridge)
        return 0
    if name == "buy":
        buy_agent.run(settings, bridge)
        return 0
    if name == "refresh":
        rules = settings.rules or {}
        ohlcv_cache.refresh_universe(
            adapter_name=settings.data_adapter,
            universe_setting=rules.get("universe", "sp500_plus_watchlist"),
            watchlist=settings.watchlist_tickers,
            days=int(rules.get("lookback_days", 260)),
        )
        return 0
    print(f"unknown --run target: {name}", file=sys.stderr)
    return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="one-shot job: watchlist | buy | refresh")
    args = ap.parse_args()

    settings = load_settings()
    configure(settings.log_dir)
    store.init(settings.db_path)
    bridge = BridgeClient(settings)

    if args.run:
        return _oneshot(args.run, settings, bridge)

    log.info("agent starting; tz=%s bridge=%s", settings.tz, settings.bridge_url)
    sched = build_scheduler(settings, bridge)
    sched.start()

    stop = {"flag": False}

    def _graceful(*_):
        log.info("shutdown signal received")
        stop["flag"] = True

    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)

    # Bridge poll loop runs on the main thread.
    def handler(jid: str, text: str, number: str | None = None) -> None:
        chat_agent.handle(settings, bridge, jid, text, number)

    try:
        while not stop["flag"]:
            try:
                bridge.poll_forever(handler)
            except KeyboardInterrupt:
                break
            except Exception:
                log.exception("poll loop crashed; restarting in 5s")
                time.sleep(5)
    finally:
        sched.shutdown(wait=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

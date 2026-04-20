"""Claude tool definitions and dispatcher.

Every tool the model can call is registered here with its JSON schema.
`dispatch(name, input, ctx)` actually runs the tool and returns a string
(JSON or plain text) that gets fed back to Claude as a `tool_result`.

Keep the schemas tight — narrower types mean Claude hallucinates less.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from agent.tools import (
    context_io,
    edgar,
    fundamentals,
    news,
    news_sources,
    quotes,
    screen,
    technicals,
    whatsapp,
)


def _schema(name: str, desc: str, props: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": desc,
        "input_schema": {
            "type": "object",
            "properties": props,
            "required": required,
        },
    }


TOOL_SCHEMAS: list[dict] = [
    _schema(
        "get_quote",
        "Get current price, day change, day range and volume for a single US stock ticker.",
        {"ticker": {"type": "string", "description": "e.g. AAPL, NVDA"}},
        ["ticker"],
    ),
    _schema(
        "get_news",
        "Get recent news headlines for a ticker.",
        {
            "ticker": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 15, "default": 5},
        },
        ["ticker"],
    ),
    _schema(
        "get_fundamentals",
        "Get market cap, P/E, EPS, dividend yield, sector and next earnings date.",
        {"ticker": {"type": "string"}},
        ["ticker"],
    ),
    _schema(
        "screen_stocks",
        "Run the YAML-configured screener. Returns up to max_results tickers that pass all rules.",
        {
            "rules_override": {
                "type": "object",
                "description": "Optional: override rules.yml for this call. Keys: conditions, max_results, universe.",
            }
        },
        [],
    ),
    _schema(
        "read_context",
        "Read the user's investing-context markdown file (strategy, holdings, preferences).",
        {},
        [],
    ),
    _schema(
        "log_report",
        "Persist a structured report for history/audit.",
        {
            "kind": {"type": "string", "enum": ["watchlist", "buy", "lookup", "chat"]},
            "ticker": {"type": "string"},
            "payload": {"type": "object"},
        },
        ["kind", "payload"],
    ),
    _schema(
        "send_whatsapp",
        "Send a message to the owner's WhatsApp. Use this to deliver the final report at the end of scheduled runs. The 'to' field is fixed to the owner; you cannot send to arbitrary numbers.",
        {"text": {"type": "string"}},
        ["text"],
    ),
    _schema(
        "get_technicals",
        "Compute a full set of technical indicators for a ticker (SMA 20/50/200, EMA 12/26, RSI 14, MACD, Bollinger Bands, ATR, Stochastic, OBV, ADX, 52w high/low distance, golden/death cross flags). Free, offline, TradingView-parity.",
        {"ticker": {"type": "string"}},
        ["ticker"],
    ),
    _schema(
        "get_insider_filings",
        "Recent SEC Form 4 insider transactions for a ticker (officers and directors buying/selling). Returns date, insider name/title, action (buy/sell/award), shares, price, total value.",
        {
            "ticker": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 30, "default": 10},
        },
        ["ticker"],
    ),
    _schema(
        "get_recent_sec_filings",
        "Recent 8-K / 10-Q / 10-K / S-1 filings for a ticker from SEC EDGAR (material events and quarterly/annual reports).",
        {
            "ticker": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 30, "default": 10},
        },
        ["ticker"],
    ),
    _schema(
        "get_deep_news",
        "Broader news + sentiment fetch combining Yahoo RSS, StockTwits (with sentiment labels), Reddit (WSB/investing/stocks), and NewsAPI (if NEWSAPI_KEY set). Deduped and time-sorted.",
        {
            "ticker": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 40, "default": 20},
        },
        ["ticker"],
    ),
]


def dispatch(name: str, tool_input: dict, ctx: dict) -> str:
    settings = ctx["settings"]
    bridge = ctx.get("bridge")

    if name == "get_quote":
        return _json(quotes.get_quote(settings, tool_input["ticker"]))
    if name == "get_news":
        limit = int(tool_input.get("limit", 5))
        return _json(news.get_news(settings, tool_input["ticker"], limit))
    if name == "get_fundamentals":
        return _json(fundamentals.get_fundamentals(settings, tool_input["ticker"]))
    if name == "screen_stocks":
        return _json(screen.screen_stocks(settings, tool_input.get("rules_override")))
    if name == "read_context":
        return context_io.read_context(settings)
    if name == "log_report":
        context_io.log_report(tool_input.get("kind"), tool_input.get("ticker"), tool_input.get("payload") or {})
        return "ok"
    if name == "send_whatsapp":
        if bridge is None:
            return "error: bridge not available"
        whatsapp.send_whatsapp(bridge, tool_input["text"])
        return "sent"
    if name == "get_technicals":
        return _json(technicals.get_technicals(settings, tool_input["ticker"]))
    if name == "get_insider_filings":
        limit = int(tool_input.get("limit", 10))
        return _json(edgar.get_insider_filings(settings, tool_input["ticker"], limit))
    if name == "get_recent_sec_filings":
        limit = int(tool_input.get("limit", 10))
        return _json(edgar.get_recent_filings(settings, tool_input["ticker"], limit))
    if name == "get_deep_news":
        limit = int(tool_input.get("limit", 20))
        return _json(news_sources.get_deep_news(tool_input["ticker"], limit))
    return f"error: unknown tool {name}"


def _json(obj: Any) -> str:
    return json.dumps(obj, default=str, ensure_ascii=False)

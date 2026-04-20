"""Shared Claude agent loop.

One function, `run_agent`, drives all three sub-agents (watchlist, buy,
chat). Differences between them are just:
  * the model id (Sonnet vs Opus),
  * the role-specific system instructions,
  * the user message,
  * whether a session_id is supplied (ad-hoc chat is persistent per JID,
    scheduled runs are stateless).

Prompt caching
--------------
The static system block (preamble + context.md + watchlist YAML) is marked
with `cache_control: ephemeral`. That means repeated calls within ~5 min
reuse the cached tokens at ~10% cost; across longer gaps the 1-hour cache
still helps for the morning's cluster of jobs. We log
`usage.cache_read_input_tokens` so you can see caching working.

Model IDs (April 2026)
----------------------
  Opus 4.7:    claude-opus-4-7
  Sonnet 4.6:  claude-sonnet-4-6
  Haiku 4.5:   claude-haiku-4-5-20251001
Override via `.env` (SONNET_MODEL, OPUS_MODEL).
"""
from __future__ import annotations

import logging
from typing import Any

from anthropic import Anthropic

from agent.config import Settings
from agent.db import store
from agent.tools import TOOL_SCHEMAS, dispatch

log = logging.getLogger(__name__)

PREAMBLE = """You are a personal stock-market assistant for the user.
You operate over WhatsApp and via scheduled daily jobs. Keep all messages
concise and mobile-friendly: use short lines, bullets, and no markdown
tables. Never invent numbers — always call tools for current data. When
you make a recommendation, anchor it to the user's context (holdings,
risk tolerance, sector views) from the cached context block below. If
you are unsure or data is missing, say so plainly."""


def _static_system_block(settings: Settings) -> dict:
    context_md = (
        settings.context_md_path.read_text(encoding="utf-8")
        if settings.context_md_path.exists()
        else "(no context.md provided)"
    )
    watchlist = settings.watchlist or {}
    wl_text = "\n".join(f"- {t}" for t in (watchlist.get("tickers") or []))
    notes = watchlist.get("notes") or {}
    note_text = "\n".join(f"- {k}: {v}" for k, v in notes.items())
    return {
        "type": "text",
        "text": (
            f"{PREAMBLE}\n\n"
            f"# User context (from config/context.md)\n{context_md}\n\n"
            f"# Default watchlist\n{wl_text or '(empty)'}\n\n"
            f"# Watchlist notes\n{note_text or '(none)'}"
        ),
        "cache_control": {"type": "ephemeral"},
    }


def run_agent(
    settings: Settings,
    bridge,
    *,
    model: str,
    role_instructions: str,
    user_message: str,
    session_id: str | None = None,
    max_turns: int = 8,
) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    system = [
        _static_system_block(settings),
        {"type": "text", "text": role_instructions},
    ]

    history: list[dict[str, Any]] = []
    if session_id:
        history = store.get_session(session_id)[-40:]  # keep last ~20 turns
    history.append({"role": "user", "content": user_message})

    ctx = {"settings": settings, "bridge": bridge}
    final_text = ""

    for turn in range(max_turns):
        resp = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            tools=TOOL_SCHEMAS,
            messages=history,
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            log.info(
                "claude turn=%d in=%s out=%s cache_read=%s cache_write=%s",
                turn,
                getattr(usage, "input_tokens", None),
                getattr(usage, "output_tokens", None),
                getattr(usage, "cache_read_input_tokens", None),
                getattr(usage, "cache_creation_input_tokens", None),
            )

        blocks = resp.content or []
        # Record the assistant turn verbatim so tool_use IDs line up.
        history.append(
            {"role": "assistant", "content": [b.model_dump() for b in blocks]}
        )

        tool_uses = [b for b in blocks if b.type == "tool_use"]
        text_blocks = [b for b in blocks if b.type == "text"]
        if text_blocks:
            final_text = "\n".join(b.text for b in text_blocks).strip()

        if not tool_uses or resp.stop_reason != "tool_use":
            break

        tool_results = []
        for tu in tool_uses:
            try:
                result = dispatch(tu.name, tu.input or {}, ctx)
            except Exception as e:
                log.exception("tool %s failed", tu.name)
                result = f"error: {e}"
            tool_results.append(
                {"type": "tool_result", "tool_use_id": tu.id, "content": result}
            )
        history.append({"role": "user", "content": tool_results})

    if session_id:
        store.save_session(session_id, history)

    return final_text

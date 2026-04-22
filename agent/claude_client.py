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
    reply_to: str | None = None,
    broadcast: bool = False,
    max_turns: int = 8,
) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    system = [
        _static_system_block(settings),
        {"type": "text", "text": role_instructions},
    ]

    history: list[dict[str, Any]] = []
    if session_id:
        # Defensive: any session saved by an older build may still contain
        # tool_use / tool_result blocks that would break Claude on reload.
        # Re-simplify whatever we read before using it.
        history = _simplify_history(store.get_session(session_id))[-40:]
    history.append({"role": "user", "content": user_message})

    # `reply_to` is consumed by the send_whatsapp tool. Scheduled jobs
    # pass None -> defaults to OWNER_JID inside bridge.send. Chat passes
    # the sender's JID so replies go back to whoever asked.
    ctx = {
        "settings": settings,
        "bridge": bridge,
        "reply_to": reply_to,
        "broadcast": broadcast,
    }
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
        store.save_session(session_id, _simplify_history(history))

    return final_text


def _simplify_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compress persistent session history to plain-text turns only.

    The live in-loop `history` contains tool_use (assistant) and
    tool_result (user) blocks. Persisting those across turns causes
    Anthropic API 400s on reload: trimming to [-40:] can leave an
    orphan `tool_result` at index 0 with no preceding `tool_use`, or
    two adjacent user messages. Since cross-turn memory only needs the
    user's question and Claude's final answer, we collapse each
    assistant turn to its concatenated text blocks and drop any user
    turn whose content is a tool_result list.
    """
    simplified: list[dict[str, Any]] = []
    for msg in history:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            if isinstance(content, str) and content.strip():
                simplified.append({"role": "user", "content": content})
            # Drop tool_result lists — they carry no cross-turn meaning.
        elif role == "assistant":
            if isinstance(content, str):
                simplified.append(msg)
            elif isinstance(content, list):
                texts = [
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                joined = "\n".join(t for t in texts if t).strip()
                if joined:
                    simplified.append({"role": "assistant", "content": joined})
    # Avoid two consecutive same-role messages (a compressed artifact
    # that the API also rejects).
    deduped: list[dict[str, Any]] = []
    for msg in simplified:
        if deduped and deduped[-1]["role"] == msg["role"]:
            deduped[-1] = msg
        else:
            deduped.append(msg)
    return deduped

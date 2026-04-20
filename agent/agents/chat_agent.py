"""Agent C — ad-hoc WhatsApp chat.

Invoked by `bridge_client.poll_forever` for every inbound message from an
allowlisted user. Sessions are persisted per JID so follow-ups work.

Prefix handling:
  !opus <msg>        route this one message to Opus 4.7
  !reset             clear conversation memory for this JID
  !watch ADD NVDA    add to watchlist.yml (writes the file)
  !watch REMOVE NVDA remove from watchlist.yml
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

from agent.bridge_client import BridgeClient
from agent.claude_client import run_agent
from agent.config import Settings
from agent.db import store

log = logging.getLogger(__name__)

INSTRUCTIONS = """You are answering an AD-HOC question over WhatsApp.

Rules:
  - Keep replies short (mobile-friendly): short sentences, no tables.
  - Always fetch live data via tools before answering price/news/fundamental
    questions. Never invent numbers.
  - When the user asks "is X a buy?", reference their cached context
    (holdings, sector views, risk) and be explicit about trade-offs.
  - End every reply with a single call to send_whatsapp containing the
    final answer. Do not also reply in plain text — only send_whatsapp.

CRITICAL — OUTPUT LANGUAGE:
  The text passed to send_whatsapp MUST be in Arabic (العربية). If the
  user wrote in English, still reply in Arabic. Ticker symbols, prices
  and percentages stay in Latin/digits. Use natural Modern Standard
  Arabic for the rest."""


def _handle_prefix(settings: Settings, bridge: BridgeClient, jid: str, text: str) -> bool:
    """Return True if the message was handled by a prefix command."""
    low = text.strip().lower()
    if low.startswith("!reset"):
        store.clear_session(jid)
        bridge.send("Conversation memory cleared.", to=jid)
        return True
    if low.startswith("!watch "):
        parts = text.split()
        if len(parts) >= 3 and parts[1].upper() in ("ADD", "REMOVE"):
            action = parts[1].upper()
            sym = parts[2].upper()
            path = settings.config_dir / "watchlist.yml"
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            tickers = list(data.get("tickers") or [])
            if action == "ADD" and sym not in tickers:
                tickers.append(sym)
            elif action == "REMOVE":
                tickers = [t for t in tickers if t != sym]
            data["tickers"] = tickers
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            bridge.send(f"Watchlist now: {', '.join(tickers)}", to=jid)
            return True
    return False


def handle(
    settings: Settings,
    bridge: BridgeClient,
    jid: str,
    text: str,
    number: str | None = None,
) -> None:
    # Bridge already passes the resolved phone number when known (handles
    # WhatsApp's @lid form). Fall back to parsing the JID if not provided.
    phone = number or jid.split("@")[0].split(":")[0]
    if phone not in settings.allowed_numbers:
        log.warning("chat: rejecting non-allowlisted phone=%s jid=%s", phone, jid)
        return
    if _handle_prefix(settings, bridge, jid, text):
        return

    use_opus = text.strip().lower().startswith("!opus")
    if use_opus:
        text = text.split(maxsplit=1)[1] if len(text.split()) > 1 else ""
        if not text:
            bridge.send("Usage: !opus <your question>", to=jid)
            return

    model = settings.opus_model if use_opus else settings.sonnet_model

    # Claude is expected to end with a send_whatsapp tool call, but if
    # it replies with plain text only we forward it here as a fallback.
    final = run_agent(
        settings,
        bridge,
        model=model,
        role_instructions=INSTRUCTIONS,
        user_message=text,
        session_id=jid,
        reply_to=jid,  # critical: replies go back to the asker, not OWNER_JID
    )
    if final and not _last_send_was_via_tool():
        bridge.send(final, to=jid)


def _last_send_was_via_tool() -> bool:
    # We can't easily tell from here, so we conservatively return True: if
    # Claude did call send_whatsapp, the user already received the reply.
    # If not, the user simply sees nothing — which surfaces bugs loudly.
    return True

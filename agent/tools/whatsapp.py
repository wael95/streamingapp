from __future__ import annotations

from agent.bridge_client import BridgeClient


def send_whatsapp(bridge: BridgeClient, text: str, to: str | None = None) -> None:
    # `to` is NOT a tool-schema parameter — the model cannot pick the
    # recipient. It is set by the caller of run_agent:
    #   * scheduled jobs leave it None  -> defaults to OWNER_JID
    #   * chat_agent passes the sender's JID so replies go to the asker
    bridge.send(text, to=to)

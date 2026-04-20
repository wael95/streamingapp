from __future__ import annotations

from agent.bridge_client import BridgeClient


def send_whatsapp(bridge: BridgeClient, text: str) -> None:
    # `to` is intentionally not exposed as a tool parameter; the bridge
    # client already defaults to settings.owner_jid. This prevents the
    # model from sending messages to arbitrary numbers.
    bridge.send(text)

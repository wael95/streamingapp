from __future__ import annotations

from agent.bridge_client import BridgeClient


def send_whatsapp(
    bridge: BridgeClient,
    text: str,
    to: str | None = None,
    broadcast: bool = False,
) -> None:
    # `to` / `broadcast` are NOT tool-schema parameters — the model cannot
    # pick the recipient. They're set by the caller of run_agent:
    #   * scheduled jobs set broadcast=True  -> every allowlisted number
    #   * chat_agent sets to=sender JID      -> reply to the asker
    #   * otherwise defaults to OWNER_JID
    if broadcast:
        bridge.broadcast(text)
    else:
        bridge.send(text, to=to)

"""HTTP client for the Node WhatsApp bridge.

Two uses:
  * `send(text, to=None)`  - outbound message; defaults to `OWNER_JID`.
  * `poll_forever(handler)` - long-running loop that fetches new inbound
    messages and hands each one to `handler(jid, text)`. The DB stores the
    cursor so restarts don't replay old messages.

The bridge is a local process bound to 127.0.0.1, so we use short timeouts.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

import httpx

from agent.config import Settings
from agent.db import store

log = logging.getLogger(__name__)


class BridgeClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.Client(
            base_url=settings.bridge_url,
            headers={"Authorization": f"Bearer {settings.bridge_token}"},
            timeout=10.0,
        )

    def health(self) -> dict:
        return self.http.get("/health").json()

    def send(self, text: str, to: str | None = None) -> None:
        jid = to or self.settings.owner_jid
        chunks = _chunk(text, 3500)
        for c in chunks:
            r = self.http.post("/send", json={"to": jid, "text": c})
            r.raise_for_status()
            store.log_message(jid, "out", c)

    def broadcast(self, text: str) -> None:
        """Send to every allowlisted number (scheduled jobs use this)."""
        for num in self.settings.allowed_numbers:
            jid = f"{num}@s.whatsapp.net"
            try:
                self.send(text, to=jid)
            except Exception:
                log.exception("broadcast send failed to %s", jid)

    def poll_forever(self, handler: Callable[..., None], interval: float = 2.0) -> None:
        while True:
            try:
                cursor = store.get_cursor()
                r = self.http.get("/poll", params={"since": cursor})
                r.raise_for_status()
                data = r.json()
                for m in data.get("messages", []):
                    jid = m["from"]
                    text = m["text"]
                    number = m.get("number")
                    store.log_message(jid, "in", text)
                    try:
                        handler(jid, text, number)
                    except Exception:
                        log.exception("chat handler failed jid=%s", jid)
                if data.get("cursor") is not None:
                    store.set_cursor(int(data["cursor"]))
            except Exception:
                log.exception("bridge poll failed")
            time.sleep(interval)


def _chunk(s: str, n: int) -> list[str]:
    if len(s) <= n:
        return [s]
    out: list[str] = []
    while s:
        out.append(s[:n])
        s = s[n:]
    return out

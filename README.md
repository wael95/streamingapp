# WhatsApp Stock Agent

Personal AI agent that runs on your Mac, reads US stock market data, and chats with you on WhatsApp. Sends a daily watchlist update and a "what to buy" shortlist at 3:50 PM Riyadh (Mon–Fri), and answers ad-hoc questions like "look up NVDA" or "is AAPL a buy?".

Architecture:
- **Python agent** (Anthropic SDK + APScheduler + yfinance + SQLite) — scheduling, data, screening, Claude calls.
- **Node bridge** (Baileys + Fastify) — sends/receives WhatsApp on your personal number via QR login.
- They talk over `127.0.0.1` with a bearer token. Both run forever under `launchd` with `KeepAlive=true`.

## Setup (one-time)

1. Install deps:
   ```sh
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cd whatsapp_bridge && npm install && cd ..
   ```
2. Copy templates and fill in:
   ```sh
   cp .env.example .env
   cp config/context.md.example config/context.md
   # edit .env, config/context.md, config/watchlist.yml, config/rules.yml
   ```
   Generate a bridge token: `openssl rand -hex 32` → paste into `BRIDGE_TOKEN`.
3. First-run QR scan (one terminal):
   ```sh
   node whatsapp_bridge/src/index.js
   ```
   Scan with WhatsApp on your phone. Once logged in, `Ctrl-C`.
4. Install launch agents:
   ```sh
   ./scripts/load_launchd.sh
   ```

## Verification

```sh
# Bridge reachable?
curl -H "Authorization: Bearer $BRIDGE_TOKEN" http://127.0.0.1:8787/health

# Trigger the watchlist agent now
.venv/bin/python -m agent.main --run watchlist

# Trigger the buy screener now
.venv/bin/python -m agent.main --run buy

# Watch logs
tail -f logs/*.log
```

Then WhatsApp-message yourself: `look up NVDA` or `is AAPL a buy?`.

## WhatsApp commands

- `!opus <question>` — route this one message to Opus 4.7.
- `!reset` — clear conversation memory for your JID.
- `!watch ADD NVDA` / `!watch REMOVE NVDA` — edit watchlist.

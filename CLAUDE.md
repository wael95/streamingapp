# CLAUDE.md — working notes for AI contributors

This file is for future Claude sessions (any account) that pick up this
repo. Read it **before** editing anything. It encodes the architectural
decisions that are not obvious from the code alone.

## What this project is

A personal WhatsApp AI agent that runs forever on the owner's Mac. It:
- Sends a **daily watchlist digest** at 15:50 Riyadh (Mon–Fri).
- Sends **"what to buy today" ideas** at 15:50 Riyadh (Mon–Fri), filtered
  by user-defined rules and ranked by Claude using the user's own
  investing-context markdown.
- Answers **ad-hoc WhatsApp questions** like "look up NVDA" or "is AAPL a
  buy?" at any time of day, with per-contact conversation memory.
- Only talks to **allowlisted phone numbers** (strict — the whole point
  is this is a private personal tool).

The owner is in Saudi Arabia. Timezone is `Asia/Riyadh` everywhere.

## High-level architecture

```
┌──────────────────────── macOS (launchd user agents) ────────────────────────┐
│                                                                             │
│  ┌─────────────────────┐      127.0.0.1:8787      ┌────────────────────┐    │
│  │ whatsapp_bridge     │◀────── Bearer token ────▶│  agent (Python)    │    │
│  │ Node + Baileys +    │       POST /send         │  APScheduler +     │    │
│  │ Fastify (loopback)  │       GET  /poll         │  Anthropic SDK +   │    │
│  │                     │       GET  /health       │  yfinance + SQLite │    │
│  └─────────┬───────────┘                          └──────────┬─────────┘    │
│            │                                                  │              │
│            ▼                                                  ▼              │
│      WhatsApp Web                                 data/stockagent.db (WAL)  │
│      (personal #,                                 config/*.yml, context.md  │
│       QR once)                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

Two long-running processes, both under `launchd` with `KeepAlive=true`:

1. **`whatsapp_bridge/`** (Node, ESM). Owns the Baileys socket, receives
   inbound messages from allowlisted senders only, exposes a tiny
   loopback HTTP API. Session files in `whatsapp_bridge/auth/` (gitignored).
2. **`agent/`** (Python). Runs APScheduler (with `Asia/Riyadh` CronTrigger),
   polls the bridge for inbound messages, calls Claude for every
   scheduled job and every ad-hoc reply.

Scheduling is **internal** (APScheduler inside the long-lived Python
process), **not** `launchd StartCalendarInterval`. This is because the
agent must also handle ad-hoc chat all day, so the process has to stay up
anyway.

## Key design decisions (and why)

- **Unofficial WhatsApp (Baileys), not Cloud API.** The owner uses his
  personal number. Baileys is free and works fine for personal use.
  Tradeoff: WhatsApp can ban the number if it behaves spammily; we
  rate-limit outbound to 20/min in the bridge as a safety net.
- **Hybrid Python + Node.** Python is best for stock data and AI libs;
  Node has the actively-maintained Baileys. They talk over `127.0.0.1`
  with a bearer token. `127.0.0.1` binding + allowlist is the real
  security boundary — the bearer token is belt-and-suspenders.
- **Nightly OHLCV pre-fetch (03:00 Riyadh).** yfinance is rate-limited
  and periodically broken by Yahoo. Pre-fetching one year of bars for the
  whole universe into SQLite means the 15:50 screener is instant and
  resilient. The `ohlcv_cache` table is the single source of truth for
  price history; `yfinance` is only hit by the nightly job and by
  ad-hoc quote/news/fundamentals lookups.
- **Pluggable data adapter.** `agent/data/base.py` defines a narrow ABC.
  `.env` `DATA_ADAPTER` selects the implementation (`yfinance` by default;
  stubs for `finnhub` and `alpha_vantage`). Do not import a specific
  adapter module from anywhere except `agent/data/__init__.py`.
- **Rules-first then Claude.** The buy screener is a deterministic
  pandas/numpy filter defined in `config/rules.yml`. Claude only sees
  the shortlist (≤15 tickers). This keeps token usage bounded and
  auditable. Claude's job is to rank + explain, not to generate the
  candidates.
- **Single shared agent loop.** `agent/claude_client.run_agent` is the
  one function that actually talks to Claude. The three "agents"
  (watchlist / buy / chat) are thin wrappers that differ only in:
  the system instructions, the model, and whether a `session_id` is
  supplied (scheduled runs are stateless; chat is persistent per JID).
- **Prompt caching.** `context.md` + watchlist go into a single system
  content block tagged `cache_control: ephemeral`. Caching saves money
  both within a day (watchlist + buy jobs run minutes apart) and across
  days via the 1-hour cache.
- **Model selection.**
  - `SONNET_MODEL=claude-sonnet-4-6` — daily watchlist, ad-hoc chat.
  - `OPUS_MODEL=claude-opus-4-7` — buy ranking, `!opus` prefix chats.
  - Haiku is available as `claude-haiku-4-5-20251001` if you ever want a
    cheaper intent classifier.
- **`send_whatsapp` is locked to `OWNER_JID`.** The tool schema does not
  expose a `to` field. This prevents the model from exfiltrating
  messages to arbitrary numbers even if prompt-injected by, say, news
  content.
- **Weekdays only.** US market is closed Sat/Sun. Cron triggers use
  `day_of_week='mon-fri'`. US holidays are not auto-detected; add a
  holiday check if this becomes a nuisance.

## Directory map

```
agent/                       Python package
  main.py                    entrypoint — scheduler + inbound poll loop
  scheduler.py               APScheduler wiring (3 cron jobs)
  claude_client.py           run_agent loop + prompt caching
  bridge_client.py           HTTP client for Node bridge (send + poll)
  config.py                  Settings dataclass loaded from .env + YAML
  logging_conf.py            rotating logs -> logs/agent.log
  agents/
    watchlist_agent.py       Agent A (Sonnet, 15:50)
    buy_agent.py             Agent B (Opus, 15:50)
    chat_agent.py            Agent C (ad-hoc, per-JID memory)
  tools/
    __init__.py              TOOL_SCHEMAS + dispatch()
    quotes.py news.py fundamentals.py screen.py context_io.py whatsapp.py
  data/
    base.py                  StockDataAdapter ABC
    yfinance_adapter.py      default; tenacity-wrapped
    finnhub_adapter.py       stub
    alpha_vantage_adapter.py stub
    universe.py              S&P 500 ∪ watchlist loader
    sp500.csv                static list (starter ~120 names; expand freely)
    ohlcv_cache.py           nightly pre-fetch
  screening/
    engine.py                YAML rules -> pandas filter
    indicators.py            RSI, SMA, golden_cross, change_pct
  db/
    schema.sql               SQLite DDL
    store.py                 single-connection sqlite3 wrapper (WAL)

whatsapp_bridge/             Node ESM
  src/
    index.js                 boot
    baileys.js               socket, reconnect, inbound filter
    api.js                   POST /send, GET /poll, GET /health (bearer)
    queue.js                 in-memory ring buffer
    config.js                .env loader
  auth/                      Baileys session (gitignored)

config/
  watchlist.yml              user's default watchlist
  rules.yml                  screening rules DSL
  context.md                 user's investing strategy (gitignored)
  context.md.example         template

launchd/
  com.user.stockagent.bridge.plist
  com.user.stockagent.agent.plist

scripts/
  load_launchd.sh            install & load plists (substitutes REPO_ROOT)
  unload_launchd.sh

logs/   (gitignored)
data/stockagent.db   (gitignored, WAL)
```

## Data flow cheat sheet

**Scheduled run at 15:50:**
1. APScheduler fires `buy_job` / `watchlist_job` on worker thread.
2. Job builds system prompt (cached context.md + watchlist).
3. Calls `run_agent` → Claude with tools.
4. Claude calls `screen_stocks` (which reads `ohlcv_cache` only — no
   network) and/or `get_quote`/`get_news`/`get_fundamentals`.
5. Claude finishes by calling `send_whatsapp` → Python posts `POST /send`
   on the bridge → Baileys sends to `OWNER_JID`.
6. `log_report` writes a row to `reports` for history.

**Ad-hoc WhatsApp message:**
1. User sends WhatsApp to the bridged number.
2. Baileys upsert handler checks the sender is in `ALLOWED_NUMBERS`;
   drops otherwise. Allowed msgs go into the ring buffer.
3. Python `poll_forever` pulls them via `GET /poll?since=<cursor>`.
4. `chat_agent.handle` parses `!opus` / `!reset` / `!watch` prefixes,
   then calls `run_agent` with `session_id=jid`. Model = Sonnet (or
   Opus on `!opus`).
5. Claude calls tools, ends with `send_whatsapp` — reply goes out.
6. Conversation history saved to `sessions` table (trimmed to last 40
   turn blocks).

## Security posture

- **Allowlist is enforced in two places:** the Node bridge filters
  inbound at `messages.upsert`, and `chat_agent.handle` re-checks before
  invoking Claude. Defense in depth.
- **The bridge binds to `127.0.0.1` only.** Fastify `host: '127.0.0.1'`.
- **Bearer token** rotates any time: regenerate with `openssl rand -hex 32`
  and put in `.env` (`BRIDGE_TOKEN`). Both processes restart with
  `launchctl kickstart -k`.
- **Secrets**: `.env` + `config/context.md` + `whatsapp_bridge/auth/` are
  gitignored. `.env.example` ships the schema with no values.
- **`send_whatsapp` cannot be redirected.** Tool schema exposes only
  `text`; `to` is always `OWNER_JID`.

## Common tasks

**Edit the strategy (context the ranker uses):**
- Edit `config/context.md`. Changes take effect on the next Claude call
  (caching invalidates automatically when content changes).

**Add/remove a watchlist ticker:**
- Edit `config/watchlist.yml`, or send WhatsApp `!watch ADD NVDA` / `!watch REMOVE NVDA`.

**Tune the buy screener:**
- Edit `config/rules.yml`. Supported metrics & ops are listed in
  `agent/screening/engine.py`. Add a new metric by extending
  `_metric_value` and `indicators.py`.

**Add a new data provider:**
- Implement `agent/data/<name>_adapter.py` subclassing `StockDataAdapter`.
- Register in `agent/data/__init__.py`.
- Set `DATA_ADAPTER=<name>` in `.env`.

**Change schedule time:**
- Edit the `CronTrigger(...)` calls in `agent/scheduler.py`.

**Add Tadawul (.SR) tickers:**
- Append `.SR` symbols (e.g. `2222.SR`) to `config/watchlist.yml`.
- For the screener, add them to `agent/data/sp500.csv` (despite the
  name — it's really "the screening universe"), or create a separate
  universe type in `universe.py`.

## Running / operating

One-shot (useful for testing any time):
```sh
.venv/bin/python -m agent.main --run watchlist
.venv/bin/python -m agent.main --run buy
.venv/bin/python -m agent.main --run refresh
```

Daemon mode (what launchd runs):
```sh
.venv/bin/python -m agent.main
```

Bridge (first-time QR scan, or dev):
```sh
cd whatsapp_bridge && node src/index.js
```

Logs:
```sh
tail -f logs/*.log
```

## Things that have bitten us (add as we find them)

- **yfinance rate limits.** Mitigated by nightly cache + tenacity. If
  you see `429` spikes, widen the jitter in `ohlcv_cache.refresh_universe`.
- **yfinance news schema changed** in 2024/2025; the adapter handles
  both the `content.*` shape and the legacy shape.
- **Baileys session expiry.** Every few weeks WhatsApp logs the device
  out. `send_whatsapp` fails. Check `logs/bridge.err.log`, rerun
  `node whatsapp_bridge/src/index.js` in a terminal to scan a fresh QR,
  then `launchctl kickstart -k gui/$(id -u)/com.user.stockagent.bridge`.
- **Riyadh has no DST**, so APScheduler's DST edge cases don't apply —
  but do not "fix" this by switching the triggers to UTC without
  re-testing.

## Things intentionally NOT done

- No web UI. No dashboard. No multi-user. No PostgreSQL. No Docker.
  Adding any of these without a concrete reason is scope creep.
- No WhatsApp Cloud API integration. Baileys is fine for personal use.
- No streaming/WebSocket inbound — 2s polling is plenty for personal
  traffic and is much simpler to reason about.
- No LLM-based screener. The rules engine is deterministic on purpose;
  Claude only ranks.

## Appendix: model IDs (April 2026)

- Opus 4.7 → `claude-opus-4-7`
- Sonnet 4.6 → `claude-sonnet-4-6`
- Haiku 4.5 → `claude-haiku-4-5-20251001`

When migrating across model versions, update both `.env` defaults and
`agent/claude_client.py` docstring.

-- SQLite schema for the agent.
--
-- Tables:
--   messages       every inbound/outbound WhatsApp message, for audit/history.
--   reports        scheduled run outputs (watchlist / buy / lookup).
--   sessions       per-JID conversation memory for ad-hoc chat.
--   ohlcv_cache    pre-fetched daily bars for the screening universe,
--                  populated by the 03:00 Riyadh nightly job so the 15:50
--                  run doesn't hit yfinance rate limits.

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  jid TEXT NOT NULL,
  direction TEXT NOT NULL CHECK(direction IN ('in','out')),
  text TEXT NOT NULL,
  ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_jid_ts ON messages(jid, ts);

CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  ticker TEXT,
  payload_json TEXT NOT NULL,
  ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_type_ts ON reports(type, ts);

CREATE TABLE IF NOT EXISTS sessions (
  jid TEXT PRIMARY KEY,
  last_context_json TEXT NOT NULL,
  ts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS ohlcv_cache (
  symbol TEXT NOT NULL,
  date TEXT NOT NULL,
  open REAL, high REAL, low REAL, close REAL, adj_close REAL,
  volume REAL,
  PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol ON ohlcv_cache(symbol);

CREATE TABLE IF NOT EXISTS poll_cursor (
  id INTEGER PRIMARY KEY CHECK(id = 1),
  cursor INTEGER NOT NULL
);
INSERT OR IGNORE INTO poll_cursor(id, cursor) VALUES (1, 0);

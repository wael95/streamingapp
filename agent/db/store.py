"""Thin SQLite wrapper.

All DB access goes through this module. We use the stdlib `sqlite3` with a
single connection per process (the Python agent is single-process) and
`check_same_thread=False` because APScheduler fires jobs on worker threads.
`journal_mode=WAL` is set once at init for safer concurrent reads.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable

_LOCK = threading.Lock()
_CONN: sqlite3.Connection | None = None
_DB_PATH: Path | None = None


def init(db_path: Path) -> None:
    global _CONN, _DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _DB_PATH = db_path
    _CONN = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
    _CONN.execute("PRAGMA journal_mode=WAL")
    _CONN.execute("PRAGMA foreign_keys=ON")
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    _CONN.executescript(schema)


def _c() -> sqlite3.Connection:
    if _CONN is None:
        raise RuntimeError("db.store.init() not called")
    return _CONN


def log_message(jid: str, direction: str, text: str) -> None:
    with _LOCK:
        _c().execute(
            "INSERT INTO messages(jid, direction, text, ts) VALUES (?,?,?,?)",
            (jid, direction, text, int(time.time())),
        )


def log_report(kind: str, ticker: str | None, payload: dict[str, Any]) -> None:
    with _LOCK:
        _c().execute(
            "INSERT INTO reports(type, ticker, payload_json, ts) VALUES (?,?,?,?)",
            (kind, ticker, json.dumps(payload, default=str), int(time.time())),
        )


def get_session(jid: str) -> list[dict[str, Any]]:
    row = _c().execute(
        "SELECT last_context_json FROM sessions WHERE jid = ?", (jid,)
    ).fetchone()
    if not row:
        return []
    try:
        return json.loads(row[0])
    except Exception:
        return []


def save_session(jid: str, history: list[dict[str, Any]]) -> None:
    with _LOCK:
        _c().execute(
            "INSERT INTO sessions(jid, last_context_json, ts) VALUES (?,?,?) "
            "ON CONFLICT(jid) DO UPDATE SET last_context_json=excluded.last_context_json, ts=excluded.ts",
            (jid, json.dumps(history, default=str), int(time.time())),
        )


def clear_session(jid: str) -> None:
    with _LOCK:
        _c().execute("DELETE FROM sessions WHERE jid = ?", (jid,))


def get_cursor() -> int:
    row = _c().execute("SELECT cursor FROM poll_cursor WHERE id = 1").fetchone()
    return int(row[0]) if row else 0


def set_cursor(cursor: int) -> None:
    with _LOCK:
        _c().execute("UPDATE poll_cursor SET cursor = ? WHERE id = 1", (cursor,))


def upsert_ohlcv(rows: Iterable[tuple]) -> None:
    with _LOCK:
        _c().executemany(
            "INSERT OR REPLACE INTO ohlcv_cache(symbol, date, open, high, low, close, adj_close, volume) "
            "VALUES (?,?,?,?,?,?,?,?)",
            list(rows),
        )


def read_ohlcv(symbol: str, limit: int = 260) -> list[tuple]:
    return _c().execute(
        "SELECT date, open, high, low, close, adj_close, volume FROM ohlcv_cache "
        "WHERE symbol = ? ORDER BY date DESC LIMIT ?",
        (symbol, limit),
    ).fetchall()


def symbols_with_data() -> list[str]:
    rows = _c().execute("SELECT DISTINCT symbol FROM ohlcv_cache").fetchall()
    return [r[0] for r in rows]

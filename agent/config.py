"""Central configuration loading.

Reads `.env` plus the YAML files under `config/`. Exposes a single `Settings`
object that the rest of the code imports. Keep this module dependency-light
so tests can import it without pulling in network clients.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _require(key: str) -> str:
    v = os.environ.get(key, "").strip()
    if not v:
        raise RuntimeError(f"missing required env var: {key}")
    return v


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class Settings:
    root: Path
    anthropic_api_key: str
    bridge_token: str
    bridge_url: str
    allowed_numbers: tuple[str, ...]
    owner_jid: str
    tz: str
    sonnet_model: str
    opus_model: str
    data_adapter: str
    db_path: Path
    log_dir: Path
    config_dir: Path
    watchlist: dict[str, Any] = field(default_factory=dict)
    rules: dict[str, Any] = field(default_factory=dict)

    @property
    def context_md_path(self) -> Path:
        return self.config_dir / "context.md"

    @property
    def watchlist_tickers(self) -> list[str]:
        return list(self.watchlist.get("tickers") or [])


def load_settings() -> Settings:
    host = _get("BRIDGE_HOST", "127.0.0.1")
    port = _get("BRIDGE_PORT", "8787")
    config_dir = ROOT / _get("CONFIG_DIR", "config")
    return Settings(
        root=ROOT,
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        bridge_token=_require("BRIDGE_TOKEN"),
        bridge_url=f"http://{host}:{port}",
        allowed_numbers=tuple(
            s.strip() for s in _get("ALLOWED_NUMBERS", "").split(",") if s.strip()
        ),
        owner_jid=_require("OWNER_JID"),
        tz=_get("TZ", "Asia/Riyadh"),
        sonnet_model=_get("SONNET_MODEL", "claude-sonnet-4-6"),
        opus_model=_get("OPUS_MODEL", "claude-opus-4-7"),
        data_adapter=_get("DATA_ADAPTER", "yfinance"),
        db_path=ROOT / _get("DB_PATH", "data/stockagent.db"),
        log_dir=ROOT / _get("LOG_DIR", "logs"),
        config_dir=config_dir,
        watchlist=_load_yaml(config_dir / "watchlist.yml"),
        rules=_load_yaml(config_dir / "rules.yml"),
    )

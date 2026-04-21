"""Technicals tool — TradingView-parity indicators computed locally.

Runs on our OHLCV cache (`ohlcv_cache` table) so it's free, offline, and
instant. Uses the `ta` library which implements every mainstream indicator
and works on Python 3.10+.

Exposed metrics in one call (`get_technicals`):
    price, sma_20/50/200, ema_12/26, rsi_14, macd (+hist +signal),
    bb_upper/middle/lower (20, 2σ), atr_14, stoch_k/d, obv, adx_14,
    %-distance to 52w high/low.

Boolean flags:
    golden_cross_recent (50 crossed 200 up within last 20 bars)
    death_cross_recent
    above_sma50, above_sma200
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from agent.config import Settings
from agent.data import get_adapter
from agent.db import store


def _df_from_cache(symbol: str, days: int = 260) -> pd.DataFrame | None:
    rows = store.read_ohlcv(symbol, limit=days)
    if not rows:
        return None
    rows = list(reversed(rows))
    df = pd.DataFrame(
        rows, columns=["date", "open", "high", "low", "close", "adj_close", "volume"]
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").astype(float)
    return df


def _ensure_cache(settings: Settings, symbol: str, days: int) -> pd.DataFrame | None:
    df = _df_from_cache(symbol, days)
    if df is not None and len(df) > 30:
        return df
    try:
        adapter = get_adapter(settings.data_adapter)
        bars = adapter.ohlcv(symbol, days=days)
        if not bars:
            return None
        store.upsert_ohlcv(
            [
                (symbol, b.date, b.open, b.high, b.low, b.close, b.adj_close, b.volume)
                for b in bars
            ]
        )
        return _df_from_cache(symbol, days)
    except Exception:
        return None


def _round(v: Any, n: int = 4) -> Any:
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, n)
    except (TypeError, ValueError):
        return None


def _last(series) -> Any:
    try:
        v = series.iloc[-1]
        if pd.isna(v):
            return None
        return float(v)
    except Exception:
        return None


def get_technicals(settings: Settings, ticker: str) -> dict:
    df = _ensure_cache(settings, ticker.upper(), days=260)
    if df is None or df.empty:
        return {"symbol": ticker.upper(), "error": "no data"}

    # Lazy imports — `ta` is a heavy tree.
    from ta.trend import SMAIndicator, EMAIndicator, MACD, ADXIndicator
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.volatility import BollingerBands, AverageTrueRange
    from ta.volume import OnBalanceVolumeIndicator

    close = df["close"]
    high = df["high"]
    low = df["low"]
    vol = df["volume"]

    sma20 = SMAIndicator(close, window=20).sma_indicator()
    sma50 = SMAIndicator(close, window=50).sma_indicator()
    sma200 = SMAIndicator(close, window=200).sma_indicator()
    ema12 = EMAIndicator(close, window=12).ema_indicator()
    ema26 = EMAIndicator(close, window=26).ema_indicator()
    rsi14 = RSIIndicator(close, window=14).rsi()
    macd = MACD(close)
    bb = BollingerBands(close, window=20, window_dev=2)
    atr14 = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    stoch = StochasticOscillator(high=high, low=low, close=close)
    obv = OnBalanceVolumeIndicator(close=close, volume=vol).on_balance_volume()
    adx = ADXIndicator(high=high, low=low, close=close, window=14).adx()

    last_close = _last(close) or 0.0
    hi_52w = float(close.tail(252).max())
    lo_52w = float(close.tail(252).min())

    def cross_recent(short: pd.Series, long: pd.Series, up: bool) -> bool:
        d = (short - long).dropna().tail(22)
        if len(d) < 2:
            return False
        diffs = d.to_numpy()
        if up:
            cond = (diffs[:-1] <= 0) & (diffs[1:] > 0)
        else:
            cond = (diffs[:-1] >= 0) & (diffs[1:] < 0)
        return bool(cond.any())

    s50 = _last(sma50)
    s200 = _last(sma200)

    # Cleanliness check: largest single-day rise in the last 10 trading days.
    # Used as a hard filter to skip stocks that already exploded recently.
    last10 = close.tail(11)  # need 11 closes to get 10 daily changes
    max_1d_last10 = None
    if len(last10) >= 2:
        ch = last10.pct_change().dropna() * 100
        max_1d_last10 = float(ch.max()) if not ch.empty else None

    # Spike-then-drop pattern detection over the last 60 trading days.
    # Looking for: a peak somewhere in the window, the peak was >= 5 bars
    # ago, and current price is at least 30% below that peak.
    win = close.tail(60)
    pct_below_60d_peak = None
    bars_since_60d_peak = None
    spike_then_drop = False
    if len(win) >= 10:
        peak = float(win.max())
        peak_idx = int(win.values.argmax())
        bars_since_60d_peak = len(win) - 1 - peak_idx
        if peak > 0 and last_close > 0:
            pct_below_60d_peak = round((last_close / peak - 1) * 100, 2)
            spike_then_drop = bool(
                pct_below_60d_peak <= -30 and bars_since_60d_peak >= 5
            )

    return {
        "symbol": ticker.upper(),
        "price": _round(last_close, 2),
        "sma_20": _round(_last(sma20)),
        "sma_50": _round(s50),
        "sma_200": _round(s200),
        "ema_12": _round(_last(ema12)),
        "ema_26": _round(_last(ema26)),
        "rsi_14": _round(_last(rsi14), 2),
        "macd": _round(_last(macd.macd())),
        "macd_hist": _round(_last(macd.macd_diff())),
        "macd_signal": _round(_last(macd.macd_signal())),
        "bb_upper": _round(_last(bb.bollinger_hband())),
        "bb_middle": _round(_last(bb.bollinger_mavg())),
        "bb_lower": _round(_last(bb.bollinger_lband())),
        "atr_14": _round(_last(atr14)),
        "stoch_k": _round(_last(stoch.stoch())),
        "stoch_d": _round(_last(stoch.stoch_signal())),
        "obv": _round(_last(obv), 0),
        "adx_14": _round(_last(adx)),
        "hi_52w": _round(hi_52w, 2),
        "lo_52w": _round(lo_52w, 2),
        "pct_below_52w_high": _round((last_close / hi_52w - 1) * 100, 2) if hi_52w else None,
        "pct_above_52w_low": _round((last_close / lo_52w - 1) * 100, 2) if lo_52w else None,
        "above_sma50": bool(s50 is not None and last_close > s50),
        "above_sma200": bool(s200 is not None and last_close > s200),
        "golden_cross_recent": cross_recent(sma50, sma200, up=True),
        "death_cross_recent": cross_recent(sma50, sma200, up=False),
        "max_1d_change_last_10d": _round(max_1d_last10, 2),
        "pct_below_60d_peak": pct_below_60d_peak,
        "bars_since_60d_peak": bars_since_60d_peak,
        "spike_then_drop": spike_then_drop,
    }

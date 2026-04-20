"""Technical indicators used by the screener.

Kept dependency-free (numpy only) and vectorised so a 500-name screen is
cheap. All functions accept a numpy array of close prices, oldest first,
and return either a scalar (latest value) or a bool.
"""
from __future__ import annotations

import numpy as np


def sma(closes: np.ndarray, n: int) -> float | None:
    if closes.size < n:
        return None
    return float(np.mean(closes[-n:]))


def rsi(closes: np.ndarray, n: int = 14) -> float | None:
    if closes.size < n + 1:
        return None
    diffs = np.diff(closes)
    gains = np.clip(diffs, 0, None)
    losses = -np.clip(diffs, None, 0)
    avg_gain = np.mean(gains[-n:])
    avg_loss = np.mean(losses[-n:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def golden_cross(closes: np.ndarray, short: int = 50, long: int = 200, lookback: int = 20) -> bool:
    """True if SMA(short) crossed above SMA(long) within the last `lookback` bars."""
    if closes.size < long + lookback:
        return False
    # Compute rolling means for the tail window.
    window = long + lookback
    tail = closes[-window:]
    def rolling(a, n):
        if a.size < n:
            return np.array([])
        cs = np.cumsum(np.insert(a, 0, 0.0))
        return (cs[n:] - cs[:-n]) / n
    s = rolling(tail, short)
    l = rolling(tail, long)
    m = min(s.size, l.size)
    if m < 2:
        return False
    s, l = s[-m:], l[-m:]
    diff = s - l
    # crossed up: prior <=0, current >0, anywhere in tail
    crossed = (diff[:-1] <= 0) & (diff[1:] > 0)
    return bool(crossed[-lookback:].any()) if crossed.size else False


def change_pct(closes: np.ndarray, n: int) -> float | None:
    if closes.size < n + 1:
        return None
    return float((closes[-1] / closes[-1 - n] - 1) * 100.0)


def avg_volume(volumes: np.ndarray, n: int = 30) -> float | None:
    if volumes.size < n:
        return None
    return float(np.mean(volumes[-n:]))

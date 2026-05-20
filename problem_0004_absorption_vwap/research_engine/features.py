from __future__ import annotations

from bisect import bisect_right, insort

from typing import Any, Dict

import numpy as np
import pandas as pd

from .schemas import feature_config
from .signal_logic import block_reason, classify_vwap_location
from .vwap import add_session_vwap


def add_atr(df: pd.DataFrame, length: int) -> pd.DataFrame:
    out = df.copy()
    pieces = []
    for _, group in out.groupby("symbol", sort=False):
        g = group.copy()
        prev_close = g["close"].shift(1)
        tr = pd.concat([
            g["high"] - g["low"],
            (g["high"] - prev_close).abs(),
            (g["low"] - prev_close).abs(),
        ], axis=1).max(axis=1)
        g["true_range"] = tr
        g["atr"] = tr.rolling(length, min_periods=length).mean()
        pieces.append(g)
    return pd.concat(pieces).sort_index()


def rolling_percentile_rank(series: pd.Series, lookback: int, min_periods: int | None = None) -> pd.Series:
    min_periods = min_periods or lookback
    values = series.to_numpy(dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    window: list[float] = []
    queue: list[float] = []
    for i, current in enumerate(values):
        queue.append(current)
        if not np.isnan(current):
            insort(window, float(current))
        if len(queue) > lookback:
            old = queue.pop(0)
            if not np.isnan(old):
                remove_at = bisect_right(window, float(old)) - 1
                if remove_at >= 0:
                    window.pop(remove_at)
        if len(window) >= min_periods and not np.isnan(current):
            result[i] = 100.0 * bisect_right(window, float(current)) / len(window)
    return pd.Series(result, index=series.index)


def compute_absorption_features(df: pd.DataFrame, cfg: Dict[str, Any] | None = None) -> pd.DataFrame:
    cfg = cfg or {}
    fcfg = feature_config(cfg)
    out = add_session_vwap(df, cfg)
    out = add_atr(out, int(fcfg.get("atr_length", 60)))

    lookback = int(fcfg.get("volume_lookback", 100))
    min_periods = int(fcfg.get("volume_percentile_min_periods", lookback))
    pieces = []
    for _, group in out.groupby("symbol", sort=False):
        g = group.copy()
        g["volume_percentile"] = rolling_percentile_rank(g["volume"].astype(float), lookback, min_periods=min_periods)
        pieces.append(g)
    out = pd.concat(pieces).sort_index()

    out["body_displacement"] = (out["close"] - out["open"]).abs()
    out["bar_range"] = out["high"] - out["low"]
    out["displacement_atr"] = out["body_displacement"] / out["atr"].replace(0, np.nan)
    out["vwap_distance"] = out["close"] - out["session_vwap"]
    out["vwap_distance_atr"] = out["vwap_distance"] / out["atr"].replace(0, np.nan)

    near = float(fcfg.get("near_vwap_threshold_atr", 0.25))
    min_dist = float(fcfg.get("min_vwap_distance_atr", 0.0))
    out["location_vs_vwap"] = [
        classify_vwap_location(c, v, a, near, min_dist)
        for c, v, a in zip(out["close"], out["session_vwap"], out["atr"])
    ]

    threshold = float(fcfg.get("high_volume_percentile_threshold", 95))
    max_disp = float(fcfg.get("max_displacement_atr", 0.3))
    out["high_volume_pass"] = out["volume_percentile"] >= threshold
    out["low_displacement_pass"] = out["displacement_atr"] <= max_disp
    out["is_absorption_bar"] = out["high_volume_pass"] & out["low_displacement_pass"] & out["atr"].notna() & out["session_vwap"].notna()
    out["absorption_side"] = np.where(out["is_absorption_bar"], out["location_vs_vwap"], "unknown")
    out["block_reason"] = out.apply(block_reason, axis=1)
    return out


def feature_columns() -> list[str]:
    return [
        "timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe", "session_date",
        "atr", "body_displacement", "displacement_atr", "volume_percentile", "session_vwap",
        "vwap_distance", "vwap_distance_atr", "location_vs_vwap", "is_absorption_bar", "absorption_side", "block_reason",
    ]

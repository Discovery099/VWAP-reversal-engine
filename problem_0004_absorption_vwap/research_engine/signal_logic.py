from __future__ import annotations

import numpy as np
import pandas as pd


def classify_vwap_location(close, session_vwap, atr, near_threshold_atr: float = 0.25, min_distance_atr: float = 0.0) -> str:
    if pd.isna(session_vwap) or pd.isna(atr) or atr <= 0:
        return "unknown"
    distance_atr = (close - session_vwap) / atr
    if abs(distance_atr) <= near_threshold_atr:
        return "near_vwap"
    if distance_atr > min_distance_atr:
        return "above_vwap"
    if distance_atr < -min_distance_atr:
        return "below_vwap"
    return "unknown"


def expected_direction_for_side(side: str) -> str:
    if side == "above_vwap":
        return "down"
    if side == "below_vwap":
        return "up"
    if side == "near_vwap":
        return "neutral"
    return "unknown"


def block_reason(row) -> str:
    reasons = []
    if pd.isna(row.get("session_vwap")):
        reasons.append("VWAP_UNAVAILABLE")
    if pd.isna(row.get("atr")) or row.get("atr", 0) <= 0:
        reasons.append("ATR_UNAVAILABLE")
    if pd.isna(row.get("volume_percentile")):
        reasons.append("VOLUME_LOOKBACK_UNAVAILABLE")
    if row.get("volume", 1) == 0:
        reasons.append("ZERO_VOLUME")
    if reasons:
        return "|".join(reasons)
    if bool(row.get("is_absorption_bar", False)):
        return "PASS"
    fails = []
    if not bool(row.get("high_volume_pass", False)):
        fails.append("HIGH_VOLUME_FAIL")
    if not bool(row.get("low_displacement_pass", False)):
        fails.append("DISPLACEMENT_FAIL")
    return "|".join(fails) if fails else "NOT_ABSORPTION"


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(length, min_periods=length).mean()
    loss = (-delta.clip(upper=0)).rolling(length, min_periods=length).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

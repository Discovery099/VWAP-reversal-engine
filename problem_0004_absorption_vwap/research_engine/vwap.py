from __future__ import annotations

import warnings
from typing import Any, Dict

import numpy as np
import pandas as pd


def add_session_vwap(df: pd.DataFrame, cfg: Dict[str, Any] | None = None) -> pd.DataFrame:
    cfg = cfg or {}
    out = df.copy()
    if "session_date" not in out.columns:
        out["session_date"] = out["timestamp"].dt.date.astype(str)

    if "vwap" in out.columns and out["vwap"].notna().any():
        out["session_vwap"] = pd.to_numeric(out["vwap"], errors="coerce")
        return out

    zero_policy = cfg.get("zero_volume_policy", "carry_forward")
    out["typical_price"] = (out["high"] + out["low"] + out["close"]) / 3.0
    pieces = []
    for _, group in out.groupby(["symbol", "session_date"], sort=False):
        g = group.copy()
        if (g["volume"] == 0).any():
            warnings.warn(f"Zero-volume bars in {g['symbol'].iloc[0]} {g['session_date'].iloc[0]}", RuntimeWarning)
        vol = g["volume"].astype(float).clip(lower=0)
        pv = g["typical_price"] * vol
        cum_vol = vol.cumsum()
        cum_pv = pv.cumsum()
        with np.errstate(divide="ignore", invalid="ignore"):
            vwap = cum_pv / cum_vol.replace(0, np.nan)
        if zero_policy == "carry_forward":
            vwap = vwap.ffill()
        elif zero_policy == "nan":
            pass
        else:
            raise ValueError(f"Unsupported zero_volume_policy: {zero_policy}")
        g["cum_volume"] = cum_vol
        g["cum_pv"] = cum_pv
        g["session_vwap"] = vwap
        pieces.append(g)
    return pd.concat(pieces).sort_index()

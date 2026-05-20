from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .schemas import feature_config
from .signal_logic import expected_direction_for_side


def _round_trip_cost_price(cfg: Dict[str, Any]) -> float:
    costs = cfg.get("costs", {}) if cfg else {}
    point_value = float(costs.get("point_value", 1.0) or 1.0)
    commission_price = float(costs.get("commission_per_trade", 0.0) or 0.0) / point_value
    spread = float(costs.get("spread", 0.0) or 0.0)
    slippage = float(costs.get("slippage_ticks", 0.0) or 0.0) * float(costs.get("tick_size", 0.0) or 0.0) * 2.0
    return commission_price + spread + slippage


def label_absorption_events(feature_df: pd.DataFrame, cfg: Dict[str, Any] | None = None) -> pd.DataFrame:
    cfg = cfg or {}
    fcfg = feature_config(cfg)
    horizon = int(fcfg.get("reversal_horizon_bars", 15))
    cost_threshold = _round_trip_cost_price(cfg)
    df = feature_df.sort_values(["symbol", "timestamp"]).reset_index(drop=True).copy()
    df["bar_id"] = np.arange(len(df))
    events: List[Dict[str, Any]] = []

    for _, event in df[df["is_absorption_bar"]].iterrows():
        side = str(event.get("absorption_side", "unknown"))
        direction = expected_direction_for_side(side)
        same = df[(df["symbol"] == event["symbol"]) & (df["session_date"] == event["session_date"]) & (df["bar_id"] > event["bar_id"])]
        future = same.head(horizon)
        row = {
            "event_bar_id": int(event["bar_id"]),
            "timestamp": event["timestamp"],
            "symbol": event["symbol"],
            "timeframe": event.get("timeframe", ""),
            "session_date": event.get("session_date", ""),
            "event_close": float(event["close"]),
            "event_vwap": float(event["session_vwap"]) if pd.notna(event["session_vwap"]) else np.nan,
            "absorption_side": side,
            "location_vs_vwap": event.get("location_vs_vwap", "unknown"),
            "expected_direction": direction,
            "volume_percentile": event.get("volume_percentile", np.nan),
            "displacement_atr": event.get("displacement_atr", np.nan),
            "label_status": "OK" if len(future) else "NO_FUTURE_BARS",
        }
        if not len(future) or direction not in {"up", "down"}:
            row.update({
                "reversed_toward_vwap": None if direction != "neutral" else False,
                "return_next_horizon": np.nan,
                "bars_to_vwap_touch": np.nan,
                "max_adverse_excursion": np.nan,
                "max_favorable_excursion": np.nan,
            })
            events.append(row)
            continue

        final_close = float(future["close"].iloc[-1])
        raw_return = (final_close - float(event["close"])) / float(event["close"])
        vwap = float(event["session_vwap"])
        close0 = float(event["close"])
        if direction == "down":
            touch_mask = future["low"] <= vwap
            direction_move = final_close <= close0 - cost_threshold
            mfe = close0 - float(future["low"].min())
            mae = float(future["high"].max()) - close0
        else:
            touch_mask = future["high"] >= vwap
            direction_move = final_close >= close0 + cost_threshold
            mfe = float(future["high"].max()) - close0
            mae = close0 - float(future["low"].min())
        touch = bool(touch_mask.any())
        bars_to_touch = int(np.argmax(touch_mask.to_numpy()) + 1) if touch else np.nan
        row.update({
            "reversed_toward_vwap": bool(touch or direction_move),
            "return_next_horizon": raw_return,
            "bars_to_vwap_touch": bars_to_touch,
            "max_adverse_excursion": mae,
            "max_favorable_excursion": mfe,
        })
        events.append(row)
    return pd.DataFrame(events)

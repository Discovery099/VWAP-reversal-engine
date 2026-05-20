from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd


def round_trip_cost_price(cfg: Dict[str, Any]) -> float:
    costs = cfg.get("costs", {}) if cfg else {}
    point_value = float(costs.get("point_value", 1.0) or 1.0)
    commission_price = float(costs.get("commission_per_trade", 0.0) or 0.0) / point_value
    spread = float(costs.get("spread", 0.0) or 0.0)
    slippage = float(costs.get("slippage_ticks", 0.0) or 0.0) * float(costs.get("tick_size", 0.0) or 0.0) * 2.0
    return commission_price + spread + slippage


def _direction_from_row(row) -> str | None:
    loc = row.get("location_vs_vwap", row.get("absorption_side", "unknown"))
    if loc == "above_vwap":
        return "short"
    if loc == "below_vwap":
        return "long"
    return None


def build_trades(
    feature_df: pd.DataFrame,
    cfg: Dict[str, Any],
    signal_mask,
    signal_name: str,
    direction_series=None,
    random_direction: bool = False,
) -> pd.DataFrame:
    horizon = int(cfg.get("features", {}).get("reversal_horizon_bars", cfg.get("backtest", {}).get("time_stop_bars", 15)))
    include_near = bool(cfg.get("backtest", {}).get("include_near_vwap", False))
    point_value = float(cfg.get("costs", {}).get("point_value", 1.0) or 1.0)
    cost_price = round_trip_cost_price(cfg)
    rng = np.random.default_rng(int(cfg.get("validation", {}).get("random_seed", 7)))

    df = feature_df.sort_values(["symbol", "timestamp"]).reset_index(drop=True).copy()
    df["bar_id"] = np.arange(len(df))
    mask = pd.Series(signal_mask, index=feature_df.index).fillna(False).to_numpy()
    if len(mask) != len(df):
        mask = pd.Series(signal_mask).fillna(False).to_numpy()
    signal_positions = np.where(mask)[0]

    group_end = np.zeros(len(df), dtype=int)
    for _, idx in df.groupby(["symbol", "session_date"], sort=False).indices.items():
        positions = np.asarray(idx, dtype=int)
        group_end[positions] = int(positions.max()) + 1

    trades = []
    for original_idx in signal_positions:
        row = df.iloc[original_idx]
        if direction_series is not None:
            direction = direction_series.iloc[original_idx] if hasattr(direction_series, "iloc") else direction_series[original_idx]
        elif random_direction:
            direction = "long" if rng.random() >= 0.5 else "short"
        else:
            direction = _direction_from_row(row)
        if direction not in {"long", "short"}:
            if row.get("location_vs_vwap") == "near_vwap" and include_near:
                direction = "short" if row["close"] > row["session_vwap"] else "long"
            else:
                continue
        end_pos = int(group_end[original_idx])
        start_pos = int(original_idx) + 1
        if start_pos >= end_pos:
            continue
        future = df.iloc[start_pos:min(end_pos, start_pos + horizon)]
        if future.empty:
            continue
        entry_bar = future.iloc[0]
        entry = float(entry_bar["open"])
        vwap = float(row["session_vwap"])
        exit_price = float(future["close"].iloc[-1])
        exit_reason = "TIME_STOP"
        if direction == "long":
            touch = future[future["high"] >= vwap]
            if len(touch):
                exit_price = vwap
                exit_reason = "VWAP_TARGET"
            gross_points = exit_price - entry
        else:
            touch = future[future["low"] <= vwap]
            if len(touch):
                exit_price = vwap
                exit_reason = "VWAP_TARGET"
            gross_points = entry - exit_price
        net_points = gross_points - cost_price
        trades.append({
            "signal_name": signal_name,
            "timestamp": row["timestamp"],
            "symbol": row["symbol"],
            "session_date": row["session_date"],
            "direction": direction,
            "entry_timestamp": entry_bar["timestamp"],
            "entry_price": entry,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "horizon_bars": int(len(future)),
            "gross_pnl_points": gross_points,
            "cost_points": cost_price,
            "net_pnl_points": net_points,
            "net_pnl_value": net_points * point_value,
            "win": net_points > 0,
            "location_vs_vwap": row.get("location_vs_vwap", "unknown"),
            "volume_percentile": row.get("volume_percentile", np.nan),
            "displacement_atr": row.get("displacement_atr", np.nan),
        })
    return pd.DataFrame(trades)


def summarize_trades(trades: pd.DataFrame) -> Dict[str, Any]:
    if trades is None or trades.empty:
        return {
            "trade_count": 0,
            "hit_rate": 0.0,
            "expectancy_after_cost": 0.0,
            "total_net_pnl": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
        }
    pnl = trades["net_pnl_value"].astype(float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    if gross_loss < 0:
        pf = gross_profit / abs(gross_loss)
    elif gross_profit > 0:
        pf = float("inf")
    else:
        pf = 0.0
    equity = pnl.cumsum()
    peak = equity.cummax()
    dd = equity - peak
    return {
        "trade_count": int(len(trades)),
        "hit_rate": float((pnl > 0).mean()),
        "expectancy_after_cost": float(pnl.mean()),
        "total_net_pnl": float(pnl.sum()),
        "profit_factor": pf,
        "max_drawdown": float(dd.min()),
    }

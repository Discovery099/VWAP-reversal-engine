from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd

from .backtest import round_trip_cost_price
from .features import compute_absorption_features
from .schemas import deep_merge, load_yaml


def _param_product(grid: Dict[str, Iterable[Any]], max_combinations: int | None = None):
    keys = list(grid.keys())
    for i, values in enumerate(product(*[grid[k] for k in keys])):
        if max_combinations is not None and i >= max_combinations:
            break
        yield dict(zip(keys, values))


def _cfg_with_params(base_cfg: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    override = {"features": params}
    return deep_merge(base_cfg, override)


def _location_for_threshold(vwap_distance_atr: pd.Series, near_threshold: float) -> pd.Series:
    loc = pd.Series("unknown", index=vwap_distance_atr.index, dtype=object)
    loc[vwap_distance_atr.abs() <= near_threshold] = "near_vwap"
    loc[vwap_distance_atr > near_threshold] = "above_vwap"
    loc[vwap_distance_atr < -near_threshold] = "below_vwap"
    loc[vwap_distance_atr.isna()] = "unknown"
    return loc


def _group_end_positions(df: pd.DataFrame) -> np.ndarray:
    group_end = np.zeros(len(df), dtype=int)
    for _, idx in df.groupby(["symbol", "session_date"], sort=False).indices.items():
        positions = np.asarray(idx, dtype=int)
        group_end[positions] = int(positions.max()) + 1
    return group_end


def _fast_absorption_metrics(features: pd.DataFrame, cfg: Dict[str, Any], signal_mask: pd.Series) -> Dict[str, Any]:
    if signal_mask.sum() == 0:
        return {
            "trade_count": 0,
            "hit_rate": 0.0,
            "expectancy_after_cost": 0.0,
            "total_net_pnl": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
        }

    horizon = int(cfg.get("features", {}).get("reversal_horizon_bars", 15))
    point_value = float(cfg.get("costs", {}).get("point_value", 1.0) or 1.0)
    cost_price = round_trip_cost_price(cfg)
    df = features.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    mask = signal_mask.reindex(features.index).fillna(False).to_numpy()
    if len(mask) != len(df):
        mask = pd.Series(signal_mask).fillna(False).to_numpy()

    open_arr = df["open"].to_numpy(float)
    high_arr = df["high"].to_numpy(float)
    low_arr = df["low"].to_numpy(float)
    close_arr = df["close"].to_numpy(float)
    vwap_arr = df["session_vwap"].to_numpy(float)
    loc_arr = df["location_vs_vwap"].astype(str).to_numpy()
    group_end = _group_end_positions(df)

    pnl_values: List[float] = []
    for pos in np.flatnonzero(mask):
        loc = loc_arr[pos]
        if loc not in {"above_vwap", "below_vwap"}:
            continue
        start = int(pos) + 1
        end = min(int(group_end[pos]), start + horizon)
        if start >= end or np.isnan(vwap_arr[pos]):
            continue
        entry = open_arr[start]
        vwap = vwap_arr[pos]
        if loc == "below_vwap":
            touches = np.flatnonzero(high_arr[start:end] >= vwap)
            exit_price = vwap if len(touches) else close_arr[end - 1]
            gross_points = exit_price - entry
        else:
            touches = np.flatnonzero(low_arr[start:end] <= vwap)
            exit_price = vwap if len(touches) else close_arr[end - 1]
            gross_points = entry - exit_price
        pnl_values.append((gross_points - cost_price) * point_value)

    if not pnl_values:
        return {
            "trade_count": 0,
            "hit_rate": 0.0,
            "expectancy_after_cost": 0.0,
            "total_net_pnl": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
        }
    pnl = pd.Series(pnl_values, dtype=float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    if gross_loss < 0:
        profit_factor = gross_profit / abs(gross_loss)
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0
    equity = pnl.cumsum()
    drawdown = equity - equity.cummax()
    return {
        "trade_count": int(len(pnl)),
        "hit_rate": float((pnl > 0).mean()),
        "expectancy_after_cost": float(pnl.mean()),
        "total_net_pnl": float(pnl.sum()),
        "profit_factor": profit_factor,
        "max_drawdown": float(drawdown.min()),
    }


def select_plateau_centroid(results: pd.DataFrame, grid: Dict[str, List[Any]], min_neighbors: int = 5) -> Dict[str, Any]:
    if results.empty or "passes_hard_filters" not in results.columns:
        return {"status": "NO_STABLE_PLATEAU", "reason": "No grid results or missing filter column."}
    passing = results[results["passes_hard_filters"].astype(bool)].copy()
    if passing.empty:
        return {"status": "NO_STABLE_PLATEAU", "reason": "No configurations passed hard filters."}

    index_maps = {k: {v: i for i, v in enumerate(vals)} for k, vals in grid.items()}
    coords = []
    for _, row in passing.iterrows():
        coords.append(tuple(index_maps[k][row[k]] for k in grid.keys()))
    neighbor_counts = []
    for c in coords:
        count = 0
        for other in coords:
            if c == other:
                continue
            if sum(abs(a - b) for a, b in zip(c, other)) == 1:
                count += 1
        neighbor_counts.append(count)
    passing["neighbor_count"] = neighbor_counts
    stable = passing[passing["neighbor_count"] >= min_neighbors]
    if stable.empty:
        best = passing.sort_values("expectancy_after_cost", ascending=False).head(1).to_dict("records")[0]
        return {"status": "NO_STABLE_PLATEAU", "reason": "Passing configurations are isolated spikes.", "best_isolated": best}

    centroid = {}
    for key, vals in grid.items():
        mean_value = stable[key].astype(float).mean()
        centroid[key] = min(vals, key=lambda v: abs(float(v) - mean_value))
    return {
        "status": "STABLE_PLATEAU_FOUND",
        "centroid": centroid,
        "stable_count": int(len(stable)),
        "max_neighbor_count": int(stable["neighbor_count"].max()),
    }


def run_plateau(df: pd.DataFrame, base_cfg: Dict[str, Any], grid_cfg: Dict[str, Any]) -> Dict[str, Any]:
    grid = {k: list(v) for k, v in grid_cfg.get("grid", grid_cfg).items()}
    max_combinations = grid_cfg.get("max_combinations")
    min_neighbors = int(grid_cfg.get("min_neighbors_for_plateau", 5))
    min_events = int(base_cfg.get("validation", {}).get("min_events_for_full_validation", 100))
    rows: List[Dict[str, Any]] = []

    # Cache expensive ATR/VWAP/volume percentile calculations by the parameters that
    # actually affect those columns. VWAP location and threshold logic are re-evaluated
    # cheaply for every grid row without changing strategy rules.
    feature_cache: Dict[tuple, pd.DataFrame] = {}
    for params in _param_product(grid, max_combinations):
        cache_key = (params.get("volume_lookback"), params.get("atr_length"))
        if cache_key not in feature_cache:
            cfg_for_features = _cfg_with_params(base_cfg, params)
            feature_cache[cache_key] = compute_absorption_features(df, cfg_for_features)
        features = feature_cache[cache_key].copy()
        near_threshold = float(params["near_vwap_threshold_atr"])
        features["location_vs_vwap"] = _location_for_threshold(features["vwap_distance_atr"], near_threshold)
        features["high_volume_pass"] = features["volume_percentile"] >= float(params["high_volume_percentile_threshold"])
        features["low_displacement_pass"] = features["displacement_atr"] <= float(params["max_displacement_atr"])
        signal_mask = (
            features["high_volume_pass"]
            & features["low_displacement_pass"]
            & features["location_vs_vwap"].isin(["above_vwap", "below_vwap"])
        )
        cfg = _cfg_with_params(base_cfg, params)
        metrics = _fast_absorption_metrics(features, cfg, signal_mask)
        row = dict(params)
        row.update({
            "trade_count": metrics["trade_count"],
            "hit_rate": metrics["hit_rate"],
            "expectancy_after_cost": metrics["expectancy_after_cost"],
            "profit_factor": metrics["profit_factor"],
            "max_drawdown": metrics["max_drawdown"],
            "validation_status": "CANDIDATE" if metrics["trade_count"] else "NO_EVENTS",
        })
        row["passes_hard_filters"] = bool(
            row["trade_count"] >= min_events
            and row["expectancy_after_cost"] > 0
            and row["profit_factor"] > 1.0
        )
        rows.append(row)
    results = pd.DataFrame(rows)
    plateau = select_plateau_centroid(results, grid, min_neighbors=min_neighbors)
    return {"grid_results": results, "plateau": plateau}


def load_grid(path: str | Path) -> Dict[str, Any]:
    return load_yaml(path)

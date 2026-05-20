from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd

from .backtest import build_trades, summarize_trades
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

    # Cache expensive ATR/VWAP/volume percentile calculations. Threshold-only parameters
    # are then evaluated cheaply without repeatedly recomputing rolling features.
    feature_cache: Dict[tuple, pd.DataFrame] = {}
    for params in _param_product(grid, max_combinations):
        cache_key = (params.get("volume_lookback"), params.get("atr_length"), params.get("near_vwap_threshold_atr"))
        if cache_key not in feature_cache:
            cfg_for_features = _cfg_with_params(base_cfg, params)
            feature_cache[cache_key] = compute_absorption_features(df, cfg_for_features)
        features = feature_cache[cache_key].copy()
        features["high_volume_pass"] = features["volume_percentile"] >= float(params["high_volume_percentile_threshold"])
        features["low_displacement_pass"] = features["displacement_atr"] <= float(params["max_displacement_atr"])
        features["is_absorption_bar"] = (
            features["high_volume_pass"]
            & features["low_displacement_pass"]
            & features["location_vs_vwap"].isin(["above_vwap", "below_vwap"])
        )
        features["absorption_side"] = np.where(features["is_absorption_bar"], features["location_vs_vwap"], "unknown")
        cfg = _cfg_with_params(base_cfg, params)
        trades = build_trades(features, cfg, features["is_absorption_bar"], "absorption_vwap")
        metrics = summarize_trades(trades)
        row = dict(params)
        row.update({
            "trade_count": metrics["trade_count"],
            "hit_rate": metrics["hit_rate"],
            "expectancy_after_cost": metrics["expectancy_after_cost"],
            "profit_factor": metrics["profit_factor"],
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

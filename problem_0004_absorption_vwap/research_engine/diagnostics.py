from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .backtest import round_trip_cost_price
from .features import compute_absorption_features
from .plateau import _location_for_threshold, load_grid
from .reports import _json_safe, make_run_dir
from .schemas import deep_merge


SESSION_BUCKETS = ["first_30m", "morning", "midday", "afternoon", "last_30m"]
PARAM_KEYS = [
    "volume_lookback",
    "high_volume_percentile_threshold",
    "atr_length",
    "max_displacement_atr",
    "near_vwap_threshold_atr",
    "reversal_horizon_bars",
]


def _copy_with_horizon(cfg: Dict[str, Any], horizon: int) -> Dict[str, Any]:
    out = deepcopy(cfg)
    out.setdefault("features", {})["reversal_horizon_bars"] = int(horizon)
    out.setdefault("backtest", {})["time_stop_bars"] = int(horizon)
    return out


def _group_end_positions(df: pd.DataFrame) -> np.ndarray:
    group_end = np.zeros(len(df), dtype=int)
    for _, idx in df.groupby(["symbol", "session_date"], sort=False).indices.items():
        positions = np.asarray(idx, dtype=int)
        group_end[positions] = int(positions.max()) + 1
    return group_end


def _time_to_minutes(value: str | None, fallback: int) -> int:
    if not value:
        return fallback
    hour, minute = str(value).split(":")[:2]
    return int(hour) * 60 + int(minute)


def _session_bucket(ts: pd.Timestamp, cfg: Dict[str, Any] | None = None) -> str:
    minutes = ts.hour * 60 + ts.minute
    session_cfg = (cfg or {}).get("session", {})
    start = _time_to_minutes(session_cfg.get("rth_start"), 9 * 60 + 30)
    end = _time_to_minutes(session_cfg.get("rth_end"), 16 * 60)
    if minutes < start + 30:
        return "first_30m"
    if minutes >= end - 30:
        return "last_30m"
    span = max(end - start - 60, 1)
    elapsed = max(minutes - (start + 30), 0)
    if elapsed < span / 3:
        return "morning"
    if elapsed < 2 * span / 3:
        return "midday"
    return "afternoon"


def _add_diagnostic_buckets(features: pd.DataFrame, cfg: Dict[str, Any] | None = None) -> pd.DataFrame:
    out = features.copy()
    out["session_bucket"] = out["timestamp"].apply(lambda ts: _session_bucket(ts, cfg))
    out["volume_percentile_band"] = pd.cut(
        out["volume_percentile"],
        bins=[0, 95, 97.5, 99, 100.000001],
        labels=["<=95", "95-97.5", "97.5-99", "99-100"],
        include_lowest=True,
    ).astype(str)
    out["displacement_atr_band"] = pd.cut(
        out["displacement_atr"],
        bins=[-0.000001, 0.1, 0.2, 0.3, 0.5, np.inf],
        labels=["0-0.10", "0.10-0.20", "0.20-0.30", "0.30-0.50", ">0.50"],
        include_lowest=True,
    ).astype(str)
    out["abs_vwap_distance_atr"] = out["vwap_distance_atr"].abs()
    out["vwap_distance_atr_band"] = pd.cut(
        out["abs_vwap_distance_atr"],
        bins=[-0.000001, 0.25, 0.5, 1.0, 2.0, np.inf],
        labels=["0-0.25", "0.25-0.50", "0.50-1.00", "1.00-2.00", ">2.00"],
        include_lowest=True,
    ).astype(str)
    return out


def _direction_for_location(location: str, mode: str, rng: np.random.Generator | None = None) -> str | None:
    if mode == "random":
        if location not in {"above_vwap", "below_vwap"}:
            return None
        return "long" if (rng.random() if rng is not None else 0.5) >= 0.5 else "short"
    if location == "above_vwap":
        return "short" if mode == "fade" else "long"
    if location == "below_vwap":
        return "long" if mode == "fade" else "short"
    return None


def build_diagnostic_trades(
    features: pd.DataFrame,
    cfg: Dict[str, Any],
    signal_mask: pd.Series | np.ndarray,
    mode: str = "fade",
    signal_name: str = "absorption_vwap",
) -> pd.DataFrame:
    horizon = int(cfg.get("features", {}).get("reversal_horizon_bars", 15))
    point_value = float(cfg.get("costs", {}).get("point_value", 1.0) or 1.0)
    cost_points = round_trip_cost_price(cfg)
    rng = np.random.default_rng(int(cfg.get("validation", {}).get("random_seed", 7)))

    df = features.sort_values(["symbol", "timestamp"]).reset_index(drop=True).copy()
    mask = pd.Series(signal_mask).fillna(False).to_numpy(dtype=bool)
    if len(mask) != len(df):
        raise ValueError("signal_mask length must match feature dataframe length")

    group_end = _group_end_positions(df)
    open_arr = df["open"].to_numpy(float)
    high_arr = df["high"].to_numpy(float)
    low_arr = df["low"].to_numpy(float)
    close_arr = df["close"].to_numpy(float)
    vwap_arr = df["session_vwap"].to_numpy(float)
    loc_arr = df["location_vs_vwap"].astype(str).to_numpy()
    rows: List[Dict[str, Any]] = []

    for pos in np.flatnonzero(mask):
        loc = loc_arr[pos]
        direction = _direction_for_location(loc, mode, rng)
        if direction not in {"long", "short"}:
            continue
        start = int(pos) + 1
        end = min(int(group_end[pos]), start + horizon)
        if start >= end or np.isnan(vwap_arr[pos]):
            continue

        entry = float(open_arr[start])
        vwap = float(vwap_arr[pos])
        horizon_close = float(close_arr[end - 1])
        future_high = high_arr[start:end]
        future_low = low_arr[start:end]
        if direction == "long":
            touch_positions = np.flatnonzero(future_high >= vwap)
            target_exit = vwap if len(touch_positions) else horizon_close
            gross_points = target_exit - entry
            pure_horizon_gross_points = horizon_close - entry
            mfe_points = float(np.max(future_high) - entry)
            mae_points = float(entry - np.min(future_low))
        else:
            touch_positions = np.flatnonzero(future_low <= vwap)
            target_exit = vwap if len(touch_positions) else horizon_close
            gross_points = entry - target_exit
            pure_horizon_gross_points = entry - horizon_close
            mfe_points = float(entry - np.min(future_low))
            mae_points = float(np.max(future_high) - entry)
        vwap_touched = bool(len(touch_positions))
        rows.append({
            "signal_name": signal_name,
            "event_position": int(pos),
            "timestamp": df.at[pos, "timestamp"],
            "symbol": df.at[pos, "symbol"],
            "session_date": df.at[pos, "session_date"],
            "session_bucket": df.at[pos, "session_bucket"],
            "location_vs_vwap": loc,
            "direction": direction,
            "entry_price": entry,
            "target_or_horizon_exit_price": target_exit,
            "pure_horizon_exit_price": horizon_close,
            "vwap_touched": vwap_touched,
            "bars_to_vwap_touch": int(touch_positions[0] + 1) if vwap_touched else np.nan,
            "horizon_bars": int(end - start),
            "gross_pnl_points": gross_points,
            "gross_pnl_value": gross_points * point_value,
            "cost_points": cost_points,
            "cost_value": cost_points * point_value,
            "net_pnl_points": gross_points - cost_points,
            "net_pnl_value": (gross_points - cost_points) * point_value,
            "pure_horizon_gross_pnl_points": pure_horizon_gross_points,
            "pure_horizon_net_pnl_value": (pure_horizon_gross_points - cost_points) * point_value,
            "win": (gross_points - cost_points) > 0,
            "pure_horizon_win": (pure_horizon_gross_points - cost_points) > 0,
            "mfe_points": mfe_points,
            "mae_points": mae_points,
            "mfe_mae_ratio": mfe_points / mae_points if mae_points > 0 else np.inf,
            "volume_percentile": df.at[pos, "volume_percentile"],
            "volume_percentile_band": df.at[pos, "volume_percentile_band"],
            "displacement_atr": df.at[pos, "displacement_atr"],
            "displacement_atr_band": df.at[pos, "displacement_atr_band"],
            "vwap_distance_atr": df.at[pos, "vwap_distance_atr"],
            "vwap_distance_atr_band": df.at[pos, "vwap_distance_atr_band"],
        })
    return pd.DataFrame(rows)


def _profit_factor(pnl: pd.Series) -> float:
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    if gross_loss < 0:
        return gross_profit / abs(gross_loss)
    if gross_profit > 0:
        return float("inf")
    return 0.0


def _max_drawdown(pnl: pd.Series) -> float:
    if pnl.empty:
        return 0.0
    equity = pnl.cumsum()
    return float((equity - equity.cummax()).min())


def fold_consistency(trades: pd.DataFrame, folds: int = 5, pnl_col: str = "net_pnl_value") -> Dict[str, Any]:
    if trades.empty:
        return {"positive_folds": 0, "folds": folds, "min_fold_trades": 0, "fold_totals": [], "fold_trade_counts": []}
    ordered = trades.sort_values("timestamp").reset_index(drop=True)
    chunks = np.array_split(ordered.index.to_numpy(), folds)
    totals = []
    counts = []
    for idx in chunks:
        chunk = ordered.loc[idx]
        totals.append(float(chunk[pnl_col].sum()))
        counts.append(int(len(chunk)))
    return {
        "positive_folds": int(sum(v > 0 for v in totals)),
        "folds": folds,
        "min_fold_trades": int(min(counts) if counts else 0),
        "fold_totals": totals,
        "fold_trade_counts": counts,
    }


def trade_metrics(trades: pd.DataFrame, folds: int = 5, pnl_col: str = "net_pnl_value", gross_col: str = "gross_pnl_value") -> Dict[str, Any]:
    if trades.empty:
        return {
            "trades": 0,
            "hit_rate": np.nan,
            "avg_winner": np.nan,
            "avg_loser": np.nan,
            "median_winner": np.nan,
            "median_loser": np.nan,
            "win_loss_ratio": np.nan,
            "expectancy_before_cost": np.nan,
            "expectancy_after_cost": np.nan,
            "cost_drag_per_trade": np.nan,
            "profit_factor": np.nan,
            "max_drawdown": np.nan,
            "positive_folds": 0,
            "min_fold_trades": 0,
        }
    pnl = trades[pnl_col].astype(float)
    gross = trades[gross_col].astype(float)
    winners = pnl[pnl > 0]
    losers = pnl[pnl < 0]
    avg_winner = float(winners.mean()) if len(winners) else np.nan
    avg_loser = float(losers.mean()) if len(losers) else np.nan
    fc = fold_consistency(trades, folds=folds, pnl_col=pnl_col)
    return {
        "trades": int(len(trades)),
        "hit_rate": float((pnl > 0).mean()),
        "avg_winner": avg_winner,
        "avg_loser": avg_loser,
        "median_winner": float(winners.median()) if len(winners) else np.nan,
        "median_loser": float(losers.median()) if len(losers) else np.nan,
        "win_loss_ratio": float(avg_winner / abs(avg_loser)) if len(winners) and len(losers) and avg_loser != 0 else np.nan,
        "expectancy_before_cost": float(gross.mean()),
        "expectancy_after_cost": float(pnl.mean()),
        "cost_drag_per_trade": float((gross - pnl).mean()),
        "profit_factor": _profit_factor(pnl),
        "max_drawdown": _max_drawdown(pnl),
        "positive_folds": fc["positive_folds"],
        "min_fold_trades": fc["min_fold_trades"],
        "fold_totals": fc["fold_totals"],
        "fold_trade_counts": fc["fold_trade_counts"],
    }


def _subset_baseline_metrics(features: pd.DataFrame, cfg: Dict[str, Any], mask: pd.Series, folds: int) -> Dict[str, Any]:
    candidate = build_diagnostic_trades(features, cfg, mask, mode="fade")
    opposite = build_diagnostic_trades(features, cfg, mask, mode="opposite", signal_name="opposite_direction")
    random = build_diagnostic_trades(features, cfg, mask, mode="random", signal_name="random_direction")
    candidate_metrics = trade_metrics(candidate, folds=folds)
    baseline_options = []
    for name, trades in [("opposite_direction", opposite), ("random_direction", random)]:
        metrics = trade_metrics(trades, folds=folds)
        baseline_options.append({"name": name, "hit_rate": metrics["hit_rate"], "expectancy_after_cost": metrics["expectancy_after_cost"], "profit_factor": metrics["profit_factor"]})
    valid = [b for b in baseline_options if not pd.isna(b["hit_rate"])]
    best = max(valid, key=lambda b: b["hit_rate"]) if valid else {"name": None, "hit_rate": np.nan}
    lift = (candidate_metrics["hit_rate"] - best["hit_rate"]) * 100.0 if not pd.isna(candidate_metrics["hit_rate"]) and not pd.isna(best["hit_rate"]) else np.nan
    return {
        **candidate_metrics,
        "events": int(mask.sum()),
        "baseline_name": best.get("name"),
        "baseline_hit_rate": best.get("hit_rate"),
        "lift_pp": lift,
        "baseline_options": baseline_options,
    }


def _breakdown(features: pd.DataFrame, cfg: Dict[str, Any], column: str, values: List[str], base_mask: pd.Series, folds: int) -> pd.DataFrame:
    rows = []
    for value in values:
        mask = base_mask & (features[column].astype(str) == str(value))
        metrics = _subset_baseline_metrics(features, cfg, mask, folds)
        metrics[column] = value
        rows.append(metrics)
    return pd.DataFrame(rows)


def _horizon_sensitivity(features: pd.DataFrame, cfg: Dict[str, Any], base_mask: pd.Series, horizons: List[int], folds: int) -> pd.DataFrame:
    rows = []
    for horizon in horizons:
        hcfg = _copy_with_horizon(cfg, horizon)
        metrics = _subset_baseline_metrics(features, hcfg, base_mask, folds)
        metrics["horizon_bars"] = horizon
        rows.append(metrics)
    return pd.DataFrame(rows)


def _exit_target_diagnostics(trades: pd.DataFrame, folds: int) -> Dict[str, Any]:
    target_metrics = trade_metrics(trades, folds=folds, pnl_col="net_pnl_value", gross_col="gross_pnl_value")
    pure = trades.copy()
    pure["pure_horizon_gross_pnl_value"] = pure["pure_horizon_gross_pnl_points"] * (pure["gross_pnl_value"] / pure["gross_pnl_points"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    pure_metrics = trade_metrics(pure, folds=folds, pnl_col="pure_horizon_net_pnl_value", gross_col="pure_horizon_gross_pnl_value")
    touched = trades[trades["vwap_touched"]]
    not_touched = trades[~trades["vwap_touched"]]
    return {
        "target_or_horizon_metrics": target_metrics,
        "pure_fixed_horizon_metrics": pure_metrics,
        "vwap_touch_rate": float(trades["vwap_touched"].mean()) if len(trades) else np.nan,
        "avg_bars_to_vwap_touch": float(touched["bars_to_vwap_touch"].mean()) if len(touched) else np.nan,
        "median_bars_to_vwap_touch": float(touched["bars_to_vwap_touch"].median()) if len(touched) else np.nan,
        "avg_mfe_points": float(trades["mfe_points"].mean()) if len(trades) else np.nan,
        "avg_mae_points": float(trades["mae_points"].mean()) if len(trades) else np.nan,
        "median_mfe_points": float(trades["mfe_points"].median()) if len(trades) else np.nan,
        "median_mae_points": float(trades["mae_points"].median()) if len(trades) else np.nan,
        "avg_mfe_mae_ratio": float(trades["mfe_mae_ratio"].replace([np.inf, -np.inf], np.nan).mean()) if len(trades) else np.nan,
        "touched_expectancy_after_cost": float(touched["net_pnl_value"].mean()) if len(touched) else np.nan,
        "not_touched_expectancy_after_cost": float(not_touched["net_pnl_value"].mean()) if len(not_touched) else np.nan,
        "fixed_horizon_likely_hurting": bool(pure_metrics["expectancy_after_cost"] < target_metrics["expectancy_after_cost"]) if len(trades) else None,
    }


def _add_neighbor_counts(results: pd.DataFrame, grid: Dict[str, List[Any]]) -> pd.DataFrame:
    out = results.copy()
    if out.empty:
        out["neighbor_count"] = []
        return out
    index_maps = {k: {v: i for i, v in enumerate(vals)} for k, vals in grid.items()}
    passing = out[out.get("passes_hard_filters", False).astype(bool) if "passes_hard_filters" in out.columns else pd.Series(False, index=out.index)]
    coord_to_index = {}
    for idx, row in passing.iterrows():
        coord_to_index[tuple(index_maps[k][row[k]] for k in grid.keys())] = idx
    counts = pd.Series(0, index=out.index, dtype=int)
    passing_coords = list(coord_to_index.keys())
    for coord, idx in coord_to_index.items():
        count = 0
        for other in passing_coords:
            if coord == other:
                continue
            if sum(abs(a - b) for a, b in zip(coord, other)) == 1:
                count += 1
        counts.loc[idx] = count
    out["neighbor_count"] = counts
    return out


def _candidate_simplicity(params: Dict[str, Any], default_features: Dict[str, Any]) -> float:
    score = 1.0
    for key in PARAM_KEYS:
        if key in default_features and key in params:
            base = float(default_features[key])
            val = float(params[key])
            score += abs(val - base) / (abs(base) + 1.0)
    return 1.0 / score


def _plateau_diagnostics(features: pd.DataFrame, cfg: Dict[str, Any], grid_path: str | Path, plateau_dir: str | Path | None, folds: int) -> Dict[str, Any]:
    grid_cfg = load_grid(grid_path)
    grid = {k: list(v) for k, v in grid_cfg.get("grid", grid_cfg).items()}
    if plateau_dir is None:
        latest = Path("reports/parameter_plateaus/latest_run.txt")
        if latest.exists():
            plateau_dir = Path(latest.read_text(encoding="utf-8").strip())
        else:
            dirs = sorted(Path("reports/parameter_plateaus").glob("plateau_*"), key=lambda p: p.stat().st_mtime, reverse=True)
            plateau_dir = dirs[0] if dirs else None
    if plateau_dir is None or not Path(plateau_dir).exists():
        return {"status": "NO_PLATEAU_REPORT", "top_candidates": [], "stable_count": 0}
    plateau_dir = Path(plateau_dir)
    grid_results = pd.read_csv(plateau_dir / "grid_results.csv")
    plateau_json = json.loads((plateau_dir / "plateau.json").read_text(encoding="utf-8")) if (plateau_dir / "plateau.json").exists() else {}
    grid_results = _add_neighbor_counts(grid_results, grid)
    stable = grid_results[(grid_results["passes_hard_filters"].astype(bool)) & (grid_results["neighbor_count"] >= int(grid_cfg.get("min_neighbors_for_plateau", 5)))].copy()
    if stable.empty:
        return {"status": plateau_json.get("status", "NO_STABLE_PLATEAU"), "top_candidates": [], "stable_count": 0, "plateau_dir": str(plateau_dir)}

    stable["rank_seed"] = (
        stable["expectancy_after_cost"].astype(float)
        + (stable["profit_factor"].astype(float) - 1.0) * 10.0
        + stable["hit_rate"].astype(float) * 5.0
        + np.log1p(stable["trade_count"].astype(float))
        - stable["max_drawdown"].abs().astype(float) / 10000.0
        + stable["neighbor_count"].astype(float) / 10.0
    )
    to_evaluate = stable.sort_values("rank_seed", ascending=False).head(300)
    default_features = cfg.get("features", {})
    feature_cache: Dict[tuple, pd.DataFrame] = {}
    candidates = []
    for _, row in to_evaluate.iterrows():
        params = {k: row[k] for k in PARAM_KEYS}
        params["volume_lookback"] = int(params["volume_lookback"])
        params["atr_length"] = int(params["atr_length"])
        params["reversal_horizon_bars"] = int(params["reversal_horizon_bars"])
        cache_key = (params["volume_lookback"], params["atr_length"])
        if cache_key not in feature_cache:
            feature_cache[cache_key] = compute_absorption_features(features[["timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe", "session_date"]], deep_merge(cfg, {"features": params}))
            feature_cache[cache_key] = _add_diagnostic_buckets(feature_cache[cache_key].sort_values(["symbol", "timestamp"]).reset_index(drop=True), cfg)
        cand_features = feature_cache[cache_key].copy()
        cand_features["location_vs_vwap"] = _location_for_threshold(cand_features["vwap_distance_atr"], float(params["near_vwap_threshold_atr"]))
        mask = (
            (cand_features["volume_percentile"] >= float(params["high_volume_percentile_threshold"]))
            & (cand_features["displacement_atr"] <= float(params["max_displacement_atr"]))
            & cand_features["location_vs_vwap"].isin(["above_vwap", "below_vwap"])
        )
        ccfg = deep_merge(cfg, {"features": params})
        metrics = _subset_baseline_metrics(cand_features, ccfg, mask, folds)
        simplicity = _candidate_simplicity(params, default_features)
        survives = bool(
            metrics["trades"] >= int(cfg.get("validation", {}).get("min_events_for_full_validation", 100))
            and metrics["min_fold_trades"] >= int(cfg.get("validation", {}).get("min_events_per_fold", 20))
            and metrics["lift_pp"] >= float(cfg.get("validation", {}).get("min_hit_rate_lift_pp", 4.0))
            and metrics["expectancy_after_cost"] > 0
            and metrics["profit_factor"] > 1.0
            and metrics["positive_folds"] >= 4
            and int(row["neighbor_count"]) >= int(grid_cfg.get("min_neighbors_for_plateau", 5))
        )
        candidate = {
            **params,
            "events": metrics["events"],
            "trades": metrics["trades"],
            "hit_rate": metrics["hit_rate"],
            "baseline_hit_rate": metrics["baseline_hit_rate"],
            "lift_pp": metrics["lift_pp"],
            "expectancy_after_cost": metrics["expectancy_after_cost"],
            "profit_factor": metrics["profit_factor"],
            "max_drawdown": metrics["max_drawdown"],
            "positive_folds": metrics["positive_folds"],
            "min_fold_trades": metrics["min_fold_trades"],
            "neighbor_count": int(row["neighbor_count"]),
            "simplicity_score": simplicity,
            "survives_oos_fold_gate": survives,
            "fold_totals": metrics["fold_totals"],
        }
        candidate["rank_score"] = (
            float(candidate["expectancy_after_cost"])
            + float(candidate["profit_factor"] - 1.0) * 20.0
            + float(candidate["lift_pp"]) / 2.0
            + float(candidate["positive_folds"]) * 2.0
            + float(candidate["simplicity_score"])
            - abs(float(candidate["max_drawdown"])) / 2000.0
        )
        candidates.append(candidate)
    cand_df = pd.DataFrame(candidates)
    if cand_df.empty:
        top = []
        surviving_count = 0
    else:
        surviving_count = int(cand_df["survives_oos_fold_gate"].sum())
        if surviving_count:
            ranked = cand_df.sort_values(["survives_oos_fold_gate", "rank_score"], ascending=[False, False])
        else:
            ranked = cand_df.sort_values("rank_score", ascending=False)
        top = ranked.head(10).to_dict("records")
    return {
        "status": plateau_json.get("status", "UNKNOWN"),
        "plateau_dir": str(plateau_dir),
        "stable_count": int(len(stable)),
        "evaluated_stable_candidates": int(len(to_evaluate)),
        "surviving_oos_fold_gate_count_in_evaluated_set": surviving_count,
        "centroid": plateau_json.get("centroid"),
        "top_candidates": top,
    }


def _classification(default_metrics: Dict[str, Any], plateau_diag: Dict[str, Any], exit_diag: Dict[str, Any]) -> Dict[str, str]:
    surviving = int(plateau_diag.get("surviving_oos_fold_gate_count_in_evaluated_set", 0) or 0)
    if surviving > 0:
        return {
            "classification": "standalone strategy candidate",
            "reason": "At least one stable parameter-region candidate passed the diagnostic fold gates; still requires separate forward/OOS confirmation before validation language.",
        }
    if default_metrics.get("hit_rate", 0) > 0.55 and default_metrics.get("expectancy_after_cost", -1) <= 0:
        if exit_diag.get("vwap_touch_rate", 0) > 0.5:
            return {
                "classification": "exit/filter candidate only",
                "reason": "Directional hit rate is high, but payoff asymmetry, negative expectancy, and PF below 1 indicate the raw entry is not a standalone strategy under current exits/costs.",
            }
        return {
            "classification": "VWAP reversion warning module",
            "reason": "The signal appears directionally informative but does not clear standalone expectancy/profit-factor gates.",
        }
    return {"classification": "reject for MNQ", "reason": "Directional and payoff metrics do not justify continued MNQ standalone research under current definition."}


def run_diagnostics(df: pd.DataFrame, cfg: Dict[str, Any], grid_path: str | Path, plateau_dir: str | Path | None = None) -> Dict[str, Any]:
    folds = int(cfg.get("validation", {}).get("folds", 5))
    features = compute_absorption_features(df, cfg).sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    features = _add_diagnostic_buckets(features, cfg)
    absorption_mask = features["is_absorption_bar"].fillna(False)
    directional_mask = absorption_mask & features["location_vs_vwap"].isin(["above_vwap", "below_vwap"])
    default_trades = build_diagnostic_trades(features, cfg, directional_mask, mode="fade")
    default_metrics = trade_metrics(default_trades, folds=folds)
    baseline_metrics = _subset_baseline_metrics(features, cfg, directional_mask, folds)
    payoff = {
        "average_winner": default_metrics["avg_winner"],
        "average_loser": default_metrics["avg_loser"],
        "median_winner": default_metrics["median_winner"],
        "median_loser": default_metrics["median_loser"],
        "win_loss_ratio": default_metrics["win_loss_ratio"],
        "expectancy_before_cost": default_metrics["expectancy_before_cost"],
        "expectancy_after_cost": default_metrics["expectancy_after_cost"],
        "estimated_cost_drag_per_trade": default_metrics["cost_drag_per_trade"],
    }

    location_values = ["above_vwap", "below_vwap", "near_vwap"]
    location_breakdown = _breakdown(features, cfg, "location_vs_vwap", location_values, absorption_mask, folds)
    direction_rows = []
    for direction, loc in [("long", "below_vwap"), ("short", "above_vwap")]:
        mask = absorption_mask & (features["location_vs_vwap"] == loc)
        row = _subset_baseline_metrics(features, cfg, mask, folds)
        row["direction"] = direction
        row["source_location"] = loc
        direction_rows.append(row)
    direction_breakdown = pd.DataFrame(direction_rows)
    session_breakdown = _breakdown(features, cfg, "session_bucket", SESSION_BUCKETS, directional_mask, folds)
    volume_breakdown = _breakdown(features, cfg, "volume_percentile_band", ["95-97.5", "97.5-99", "99-100"], directional_mask, folds)
    displacement_breakdown = _breakdown(features, cfg, "displacement_atr_band", ["0-0.10", "0.10-0.20", "0.20-0.30"], directional_mask, folds)
    vwap_distance_breakdown = _breakdown(features, cfg, "vwap_distance_atr_band", ["0.25-0.50", "0.50-1.00", "1.00-2.00", ">2.00"], directional_mask, folds)
    horizon_sensitivity = _horizon_sensitivity(features, cfg, directional_mask, [5, 8, 10, 15, 20, 30], folds)
    exit_diag = _exit_target_diagnostics(default_trades, folds)
    plateau_diag = _plateau_diagnostics(features, cfg, grid_path, plateau_dir, folds)
    classification = _classification(default_metrics, plateau_diag, exit_diag)

    raw_range = {
        "bars_loaded": int(len(df)),
        "date_start": df["timestamp"].min().isoformat(),
        "date_end": df["timestamp"].max().isoformat(),
        "sessions": int(df["session_date"].nunique()) if "session_date" in df.columns else None,
    }
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "data": raw_range,
        "event_definition": {
            "volume_lookback": cfg.get("features", {}).get("volume_lookback"),
            "high_volume_percentile_threshold": cfg.get("features", {}).get("high_volume_percentile_threshold"),
            "atr_length": cfg.get("features", {}).get("atr_length"),
            "max_displacement_atr": cfg.get("features", {}).get("max_displacement_atr"),
            "near_vwap_threshold_atr": cfg.get("features", {}).get("near_vwap_threshold_atr"),
            "reversal_horizon_bars": cfg.get("features", {}).get("reversal_horizon_bars"),
        },
        "event_counts": {
            "absorption_events": int(absorption_mask.sum()),
            "directional_events": int(directional_mask.sum()),
            "above_vwap": int((absorption_mask & (features["location_vs_vwap"] == "above_vwap")).sum()),
            "below_vwap": int((absorption_mask & (features["location_vs_vwap"] == "below_vwap")).sum()),
            "near_vwap": int((absorption_mask & (features["location_vs_vwap"] == "near_vwap")).sum()),
        },
        "payoff_distribution": payoff,
        "default_metrics": default_metrics,
        "best_same_universe_baseline_hit_rate": baseline_metrics["baseline_hit_rate"],
        "lift_over_best_same_universe_baseline_pp": baseline_metrics["lift_pp"],
        "exit_target_diagnostics": exit_diag,
        "plateau_diagnostics": plateau_diag,
        "final_diagnostic_classification": classification,
        "hard_rule_status_default": {
            "at_least_100_events": bool(default_metrics["trades"] >= 100),
            "at_least_20_events_per_fold": bool(default_metrics["min_fold_trades"] >= 20),
            "lift_at_least_4pp": bool(baseline_metrics["lift_pp"] >= 4.0),
            "positive_after_cost_expectancy": bool(default_metrics["expectancy_after_cost"] > 0),
            "profit_factor_gt_1": bool(default_metrics["profit_factor"] > 1.0),
            "at_least_4_of_5_positive_folds": bool(default_metrics["positive_folds"] >= 4),
            "stable_oos_plateau_support": bool(plateau_diag.get("surviving_oos_fold_gate_count_in_evaluated_set", 0) > 0),
        },
    }
    tables = {
        "location_breakdown": location_breakdown,
        "direction_breakdown": direction_breakdown,
        "session_breakdown": session_breakdown,
        "volume_percentile_breakdown": volume_breakdown,
        "displacement_atr_breakdown": displacement_breakdown,
        "vwap_distance_atr_breakdown": vwap_distance_breakdown,
        "horizon_sensitivity": horizon_sensitivity,
        "default_trades": default_trades,
        "top_plateau_candidates": pd.DataFrame(plateau_diag.get("top_candidates", [])),
    }
    return {"summary": summary, "tables": tables, "features": features}


def _table_md(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df.empty:
        return "_No rows._\n"
    sample = df.head(max_rows).copy()
    cols = [str(c) for c in sample.columns]
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in sample.iterrows():
        values = []
        for col in sample.columns:
            value = row[col]
            if isinstance(value, float):
                if math.isnan(value):
                    text = ""
                else:
                    text = f"{value:.6g}"
            else:
                text = str(value)
            values.append(text.replace("|", "/"))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows) + "\n"


def write_diagnostic_report(result: Dict[str, Any], cfg: Dict[str, Any]) -> Path:
    run_dir = make_run_dir("reports/diagnostics", "diagnostic")
    summary = result["summary"]
    tables = result["tables"]
    (run_dir / "diagnostic_summary.json").write_text(json.dumps(summary, indent=2, default=_json_safe), encoding="utf-8")
    for name, table in tables.items():
        table.to_csv(run_dir / f"{name}.csv", index=False)
    lines = ["# MNQ Post-Absorption VWAP Diagnostic Report", ""]
    lines.append("This is a diagnostic-only report. It does not change entry/exit logic and does not make trading recommendations.")
    lines.append("")
    lines.append(f"Final diagnostic classification: **{summary['final_diagnostic_classification']['classification']}**")
    lines.append(f"Reason: {summary['final_diagnostic_classification']['reason']}")
    lines.append("")
    lines.append("## Payoff distribution")
    for key, value in summary["payoff_distribution"].items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("## Default hard-rule status")
    for key, value in summary["hard_rule_status_default"].items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    for title, key in [
        ("VWAP location breakdown", "location_breakdown"),
        ("Direction breakdown", "direction_breakdown"),
        ("Session breakdown", "session_breakdown"),
        ("Volume percentile buckets", "volume_percentile_breakdown"),
        ("Displacement/ATR buckets", "displacement_atr_breakdown"),
        ("VWAP-distance/ATR buckets", "vwap_distance_atr_breakdown"),
        ("Horizon sensitivity", "horizon_sensitivity"),
        ("Top plateau candidates", "top_plateau_candidates"),
    ]:
        lines.append(f"## {title}")
        lines.append(_table_md(tables[key], max_rows=12))
        lines.append("")
    (run_dir / "diagnostic_report.md").write_text("\n".join(lines), encoding="utf-8")
    return run_dir

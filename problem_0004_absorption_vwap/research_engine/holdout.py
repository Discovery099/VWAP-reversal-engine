from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .diagnostics import (
    PARAM_KEYS,
    _add_diagnostic_buckets,
    _add_neighbor_counts,
    _candidate_simplicity,
    _location_for_threshold,
    _table_md,
    build_diagnostic_trades,
    trade_metrics,
)
from .features import compute_absorption_features
from .plateau import load_grid, run_plateau
from .reports import _json_safe, make_run_dir
from .schemas import deep_merge


PREDEFINED_FILTERS = [
    {"id": "default_all_trades", "description": "Default directional absorption trades; near-VWAP excluded", "filters": {}},
    {"id": "default_above_vwap_shorts_only", "description": "Above-VWAP absorption short reversals only", "filters": {"locations": ["above_vwap"]}},
    {"id": "default_below_vwap_longs_only", "description": "Below-VWAP absorption long reversals only", "filters": {"locations": ["below_vwap"]}},
    {"id": "default_excluding_near_vwap", "description": "Explicit near-VWAP exclusion; same as directional default", "filters": {"locations": ["above_vwap", "below_vwap"]}},
    {"id": "default_excluding_last_30m", "description": "Default directional trades excluding last 30 minutes", "filters": {"exclude_session_buckets": ["last_30m"]}},
    {"id": "default_displacement_010_020", "description": "Default parameters with displacement/ATR 0.10–0.20", "filters": {"displacement_min": 0.10, "displacement_max": 0.20}},
    {"id": "default_vwap_distance_100_200", "description": "Default parameters with abs VWAP-distance/ATR 1.00–2.00", "filters": {"vwap_distance_min": 1.00, "vwap_distance_max": 2.00}},
    {"id": "default_volume_975_990", "description": "Default parameters with volume percentile 97.5–99; excludes 99–100 extreme bucket", "filters": {"volume_percentile_min": 97.5, "volume_percentile_max": 99.0}},
]


def _split_data(df: pd.DataFrame, train_end: str, holdout_start: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    ts = df["timestamp"]
    tz = getattr(ts.dt, "tz", None)
    train_end_ts = pd.Timestamp(train_end)
    holdout_start_ts = pd.Timestamp(holdout_start)
    if tz is not None:
        if train_end_ts.tzinfo is None:
            train_end_ts = train_end_ts.tz_localize(tz)
        else:
            train_end_ts = train_end_ts.tz_convert(tz)
        if holdout_start_ts.tzinfo is None:
            holdout_start_ts = holdout_start_ts.tz_localize(tz)
        else:
            holdout_start_ts = holdout_start_ts.tz_convert(tz)
    train = df[df["timestamp"] <= train_end_ts].copy()
    holdout = df[df["timestamp"] >= holdout_start_ts].copy()
    return train, holdout


def _params_from_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    f = cfg.get("features", {})
    return {key: f[key] for key in PARAM_KEYS if key in f}


def _params_from_row(row: pd.Series) -> Dict[str, Any]:
    params = {key: row[key] for key in PARAM_KEYS}
    for key in ["volume_lookback", "atr_length", "reversal_horizon_bars"]:
        params[key] = int(params[key])
    for key in ["high_volume_percentile_threshold", "max_displacement_atr", "near_vwap_threshold_atr"]:
        params[key] = float(params[key])
    return params


def _base_features(df: pd.DataFrame) -> pd.DataFrame:
    return df[["timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe", "session_date"]].copy()


def _candidate_mask(features: pd.DataFrame, params: Dict[str, Any], filters: Dict[str, Any]) -> pd.Series:
    loc = features["location_vs_vwap"].astype(str)
    allowed_locations = filters.get("locations", ["above_vwap", "below_vwap"])
    mask = (
        (features["volume_percentile"] >= float(params["high_volume_percentile_threshold"]))
        & (features["displacement_atr"] <= float(params["max_displacement_atr"]))
        & loc.isin(allowed_locations)
    )
    if filters.get("exclude_session_buckets"):
        mask &= ~features["session_bucket"].isin(filters["exclude_session_buckets"])
    if filters.get("session_buckets"):
        mask &= features["session_bucket"].isin(filters["session_buckets"])
    if "displacement_min" in filters:
        mask &= features["displacement_atr"] >= float(filters["displacement_min"])
    if "displacement_max" in filters:
        mask &= features["displacement_atr"] <= float(filters["displacement_max"])
    if "vwap_distance_min" in filters:
        mask &= features["abs_vwap_distance_atr"] >= float(filters["vwap_distance_min"])
    if "vwap_distance_max" in filters:
        mask &= features["abs_vwap_distance_atr"] <= float(filters["vwap_distance_max"])
    if "volume_percentile_min" in filters:
        mask &= features["volume_percentile"] >= float(filters["volume_percentile_min"])
    if "volume_percentile_max" in filters:
        mask &= features["volume_percentile"] < float(filters["volume_percentile_max"])
    return mask.fillna(False)


def _features_for_params(raw_df: pd.DataFrame, cfg: Dict[str, Any], params: Dict[str, Any], cache: Dict[tuple, pd.DataFrame]) -> pd.DataFrame:
    cache_key = (int(params["volume_lookback"]), int(params["atr_length"]))
    if cache_key not in cache:
        cache[cache_key] = compute_absorption_features(_base_features(raw_df), deep_merge(cfg, {"features": params}))
        cache[cache_key] = _add_diagnostic_buckets(cache[cache_key].sort_values(["symbol", "timestamp"]).reset_index(drop=True), cfg)
    features = cache[cache_key].copy()
    features["location_vs_vwap"] = _location_for_threshold(features["vwap_distance_atr"], float(params["near_vwap_threshold_atr"]))
    features["abs_vwap_distance_atr"] = features["vwap_distance_atr"].abs()
    return features


def _metrics_for_exit_style(trades: pd.DataFrame, exit_style: str, folds: int) -> Dict[str, Any]:
    if trades.empty:
        return trade_metrics(trades, folds=folds)
    t = trades.copy()
    if exit_style == "fixed_horizon":
        t["pure_horizon_gross_pnl_value"] = t["pure_horizon_gross_pnl_points"] * (t["gross_pnl_value"] / t["gross_pnl_points"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
        return trade_metrics(t, folds=folds, pnl_col="pure_horizon_net_pnl_value", gross_col="pure_horizon_gross_pnl_value")
    return trade_metrics(t, folds=folds, pnl_col="net_pnl_value", gross_col="gross_pnl_value")


def _pnl_col(exit_style: str) -> str:
    return "pure_horizon_net_pnl_value" if exit_style == "fixed_horizon" else "net_pnl_value"


def _monthly_consistency(trades: pd.DataFrame, exit_style: str) -> Dict[str, Any]:
    if trades.empty:
        return {"positive_months": 0, "total_months": 0, "positive_month_pct": np.nan, "largest_month_profit_share": np.nan, "month_totals": {}}
    pnl_col = _pnl_col(exit_style)
    t = trades.copy()
    t["month"] = pd.to_datetime(t["timestamp"]).dt.to_period("M").astype(str)
    month_totals = t.groupby("month")[pnl_col].sum().astype(float)
    positive = int((month_totals > 0).sum())
    total = int(len(month_totals))
    total_profit = float(month_totals.sum())
    largest_share = float(month_totals.clip(lower=0).max() / total_profit) if total_profit > 0 else np.nan
    return {
        "positive_months": positive,
        "total_months": total,
        "positive_month_pct": float(positive / total) if total else np.nan,
        "largest_month_profit_share": largest_share,
        "month_totals": month_totals.to_dict(),
    }


def _not_touch_profile(trades: pd.DataFrame, exit_style: str) -> Dict[str, Any]:
    if trades.empty:
        return {"vwap_touch_rate": np.nan, "not_touch_trades": 0, "not_touch_avg_loss": np.nan, "not_touch_expectancy": np.nan, "not_touch_pf": np.nan}
    pnl_col = _pnl_col(exit_style)
    not_touch = trades[~trades["vwap_touched"]]
    losses = not_touch[not_touch[pnl_col] < 0][pnl_col]
    return {
        "vwap_touch_rate": float(trades["vwap_touched"].mean()),
        "not_touch_trades": int(len(not_touch)),
        "not_touch_avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "not_touch_expectancy": float(not_touch[pnl_col].mean()) if len(not_touch) else np.nan,
        "not_touch_loss_count": int(len(losses)),
    }


def _side_breakdown(candidate_id: str, exit_style: str, trades: pd.DataFrame, folds: int) -> List[Dict[str, Any]]:
    rows = []
    for direction in ["long", "short"]:
        subset = trades[trades["direction"] == direction]
        metrics = _metrics_for_exit_style(subset, exit_style, folds)
        rows.append({"candidate_id": candidate_id, "exit_style": exit_style, "direction": direction, **metrics})
    return rows


def _session_breakdown(candidate_id: str, exit_style: str, trades: pd.DataFrame, folds: int) -> List[Dict[str, Any]]:
    rows = []
    for bucket in ["first_30m", "morning", "midday", "afternoon", "last_30m"]:
        subset = trades[trades["session_bucket"] == bucket]
        metrics = _metrics_for_exit_style(subset, exit_style, folds)
        rows.append({"candidate_id": candidate_id, "exit_style": exit_style, "session_bucket": bucket, **metrics})
    return rows


def _evaluate_candidate(
    candidate: Dict[str, Any],
    features: pd.DataFrame,
    cfg: Dict[str, Any],
    folds: int,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], pd.DataFrame]:
    params = candidate["params"]
    ccfg = deep_merge(cfg, {"features": params})
    mask = _candidate_mask(features, params, candidate.get("filters", {}))
    trades = build_diagnostic_trades(features, ccfg, mask, mode="fade", signal_name=candidate["id"])
    opposite = build_diagnostic_trades(features, ccfg, mask, mode="opposite", signal_name=f"{candidate['id']}_opposite")
    random = build_diagnostic_trades(features, ccfg, mask, mode="random", signal_name=f"{candidate['id']}_random")
    candidate_rows: List[Dict[str, Any]] = []
    side_rows: List[Dict[str, Any]] = []
    session_rows: List[Dict[str, Any]] = []
    for exit_style in ["target_or_horizon", "fixed_horizon"]:
        metrics = _metrics_for_exit_style(trades, exit_style, folds)
        opposite_metrics = _metrics_for_exit_style(opposite, exit_style, folds)
        random_metrics = _metrics_for_exit_style(random, exit_style, folds)
        baselines = [
            {"name": "opposite_direction", "hit_rate": opposite_metrics["hit_rate"]},
            {"name": "random_direction", "hit_rate": random_metrics["hit_rate"]},
        ]
        valid_baselines = [b for b in baselines if not pd.isna(b["hit_rate"])]
        best = max(valid_baselines, key=lambda b: b["hit_rate"]) if valid_baselines else {"name": None, "hit_rate": np.nan}
        lift = (metrics["hit_rate"] - best["hit_rate"]) * 100.0 if not pd.isna(metrics["hit_rate"]) and not pd.isna(best["hit_rate"]) else np.nan
        monthly = _monthly_consistency(trades, exit_style)
        not_touch = _not_touch_profile(trades, exit_style)
        total_pnl = float(trades[_pnl_col(exit_style)].sum()) if not trades.empty else 0.0
        drawdown_recovery = total_pnl / abs(metrics["max_drawdown"]) if metrics.get("max_drawdown") and metrics["max_drawdown"] < 0 else np.nan
        max_drawdown_acceptable = bool(not pd.isna(drawdown_recovery) and drawdown_recovery >= 0.5)
        passes = bool(
            metrics["trades"] >= 100
            and lift >= 4.0
            and metrics["expectancy_after_cost"] > 0
            and metrics["profit_factor"] > 1.15
            and max_drawdown_acceptable
            and monthly["positive_month_pct"] >= 0.60
            and (pd.isna(monthly["largest_month_profit_share"]) or monthly["largest_month_profit_share"] <= 0.50)
            and candidate.get("stable_training_plateau", False)
        )
        row = {
            "candidate_id": candidate["id"],
            "source": candidate["source"],
            "description": candidate["description"],
            "exit_style": exit_style,
            "baseline_name": best.get("name"),
            "baseline_hit_rate": best.get("hit_rate"),
            "lift_pp": lift,
            "positive_months": monthly["positive_months"],
            "total_months": monthly["total_months"],
            "positive_month_pct": monthly["positive_month_pct"],
            "largest_month_profit_share": monthly["largest_month_profit_share"],
            "total_net_pnl": total_pnl,
            "drawdown_recovery_ratio": drawdown_recovery,
            "max_drawdown_acceptable_proxy": max_drawdown_acceptable,
            "passes_holdout_hard_gates": passes,
            "stable_training_plateau": bool(candidate.get("stable_training_plateau", False)),
            "neighbor_count_training": candidate.get("neighbor_count_training"),
            **params,
            **candidate.get("filters", {}),
            **metrics,
            **not_touch,
        }
        candidate_rows.append(row)
        side_rows.extend(_side_breakdown(candidate["id"], exit_style, trades, folds))
        session_rows.extend(_session_breakdown(candidate["id"], exit_style, trades, folds))
    return candidate_rows, side_rows, session_rows, trades


def _rank_training_candidates(
    train_df: pd.DataFrame,
    cfg: Dict[str, Any],
    grid_cfg: Dict[str, Any],
    top_n: int,
) -> tuple[List[Dict[str, Any]], Dict[str, Any], pd.DataFrame]:
    plateau_result = run_plateau(train_df, cfg, grid_cfg)
    grid = {k: list(v) for k, v in grid_cfg.get("grid", grid_cfg).items()}
    grid_results = _add_neighbor_counts(plateau_result["grid_results"], grid)
    min_neighbors = int(grid_cfg.get("min_neighbors_for_plateau", 5))
    stable = grid_results[(grid_results["passes_hard_filters"].astype(bool)) & (grid_results["neighbor_count"] >= min_neighbors)].copy()
    if stable.empty:
        return [], plateau_result["plateau"], grid_results

    stable["rank_seed"] = (
        stable["expectancy_after_cost"].astype(float)
        + (stable["profit_factor"].astype(float) - 1.0) * 10.0
        + stable["hit_rate"].astype(float) * 5.0
        + np.log1p(stable["trade_count"].astype(float))
        - stable["max_drawdown"].abs().astype(float) / 10000.0
        + stable["neighbor_count"].astype(float) / 10.0
    )
    selected = stable.sort_values("rank_seed", ascending=False).head(top_n)
    defaults = cfg.get("features", {})
    candidates = []
    for i, (_, row) in enumerate(selected.iterrows(), start=1):
        params = _params_from_row(row)
        candidates.append({
            "id": f"train_plateau_{i:02d}",
            "source": "training_plateau_top10",
            "description": "Frozen top training plateau diagnostic parameter candidate",
            "params": params,
            "filters": {},
            "stable_training_plateau": True,
            "neighbor_count_training": int(row["neighbor_count"]),
            "training_rank_seed": float(row["rank_seed"]),
            "simplicity_score": _candidate_simplicity(params, defaults),
        })
    return candidates, plateau_result["plateau"], grid_results


def _predefined_candidates(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    params = _params_from_cfg(cfg)
    rows = []
    for spec in PREDEFINED_FILTERS:
        rows.append({
            "id": spec["id"],
            "source": "predefined_training_protocol_filter",
            "description": spec["description"],
            "params": deepcopy(params),
            "filters": deepcopy(spec["filters"]),
            "stable_training_plateau": spec["id"] in {"default_all_trades", "default_excluding_near_vwap"},
            "neighbor_count_training": None,
            "simplicity_score": 1.0,
        })
    return rows


def _evaluate_holdout_candidates(
    candidates: List[Dict[str, Any]],
    holdout_df: pd.DataFrame,
    cfg: Dict[str, Any],
    folds: int,
) -> Dict[str, pd.DataFrame]:
    feature_cache: Dict[tuple, pd.DataFrame] = {}
    candidate_rows: List[Dict[str, Any]] = []
    side_rows: List[Dict[str, Any]] = []
    session_rows: List[Dict[str, Any]] = []
    for candidate in candidates:
        params = candidate["params"]
        features = _features_for_params(holdout_df, cfg, params, feature_cache)
        rows, sides, sessions, _ = _evaluate_candidate(candidate, features, cfg, folds)
        candidate_rows.extend(rows)
        side_rows.extend(sides)
        session_rows.extend(sessions)
    return {
        "candidate_metrics": pd.DataFrame(candidate_rows),
        "side_breakdown": pd.DataFrame(side_rows),
        "session_breakdown": pd.DataFrame(session_rows),
    }


def _final_verdict(candidate_metrics: pd.DataFrame) -> Dict[str, Any]:
    if candidate_metrics.empty:
        return {"verdict": "INSUFFICIENT_DATA", "reason": "No holdout candidates produced trades."}
    passed = candidate_metrics[candidate_metrics["passes_holdout_hard_gates"].astype(bool)].copy()
    if passed.empty:
        best = candidate_metrics.sort_values(["expectancy_after_cost", "profit_factor"], ascending=False).head(1).to_dict("records")[0]
        return {
            "verdict": "NOT_VALIDATED",
            "reason": "No frozen training-selected candidate passed all holdout hard gates. Preserve as filter/exit research candidate only.",
            "best_candidate_id": best.get("candidate_id"),
            "best_exit_style": best.get("exit_style"),
        }
    best = passed.sort_values(["expectancy_after_cost", "profit_factor", "positive_month_pct"], ascending=False).head(1).to_dict("records")[0]
    return {
        "verdict": "VALIDATED_WEAK",
        "reason": "At least one frozen training-selected candidate passed the strict holdout gates. Requires cross-instrument replication before stronger language.",
        "best_candidate_id": best.get("candidate_id"),
        "best_exit_style": best.get("exit_style"),
        "passed_candidate_count": int(len(passed)),
    }


def run_holdout_confirmation(
    df: pd.DataFrame,
    cfg: Dict[str, Any],
    grid_path: str | Path,
    train_end: str = "2023-12-31 23:59:59",
    holdout_start: str = "2024-01-01 00:00:00",
    top_n: int = 10,
) -> Dict[str, Any]:
    grid_cfg = load_grid(grid_path)
    train_df, holdout_df = _split_data(df, train_end, holdout_start)
    top_candidates, train_plateau, train_grid_results = _rank_training_candidates(train_df, cfg, grid_cfg, top_n)
    candidates = _predefined_candidates(cfg) + top_candidates
    folds = int(cfg.get("validation", {}).get("folds", 5))
    tables = _evaluate_holdout_candidates(candidates, holdout_df, cfg, folds)
    verdict = _final_verdict(tables["candidate_metrics"])
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "training_selection_start": train_df["timestamp"].min().isoformat() if len(train_df) else None,
            "training_selection_end": train_df["timestamp"].max().isoformat() if len(train_df) else None,
            "holdout_start": holdout_df["timestamp"].min().isoformat() if len(holdout_df) else None,
            "holdout_end": holdout_df["timestamp"].max().isoformat() if len(holdout_df) else None,
            "training_bars": int(len(train_df)),
            "holdout_bars": int(len(holdout_df)),
            "top_training_candidates_selected": int(len(top_candidates)),
            "predefined_candidates_tested": int(len(PREDEFINED_FILTERS)),
            "exit_styles": ["target_or_horizon", "fixed_horizon"],
            "data_leakage_control": "Plateau/candidates/filters selected on training window only; holdout evaluated after freezing candidates.",
        },
        "training_plateau": train_plateau,
        "final_verdict": verdict,
        "holdout_hard_rules": {
            "min_trades": 100,
            "min_lift_pp": 4.0,
            "positive_after_cost_expectancy": True,
            "profit_factor_gt": 1.15,
            "positive_month_pct_min": 0.60,
            "largest_month_profit_share_max": 0.50,
            "max_drawdown_acceptable_proxy": "total net pnl / abs(max drawdown) >= 0.5",
            "stable_training_plateau_required": True,
        },
    }
    return {"summary": summary, "tables": tables, "training_grid_results": train_grid_results, "candidates": pd.DataFrame(candidates)}


def _summary_table_for_md(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "candidate_id", "exit_style", "source", "trades", "hit_rate", "baseline_hit_rate", "lift_pp",
        "expectancy_before_cost", "expectancy_after_cost", "profit_factor", "max_drawdown",
        "positive_months", "total_months", "positive_month_pct", "largest_month_profit_share",
        "vwap_touch_rate", "not_touch_expectancy", "passes_holdout_hard_gates",
    ]
    return df[[c for c in cols if c in df.columns]].sort_values(["passes_holdout_hard_gates", "expectancy_after_cost"], ascending=[False, False])


def write_holdout_report(result: Dict[str, Any], cfg: Dict[str, Any]) -> Path:
    run_dir = make_run_dir("reports/holdout", "holdout")
    summary = result["summary"]
    tables = result["tables"]
    (run_dir / "holdout_summary.json").write_text(json.dumps(summary, indent=2, default=_json_safe), encoding="utf-8")
    for name, table in tables.items():
        table.to_csv(run_dir / f"{name}.csv", index=False)
    result["training_grid_results"].to_csv(run_dir / "training_grid_results.csv", index=False)
    result["candidates"].to_csv(run_dir / "frozen_candidates.csv", index=False)

    metrics = tables["candidate_metrics"]
    lines = ["# MNQ Strict Train/Holdout Confirmation Report", ""]
    lines.append("This report uses 2020-2023 for training/selection and 2024-2026 for holdout validation. Candidates are frozen before holdout evaluation.")
    lines.append("")
    lines.append(f"Final verdict: **{summary['final_verdict']['verdict']}**")
    lines.append(f"Reason: {summary['final_verdict']['reason']}")
    lines.append("")
    lines.append("## Protocol")
    for key, value in summary["protocol"].items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("## Top holdout candidates")
    lines.append(_table_md(_summary_table_for_md(metrics), max_rows=20))
    lines.append("")
    lines.append("## Side breakdown")
    lines.append(_table_md(tables["side_breakdown"], max_rows=30))
    lines.append("")
    lines.append("## Session breakdown")
    lines.append(_table_md(tables["session_breakdown"], max_rows=40))
    lines.append("")
    (run_dir / "holdout_report.md").write_text("\n".join(lines), encoding="utf-8")
    return run_dir

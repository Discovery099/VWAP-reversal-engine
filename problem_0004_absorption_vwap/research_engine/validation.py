from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from .backtest import build_trades, summarize_trades
from .features import compute_absorption_features
from .labels import label_absorption_events
from .signal_logic import rsi


def _fold_metrics(trades: pd.DataFrame, folds: int) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["fold", "trade_count", "hit_rate", "expectancy_after_cost", "total_net_pnl", "profit_factor", "max_drawdown"])
    ordered = trades.sort_values("timestamp").reset_index(drop=True)
    chunks = np.array_split(ordered.index.to_numpy(), max(1, folds))
    rows = []
    for i, idx in enumerate(chunks, start=1):
        chunk = ordered.loc[idx]
        metrics = summarize_trades(chunk)
        metrics["fold"] = i
        rows.append(metrics)
    return pd.DataFrame(rows)[["fold", "trade_count", "hit_rate", "expectancy_after_cost", "total_net_pnl", "profit_factor", "max_drawdown"]]


def _baseline_trades(features: pd.DataFrame, cfg: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    f = features.copy()
    directional = f["location_vs_vwap"].isin(["above_vwap", "below_vwap"])
    baselines: Dict[str, pd.DataFrame] = {}
    baselines["absorption_vwap"] = build_trades(f, cfg, f["is_absorption_bar"] & directional, "absorption_vwap")
    baselines["high_volume_only"] = build_trades(f, cfg, f["high_volume_pass"] & directional, "high_volume_only")
    baselines["low_displacement_only"] = build_trades(f, cfg, f["low_displacement_pass"] & directional, "low_displacement_only")
    baselines["vwap_fade_no_absorption"] = build_trades(f, cfg, directional, "vwap_fade_no_absorption")

    rsi_series = pd.Series(index=f.index, dtype=float)
    for _, group in f.groupby("symbol", sort=False):
        rsi_series.loc[group.index] = rsi(group["close"], 14)
    directions = pd.Series(index=f.index, dtype=object)
    directions.loc[rsi_series < 30] = "long"
    directions.loc[rsi_series > 70] = "short"
    baselines["rsi_reversal"] = build_trades(f, cfg, directions.notna(), "rsi_reversal", direction_series=directions)
    baselines["random_direction_on_absorption"] = build_trades(f, cfg, f["is_absorption_bar"] & directional, "random_direction_on_absorption", random_direction=True)
    return baselines


def _baseline_summary(baselines: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, trades in baselines.items():
        metrics = summarize_trades(trades)
        metrics["baseline"] = name
        rows.append(metrics)
    return pd.DataFrame(rows)[["baseline", "trade_count", "hit_rate", "expectancy_after_cost", "total_net_pnl", "profit_factor", "max_drawdown"]]


def _time_bucket(ts: pd.Timestamp, session_start: pd.Timestamp) -> str:
    minutes = (ts - session_start).total_seconds() / 60.0
    if minutes <= 60:
        return "first_hour"
    if minutes >= 330:
        return "final_hour"
    return "midday"


def _event_diagnostics(features: pd.DataFrame, labels: pd.DataFrame) -> Dict[str, Any]:
    diag: Dict[str, Any] = {}
    if labels.empty:
        return {"absorption_event_count": 0, "by_side": {}, "by_session": {}, "by_volume_bucket": {}, "by_time_bucket": {}}
    diag["absorption_event_count"] = int(len(labels))
    diag["by_side"] = labels.groupby("absorption_side").size().to_dict()
    by_session = labels.groupby(["symbol", "session_date"]).size().astype(int).to_dict()
    diag["by_session"] = {f"{symbol}|{session}": int(count) for (symbol, session), count in by_session.items()}
    labeled = labels.copy()
    labeled["volume_bucket"] = pd.cut(labeled["volume_percentile"], bins=[0, 90, 95, 97.5, 100], include_lowest=True).astype(str)
    diag["by_volume_bucket"] = labeled.groupby("volume_bucket")["reversed_toward_vwap"].mean().fillna(0).to_dict()
    session_start = features.groupby(["symbol", "session_date"])["timestamp"].min().to_dict()
    buckets = []
    for _, row in labeled.iterrows():
        buckets.append(_time_bucket(row["timestamp"], session_start[(row["symbol"], row["session_date"])]))
    labeled["time_bucket"] = buckets
    diag["by_time_bucket"] = labeled.groupby("time_bucket")["reversed_toward_vwap"].mean().fillna(0).to_dict()
    return diag


def verdict_from_metrics(main_metrics: Dict[str, Any], baseline_table: pd.DataFrame, fold_table: pd.DataFrame, cfg: Dict[str, Any]) -> Tuple[str, list[str]]:
    validation = cfg.get("validation", {})
    min_events = int(validation.get("min_events_for_full_validation", 100))
    min_fold = int(validation.get("min_events_per_fold", 20))
    min_lift_pp = float(validation.get("min_hit_rate_lift_pp", 4.0))
    min_pf = float(validation.get("min_profit_factor_strong", 1.15))
    max_fold_share = float(validation.get("max_single_fold_profit_share", 0.50))
    reasons = []

    count = int(main_metrics.get("trade_count", 0))
    if count < min_events:
        reasons.append(f"Only {count} directional absorption trades; need at least {min_events} for full validation.")
        return "INSUFFICIENT_DATA", reasons
    if fold_table.empty or (fold_table["trade_count"] < min_fold).any():
        reasons.append(f"One or more folds has fewer than {min_fold} trades.")
        return "INSUFFICIENT_DATA", reasons

    baseline_only = baseline_table[baseline_table["baseline"] != "absorption_vwap"]
    best_hit = float(baseline_only["hit_rate"].max()) if not baseline_only.empty else 0.0
    lift_pp = (float(main_metrics.get("hit_rate", 0.0)) - best_hit) * 100.0
    if lift_pp < min_lift_pp:
        reasons.append(f"Hit-rate lift {lift_pp:.2f}pp is below {min_lift_pp:.2f}pp over best baseline.")
    if float(main_metrics.get("expectancy_after_cost", 0.0)) <= 0:
        reasons.append("After-cost expectancy is not positive.")
    if float(main_metrics.get("profit_factor", 0.0)) < min_pf:
        reasons.append(f"Profit factor is below strong threshold {min_pf}.")
    total_profit = float(fold_table["total_net_pnl"].sum()) if not fold_table.empty else 0.0
    if total_profit > 0:
        largest_share = float(fold_table["total_net_pnl"].clip(lower=0).max() / total_profit)
        if largest_share > max_fold_share:
            reasons.append(f"Largest fold contributes {largest_share:.1%} of net profit; max allowed is {max_fold_share:.1%}.")
    if not bool(cfg.get("_plateau_supported", False)):
        reasons.append("Stable parameter plateau support not supplied for this validation run.")

    if not reasons:
        return "VALIDATED_STRONG", ["All strong validation gates passed."]
    if float(main_metrics.get("expectancy_after_cost", 0.0)) > 0 and lift_pp > 0:
        return "VALIDATED_WEAK", reasons
    if float(main_metrics.get("expectancy_after_cost", 0.0)) < 0 and lift_pp < 0:
        return "REJECTED", reasons
    return "NOT_VALIDATED", reasons


def run_validation(df: pd.DataFrame, cfg: Dict[str, Any]) -> Dict[str, Any]:
    features = compute_absorption_features(df, cfg)
    labels = label_absorption_events(features, cfg)
    baselines = _baseline_trades(features, cfg)
    baseline_table = _baseline_summary(baselines)
    main_trades = baselines["absorption_vwap"]
    main_metrics = summarize_trades(main_trades)
    folds = int(cfg.get("validation", {}).get("folds", 5))
    fold_table = _fold_metrics(main_trades, folds)
    verdict, reasons = verdict_from_metrics(main_metrics, baseline_table, fold_table, cfg)
    diagnostics = _event_diagnostics(features, labels)
    return {
        "features": features,
        "labels": labels,
        "trades": main_trades,
        "baseline_trades": baselines,
        "baseline_table": baseline_table,
        "fold_table": fold_table,
        "metrics": main_metrics,
        "diagnostics": diagnostics,
        "validation_status": verdict,
        "validation_reasons": reasons,
    }

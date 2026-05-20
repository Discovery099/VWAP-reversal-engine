from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .data_loader import load_dataset
from .diagnostics import _add_diagnostic_buckets, build_diagnostic_trades, trade_metrics
from .features import compute_absorption_features
from .schemas import load_yaml

RECENT_SYMBOLS = ["MNQ", "RTY", "MYM", "ES", "MES", "MCL", "M2K", "MGC", "GC"]
WINDOWS = [
    ("1_month", 1, 20),
    ("3_month", 3, 30),
    ("6_month", 6, 50),
    ("12_month", 12, 75),
]


def _symbol_paths(symbol: str, root: Path) -> tuple[Path, Path]:
    return root / "data" / "raw" / f"{symbol}_5min_RTH_6year.csv", root / "configs" / f"{symbol.lower()}_5min_rth.yaml"


def _directional_mask(features: pd.DataFrame) -> pd.Series:
    return features["is_absorption_bar"].fillna(False) & features["location_vs_vwap"].isin(["above_vwap", "below_vwap"])


def _best_same_window_baseline(features: pd.DataFrame, cfg: Dict[str, Any], mask: pd.Series) -> Dict[str, Any]:
    opposite = build_diagnostic_trades(features, cfg, mask, mode="opposite", signal_name="opposite_direction")
    random = build_diagnostic_trades(features, cfg, mask, mode="random", signal_name="random_direction")
    rows = []
    for name, trades in [("opposite_direction", opposite), ("random_direction", random)]:
        metrics = trade_metrics(trades)
        rows.append({"baseline_name": name, "baseline_hit_rate": metrics["hit_rate"]})
    valid = [r for r in rows if not pd.isna(r["baseline_hit_rate"])]
    return max(valid, key=lambda r: r["baseline_hit_rate"]) if valid else {"baseline_name": None, "baseline_hit_rate": np.nan}


def _period_consistency(trades: pd.DataFrame, period: str) -> Dict[str, Any]:
    if trades.empty:
        return {
            f"positive_{period}s": 0,
            f"total_{period}s": 0,
            f"positive_{period}_pct": np.nan,
            f"largest_{period}_profit_share": np.nan,
        }
    t = trades.copy()
    if period == "week":
        t["period"] = pd.to_datetime(t["timestamp"]).dt.to_period("W").astype(str)
    elif period == "month":
        t["period"] = pd.to_datetime(t["timestamp"]).dt.to_period("M").astype(str)
    else:
        raise ValueError(period)
    totals = t.groupby("period")["net_pnl_value"].sum().astype(float)
    total_profit = float(totals.sum())
    positive = int((totals > 0).sum())
    total = int(len(totals))
    share = float(totals.clip(lower=0).max() / total_profit) if total_profit > 0 and len(totals) else np.nan
    return {
        f"positive_{period}s": positive,
        f"total_{period}s": total,
        f"positive_{period}_pct": float(positive / total) if total else np.nan,
        f"largest_{period}_profit_share": share,
    }


def _classify_recent(metrics: Dict[str, Any], sample_sufficient: bool, lift_pp: float, week_info: Dict[str, Any], month_info: Dict[str, Any]) -> tuple[str, str]:
    reasons: List[str] = []
    if not sample_sufficient:
        return "INSUFFICIENT_RECENT_DATA", "sample size below window minimum"

    expectancy = metrics.get("expectancy_after_cost", np.nan)
    pf = metrics.get("profit_factor", np.nan)
    lift_ok = lift_pp >= 4.0 if not pd.isna(lift_pp) else False
    exp_ok = expectancy > 0 if not pd.isna(expectancy) else False
    pf_active_ok = pf > 1.15 if not pd.isna(pf) else False
    pf_weak_ok = pf > 1.0 if not pd.isna(pf) else False
    week_pct = week_info.get("positive_week_pct", np.nan)
    month_pct = month_info.get("positive_month_pct", np.nan)
    week_ok = week_pct >= 0.60 if not pd.isna(week_pct) else False
    month_total = int(month_info.get("total_months", 0) or 0)
    month_ok = True if month_total < 2 else (month_pct >= 0.60 if not pd.isna(month_pct) else False)
    week_share = week_info.get("largest_week_profit_share", np.nan)
    month_share = month_info.get("largest_month_profit_share", np.nan)
    concentration_values = [v for v in [week_share, month_share if month_total >= 2 else np.nan] if not pd.isna(v)]
    concentration_ok = all(v <= 0.50 for v in concentration_values) if concentration_values else True

    if lift_ok and exp_ok and pf_active_ok and week_ok and month_ok and concentration_ok:
        return "RECENT_REGIME_ACTIVE", "recent-regime active criteria passed; not full validation"

    if exp_ok and pf_weak_ok:
        if not lift_ok:
            reasons.append("lift below +4pp")
        if not pf_active_ok:
            reasons.append("profit factor <= 1.15")
        if not week_ok:
            reasons.append("positive weeks below 60%")
        if not month_ok:
            reasons.append("positive months below 60%")
        if not concentration_ok:
            reasons.append("profit concentration above 50%")
        return "RECENT_REGIME_WEAK", "; ".join(reasons) or "positive expectancy/PF but active requirements failed"

    if (not pd.isna(lift_pp)) and lift_pp > 0 and (not exp_ok or not pf_weak_ok):
        return "WARNING_ONLY", "directional lift exists but expectancy is negative or profit factor <= 1"

    return "RECENT_REGIME_INACTIVE", "weak/negative lift and weak/negative expectancy profile"


def _empty_unavailable_row(symbol: str, window_name: str, months: int, min_trades: int) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "window_name": window_name,
        "window_months": months,
        "window_start_timestamp": None,
        "window_end_timestamp": None,
        "bars_loaded": 0,
        "signal_events": 0,
        "trades_or_labelled_outcomes": 0,
        "hit_rate": np.nan,
        "same_window_baseline_hit_rate": np.nan,
        "baseline_name": None,
        "lift_over_baseline_pp": np.nan,
        "expectancy_before_cost": np.nan,
        "expectancy_after_cost": np.nan,
        "profit_factor": np.nan,
        "max_drawdown": np.nan,
        "positive_weeks": 0,
        "total_weeks": 0,
        "positive_week_pct": np.nan,
        "positive_months": 0,
        "total_months": 0,
        "positive_month_pct": np.nan,
        "largest_week_profit_share": np.nan,
        "largest_month_profit_share": np.nan,
        "largest_week_or_month_profit_contribution": np.nan,
        "sample_size_minimum": min_trades,
        "sample_size_sufficient": False,
        "recent_regime_label": "INSUFFICIENT_RECENT_DATA",
        "comments_failure_reason": "not available: raw data or config missing",
    }


def _analyze_symbol(symbol: str, root: Path) -> List[Dict[str, Any]]:
    data_path, cfg_path = _symbol_paths(symbol, root)
    if not data_path.exists() or not cfg_path.exists():
        return [_empty_unavailable_row(symbol, name, months, minimum) for name, months, minimum in WINDOWS]

    cfg = load_yaml(cfg_path)
    df = load_dataset(data_path, cfg)
    if df.empty:
        return [_empty_unavailable_row(symbol, name, months, minimum) for name, months, minimum in WINDOWS]
    features = compute_absorption_features(df, cfg).sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    features = _add_diagnostic_buckets(features, cfg)
    latest_ts = features["timestamp"].max()
    rows: List[Dict[str, Any]] = []

    for window_name, months, minimum in WINDOWS:
        start_ts = latest_ts - pd.DateOffset(months=months)
        window_features = features[(features["timestamp"] >= start_ts) & (features["timestamp"] <= latest_ts)].reset_index(drop=True)
        signal_events = int(window_features["is_absorption_bar"].fillna(False).sum()) if not window_features.empty else 0
        mask = _directional_mask(window_features) if not window_features.empty else pd.Series(dtype=bool)
        trades = build_diagnostic_trades(window_features, cfg, mask, mode="fade", signal_name="recent_regime_absorption_vwap") if not window_features.empty else pd.DataFrame()
        metrics = trade_metrics(trades)
        baseline = _best_same_window_baseline(window_features, cfg, mask) if not window_features.empty else {"baseline_name": None, "baseline_hit_rate": np.nan}
        lift_pp = (metrics["hit_rate"] - baseline["baseline_hit_rate"]) * 100.0 if not pd.isna(metrics["hit_rate"]) and not pd.isna(baseline["baseline_hit_rate"]) else np.nan
        week_info = _period_consistency(trades, "week")
        month_info = _period_consistency(trades, "month")
        sample_sufficient = int(metrics["trades"] or 0) >= minimum
        label, comments = _classify_recent(metrics, sample_sufficient, lift_pp, week_info, month_info)
        concentration_values = [
            week_info.get("largest_week_profit_share", np.nan),
            month_info.get("largest_month_profit_share", np.nan) if int(month_info.get("total_months", 0) or 0) >= 2 else np.nan,
        ]
        concentration_values = [v for v in concentration_values if not pd.isna(v)]
        rows.append({
            "symbol": symbol,
            "window_name": window_name,
            "window_months": months,
            "window_start_timestamp": start_ts.isoformat(),
            "window_end_timestamp": latest_ts.isoformat(),
            "bars_loaded": int(len(window_features)),
            "signal_events": signal_events,
            "trades_or_labelled_outcomes": int(metrics["trades"]),
            "hit_rate": metrics["hit_rate"],
            "same_window_baseline_hit_rate": baseline["baseline_hit_rate"],
            "baseline_name": baseline["baseline_name"],
            "lift_over_baseline_pp": lift_pp,
            "expectancy_before_cost": metrics["expectancy_before_cost"],
            "expectancy_after_cost": metrics["expectancy_after_cost"],
            "profit_factor": metrics["profit_factor"],
            "max_drawdown": metrics["max_drawdown"],
            "positive_weeks": week_info["positive_weeks"],
            "total_weeks": week_info["total_weeks"],
            "positive_week_pct": week_info["positive_week_pct"],
            "positive_months": month_info["positive_months"],
            "total_months": month_info["total_months"],
            "positive_month_pct": month_info["positive_month_pct"],
            "largest_week_profit_share": week_info["largest_week_profit_share"],
            "largest_month_profit_share": month_info["largest_month_profit_share"],
            "largest_week_or_month_profit_contribution": max(concentration_values) if concentration_values else np.nan,
            "sample_size_minimum": minimum,
            "sample_size_sufficient": sample_sufficient,
            "recent_regime_label": label,
            "comments_failure_reason": comments,
        })
    return rows


def _format_pct(value: Any) -> str:
    return "" if pd.isna(value) else f"{float(value):.2%}"


def _format_num(value: Any) -> str:
    return "" if pd.isna(value) else f"{float(value):.4g}"


def _markdown_table(df: pd.DataFrame) -> str:
    cols = [
        "symbol", "window_name", "recent_regime_label", "trades_or_labelled_outcomes", "hit_rate",
        "same_window_baseline_hit_rate", "lift_over_baseline_pp", "expectancy_after_cost", "profit_factor",
        "positive_weeks", "total_weeks", "largest_week_or_month_profit_contribution", "comments_failure_reason",
    ]
    out = df[cols].copy()
    out["hit_rate"] = out["hit_rate"].map(_format_pct)
    out["same_window_baseline_hit_rate"] = out["same_window_baseline_hit_rate"].map(_format_pct)
    out["lift_over_baseline_pp"] = out["lift_over_baseline_pp"].map(_format_num)
    out["expectancy_after_cost"] = out["expectancy_after_cost"].map(_format_num)
    out["profit_factor"] = out["profit_factor"].map(_format_num)
    out["largest_week_or_month_profit_contribution"] = out["largest_week_or_month_profit_contribution"].map(_format_pct)
    rows = ["| " + " | ".join(out.columns) + " |", "| " + " | ".join(["---"] * len(out.columns)) + " |"]
    for _, row in out.iterrows():
        rows.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in out.columns) + " |")
    return "\n".join(rows)


def _summary_rows(all_results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for symbol, group in all_results.groupby("symbol", sort=False):
        available = not group["comments_failure_reason"].astype(str).str.contains("not available").all()
        counts = group["recent_regime_label"].value_counts().to_dict()
        sufficient = group[group["sample_size_sufficient"].astype(bool)]
        if not sufficient.empty:
            best = sufficient.sort_values(["recent_regime_label", "expectancy_after_cost", "profit_factor"], ascending=[True, False, False]).iloc[0]
            best_window = best["window_name"]
            best_label = best["recent_regime_label"]
            best_expectancy = best["expectancy_after_cost"]
            best_pf = best["profit_factor"]
        else:
            best_window = None
            best_label = "INSUFFICIENT_RECENT_DATA" if available else "NOT_AVAILABLE"
            best_expectancy = np.nan
            best_pf = np.nan
        if counts.get("RECENT_REGIME_ACTIVE", 0) > 0:
            posture = "standalone strategy candidate for recent regime only; not globally validated"
        elif counts.get("RECENT_REGIME_WEAK", 0) > 0:
            posture = "warning/filter only; weak positive recent research lead"
        elif counts.get("WARNING_ONLY", 0) > 0:
            posture = "warning/filter only"
        elif available and not sufficient.empty:
            posture = "inactive in recent regime"
        elif available:
            posture = "insufficient recent sample"
        else:
            posture = "not available"
        rows.append({
            "symbol": symbol,
            "available": available,
            "active_windows": counts.get("RECENT_REGIME_ACTIVE", 0),
            "weak_windows": counts.get("RECENT_REGIME_WEAK", 0),
            "warning_only_windows": counts.get("WARNING_ONLY", 0),
            "inactive_windows": counts.get("RECENT_REGIME_INACTIVE", 0),
            "insufficient_windows": counts.get("INSUFFICIENT_RECENT_DATA", 0),
            "best_window": best_window,
            "best_recent_label": best_label,
            "best_expectancy_after_cost": best_expectancy,
            "best_profit_factor": best_pf,
            "recommended_recent_posture": posture,
        })
    return pd.DataFrame(rows)


def run_recent_regime_analysis(root: str | Path = ".", symbols: List[str] | None = None) -> Dict[str, Any]:
    root = Path(root)
    symbols = symbols or RECENT_SYMBOLS
    rows: List[Dict[str, Any]] = []
    for symbol in symbols:
        rows.extend(_analyze_symbol(symbol, root))
    all_results = pd.DataFrame(rows)
    summary = _summary_rows(all_results)
    return {"all_results": all_results, "summary": summary}


def write_recent_regime_reports(result: Dict[str, Any], root: str | Path = ".") -> Path:
    root = Path(root)
    out_dir = root / "reports" / "recent_regime"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_results = result["all_results"]
    summary = result["summary"]
    all_results.to_csv(out_dir / "recent_regime_all_results.csv", index=False)
    summary.to_csv(out_dir / "recent_regime_summary.csv", index=False)

    active = sorted(all_results.loc[all_results["recent_regime_label"] == "RECENT_REGIME_ACTIVE", "symbol"].unique())
    weak = sorted(all_results.loc[all_results["recent_regime_label"] == "RECENT_REGIME_WEAK", "symbol"].unique())
    inactive = sorted(summary.loc[summary["recommended_recent_posture"] == "inactive in recent regime", "symbol"].unique())
    insufficient = sorted(summary.loc[summary["recommended_recent_posture"].isin(["insufficient recent sample", "not available"]), "symbol"].unique())

    md_lines = [
        "# Recent-Regime Analysis — Problem 0004",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This is an additional recent-regime research test only. It does not change the global NOT_VALIDATED verdict and does not create validation language.",
        "",
        "## Classification summary",
        f"- RECENT_REGIME_ACTIVE symbols/windows: {', '.join(active) if active else 'none'}",
        f"- RECENT_REGIME_WEAK symbols/windows: {', '.join(weak) if weak else 'none'}",
        f"- Inactive symbols: {', '.join(inactive) if inactive else 'none'}",
        f"- Insufficient/not available symbols: {', '.join(insufficient) if insufficient else 'none'}",
        "",
        "## Symbol summary",
        _markdown_table(all_results),
        "",
        "## Global verdict note",
        "Recent-regime testing is not full validation. Problem 0004 remains NOT_VALIDATED globally unless a separate explicit validation protocol is requested and passed.",
    ]
    md = "\n".join(md_lines)
    (out_dir / "recent_regime_summary.md").write_text(md, encoding="utf-8")
    html_body = "<html><body>" + "<pre>" + html.escape(md) + "</pre>" + "</body></html>"
    (out_dir / "recent_regime_summary.html").write_text(html_body, encoding="utf-8")

    latest = root / "reports" / "latest.html"
    latest.write_text(
        "<html><body><h1>Problem 0004 Latest Reports</h1>"
        "<ul>"
        "<li><a href='recent_regime/recent_regime_summary.html'>Recent Regime Summary</a></li>"
        "<li><a href='holdout/cross_instrument_20260520_152935/cross_instrument_summary.md'>Cross-Instrument Holdout Summary</a></li>"
        "</ul>"
        "<p>Global verdict remains NOT_VALIDATED. No live trading recommendation.</p>"
        "</body></html>",
        encoding="utf-8",
    )
    return out_dir

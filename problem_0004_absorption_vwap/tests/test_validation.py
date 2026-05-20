import pandas as pd

from research_engine.backtest import summarize_trades
from research_engine.plateau import select_plateau_centroid
from research_engine.validation import verdict_from_metrics


def test_insufficient_samples_verdict():
    baseline = pd.DataFrame({"baseline": ["absorption_vwap", "random"], "hit_rate": [0.6, 0.5], "trade_count": [10, 10], "expectancy_after_cost": [1, 0], "total_net_pnl": [10, 0], "profit_factor": [2, 1], "max_drawdown": [0, 0]})
    folds = pd.DataFrame({"fold": [1], "trade_count": [10], "hit_rate": [0.6], "expectancy_after_cost": [1], "total_net_pnl": [10], "profit_factor": [2], "max_drawdown": [0]})
    status, reasons = verdict_from_metrics({"trade_count": 10, "hit_rate": 0.6, "expectancy_after_cost": 1, "profit_factor": 2}, baseline, folds, {"validation": {"min_events_for_full_validation": 100}})
    assert status == "INSUFFICIENT_DATA"
    assert reasons


def test_plateau_rejects_isolated_spike():
    grid = {"volume_lookback": [50, 75, 100], "high_volume_percentile_threshold": [90, 95, 97.5]}
    rows = []
    for a in grid["volume_lookback"]:
        for b in grid["high_volume_percentile_threshold"]:
            rows.append({"volume_lookback": a, "high_volume_percentile_threshold": b, "expectancy_after_cost": 1 if (a, b) == (75, 95) else -1, "passes_hard_filters": (a, b) == (75, 95)})
    result = select_plateau_centroid(pd.DataFrame(rows), grid, min_neighbors=2)
    assert result["status"] == "NO_STABLE_PLATEAU"


def test_summarize_trades_empty():
    assert summarize_trades(pd.DataFrame())["trade_count"] == 0

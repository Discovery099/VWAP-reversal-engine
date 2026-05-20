import pandas as pd

from research_engine.recent_regime import _classify_recent


def test_recent_regime_classification_insufficient():
    metrics = {"trades": 10, "expectancy_after_cost": 5.0, "profit_factor": 2.0}
    label, reason = _classify_recent(metrics, False, 10.0, {"positive_week_pct": 1.0, "largest_week_profit_share": 0.2}, {"total_months": 1, "positive_month_pct": 1.0, "largest_month_profit_share": 0.2})
    assert label == "INSUFFICIENT_RECENT_DATA"
    assert "sample" in reason


def test_recent_regime_classification_warning_only():
    metrics = {"trades": 100, "expectancy_after_cost": -1.0, "profit_factor": 0.9}
    label, _ = _classify_recent(metrics, True, 5.0, {"positive_week_pct": 0.7, "largest_week_profit_share": 0.2}, {"total_months": 3, "positive_month_pct": 0.7, "largest_month_profit_share": 0.2})
    assert label == "WARNING_ONLY"


def test_recent_regime_classification_active():
    metrics = {"trades": 100, "expectancy_after_cost": 2.0, "profit_factor": 1.3}
    label, _ = _classify_recent(metrics, True, 5.0, {"positive_week_pct": 0.7, "largest_week_profit_share": 0.2}, {"total_months": 3, "positive_month_pct": 0.7, "largest_month_profit_share": 0.2})
    assert label == "RECENT_REGIME_ACTIVE"

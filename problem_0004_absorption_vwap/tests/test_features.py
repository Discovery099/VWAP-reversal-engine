import pandas as pd

from research_engine.features import compute_absorption_features
from research_engine.schemas import LABEL_COLUMNS, assert_no_label_leakage


def sample_df():
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01 09:30", periods=6, freq="min"),
        "open": [100, 101, 102, 103, 104, 105.00],
        "high": [101, 102, 103, 104, 105, 105.25],
        "low": [99, 100, 101, 102, 103, 104.75],
        "close": [101, 102, 103, 104, 105, 105.02],
        "volume": [10, 12, 11, 13, 14, 1000],
        "symbol": ["MNQ"] * 6,
        "timeframe": ["1m"] * 6,
        "session_date": ["2024-01-01"] * 6,
    })


def test_absorption_flag_triggers_known_case():
    cfg = {"features": {"atr_length": 2, "volume_lookback": 3, "volume_percentile_min_periods": 3, "high_volume_percentile_threshold": 90, "max_displacement_atr": 0.3, "near_vwap_threshold_atr": 0.1}}
    out = compute_absorption_features(sample_df(), cfg)
    assert out.loc[5, "volume_percentile"] == 100
    assert out.loc[5, "displacement_atr"] <= 0.3
    assert bool(out.loc[5, "is_absorption_bar"])


def test_labels_not_in_feature_output():
    out = compute_absorption_features(sample_df(), {"features": {"atr_length": 2, "volume_lookback": 3, "volume_percentile_min_periods": 3}})
    assert LABEL_COLUMNS.isdisjoint(out.columns)
    assert_no_label_leakage(out)

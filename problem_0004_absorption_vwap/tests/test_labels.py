import pandas as pd

from research_engine.labels import label_absorption_events


def test_forward_vwap_touch_label_correct():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01 09:30", periods=4, freq="min"),
        "open": [99, 99, 100, 101], "high": [99.5, 100.5, 101, 102], "low": [98, 98.5, 99, 100], "close": [99, 100, 101, 101.5],
        "volume": [100, 100, 100, 100], "symbol": ["MNQ"] * 4, "timeframe": ["1m"] * 4, "session_date": ["2024-01-01"] * 4,
        "session_vwap": [100, 100, 100, 100], "atr": [1, 1, 1, 1], "volume_percentile": [100, 50, 50, 50], "displacement_atr": [0.1, 0.2, 0.3, 0.4],
        "location_vs_vwap": ["below_vwap", "near_vwap", "above_vwap", "above_vwap"],
        "is_absorption_bar": [True, False, False, False], "absorption_side": ["below_vwap", "unknown", "unknown", "unknown"],
    })
    labels = label_absorption_events(df, {"features": {"reversal_horizon_bars": 3}, "costs": {"slippage_ticks": 0, "tick_size": 0, "commission_per_trade": 0}})
    assert labels.loc[0, "expected_direction"] == "up"
    assert bool(labels.loc[0, "reversed_toward_vwap"])
    assert labels.loc[0, "bars_to_vwap_touch"] == 1

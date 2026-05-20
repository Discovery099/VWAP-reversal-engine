import pandas as pd

from research_engine.diagnostics import _add_diagnostic_buckets, build_diagnostic_trades, trade_metrics


def test_diagnostic_trade_measures_vwap_touch_and_payoff():
    features = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01 09:30", periods=3, freq="5min", tz="America/New_York"),
        "open": [99.0, 99.2, 100.1],
        "high": [99.5, 100.2, 100.5],
        "low": [98.5, 99.0, 99.9],
        "close": [99.0, 100.0, 100.2],
        "volume": [1000, 500, 400],
        "symbol": ["MNQ"] * 3,
        "timeframe": ["5m"] * 3,
        "session_date": ["2024-01-01"] * 3,
        "session_vwap": [100.0, 100.0, 100.0],
        "location_vs_vwap": ["below_vwap", "near_vwap", "near_vwap"],
        "is_absorption_bar": [True, False, False],
        "volume_percentile": [99.0, 50.0, 40.0],
        "displacement_atr": [0.1, 0.2, 0.3],
        "vwap_distance_atr": [-1.0, 0.0, 0.1],
    })
    features = _add_diagnostic_buckets(features)
    trades = build_diagnostic_trades(features, {"features": {"reversal_horizon_bars": 2}, "costs": {"slippage_ticks": 0, "tick_size": 0, "point_value": 1}}, features["is_absorption_bar"])
    assert len(trades) == 1
    assert trades.loc[0, "direction"] == "long"
    assert bool(trades.loc[0, "vwap_touched"])
    assert trades.loc[0, "bars_to_vwap_touch"] == 1
    metrics = trade_metrics(trades)
    assert metrics["trades"] == 1
    assert metrics["hit_rate"] == 1.0

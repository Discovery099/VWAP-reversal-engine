import pandas as pd

from research_engine.holdout import _split_data, _monthly_consistency


def test_holdout_split_uses_chronology():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2023-12-29 15:55", "2024-01-02 09:30"]).tz_localize("America/New_York"),
        "open": [1, 1], "high": [2, 2], "low": [0, 0], "close": [1, 1], "volume": [10, 10],
        "symbol": ["MNQ", "MNQ"], "timeframe": ["5m", "5m"], "session_date": ["2023-12-29", "2024-01-02"],
    })
    train, holdout = _split_data(df, "2023-12-31 23:59:59", "2024-01-01 00:00:00")
    assert len(train) == 1
    assert len(holdout) == 1
    assert train.iloc[0]["session_date"] == "2023-12-29"
    assert holdout.iloc[0]["session_date"] == "2024-01-02"


def test_monthly_consistency_no_single_month_domination_for_loss():
    trades = pd.DataFrame({
        "timestamp": pd.to_datetime(["2024-01-02", "2024-02-02", "2024-02-03"]).tz_localize("America/New_York"),
        "net_pnl_value": [10.0, -5.0, -5.0],
    })
    out = _monthly_consistency(trades, "target_or_horizon")
    assert out["positive_months"] == 1
    assert out["total_months"] == 2

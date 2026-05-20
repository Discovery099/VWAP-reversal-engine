import pandas as pd
import pytest

from research_engine.vwap import add_session_vwap


def test_vwap_resets_by_session():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2024-01-01 09:30", "2024-01-01 09:31", "2024-01-02 09:30"]),
        "open": [9, 19, 29],
        "high": [12, 22, 32],
        "low": [9, 19, 29],
        "close": [9, 19, 29],
        "volume": [10, 30, 5],
        "symbol": ["MNQ", "MNQ", "MNQ"],
        "timeframe": ["1m", "1m", "1m"],
        "session_date": ["2024-01-01", "2024-01-01", "2024-01-02"],
    })
    out = add_session_vwap(df, {})
    tp1 = 10
    tp2 = 20
    assert out.loc[0, "session_vwap"] == pytest.approx(tp1)
    assert out.loc[1, "session_vwap"] == pytest.approx((tp1 * 10 + tp2 * 30) / 40)
    assert out.loc[2, "session_vwap"] == pytest.approx(30)


def test_zero_volume_carries_forward():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2024-01-01 09:30", "2024-01-01 09:31"]),
        "open": [9, 10], "high": [12, 13], "low": [9, 10], "close": [9, 10],
        "volume": [10, 0], "symbol": ["MNQ", "MNQ"], "timeframe": ["1m", "1m"], "session_date": ["2024-01-01", "2024-01-01"],
    })
    out = add_session_vwap(df, {"zero_volume_policy": "carry_forward"})
    assert out.loc[1, "session_vwap"] == out.loc[0, "session_vwap"]

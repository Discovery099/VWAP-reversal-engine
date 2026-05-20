import pandas as pd

from research_engine.data_loader import load_csv


def test_loader_supports_ts_event_and_defaults(tmp_path):
    path = tmp_path / "raw.csv"
    path.write_text("ts_event,open,high,low,close,volume\n2024-01-01 09:30:00,1,2,0.5,1.5,10\n", encoding="utf-8")
    df = load_csv(path, {"default_symbol": "MNQ", "default_timeframe": "1m", "session": {"timezone": None}})
    assert list(df["symbol"].unique()) == ["MNQ"]
    assert df.loc[0, "session_date"] == "2024-01-01"
    assert df.loc[0, "timeframe"] == "1m"


def test_loader_combines_date_time_with_mapping(tmp_path):
    path = tmp_path / "raw.csv"
    path.write_text("d,t,o,h,l,c,v,s\n2024-01-02,09:31:00,10,11,9,10.5,100,ES\n", encoding="utf-8")
    cfg = {
        "column_mapping": {"date": "d", "time": "t", "open": "o", "high": "h", "low": "l", "close": "c", "volume": "v", "symbol": "s"},
        "default_timeframe": "1m",
        "session": {"timezone": None},
    }
    df = load_csv(path, cfg)
    assert pd.Timestamp(df.loc[0, "timestamp"]).hour == 9
    assert df.loc[0, "symbol"] == "ES"

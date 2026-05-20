from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from .schemas import REQUIRED_COLUMNS, validate_ohlcv_schema


AUTO_COLUMN_ALIASES = {
    "timestamp": ["timestamp", "ts_event", "datetime", "date_time", "time_stamp"],
    "date": ["date", "trade_date", "session_date"],
    "time": ["time", "trade_time"],
    "open": ["open", "o"],
    "high": ["high", "h"],
    "low": ["low", "l"],
    "close": ["close", "c", "last"],
    "volume": ["volume", "vol", "qty"],
    "symbol": ["symbol", "ticker", "instrument"],
    "timeframe": ["timeframe", "interval", "bar_size"],
    "session_date": ["session_date"],
}


def _first_existing(columns: Iterable[str], aliases: List[str]) -> str | None:
    lower_to_original = {c.lower(): c for c in columns}
    for alias in aliases:
        if alias.lower() in lower_to_original:
            return lower_to_original[alias.lower()]
    return None


def _mapping_for(raw: pd.DataFrame, cfg: Dict[str, Any]) -> Dict[str, str | None]:
    configured = (cfg.get("column_mapping") or {}) if cfg else {}
    mapping: Dict[str, str | None] = {}
    for canonical, aliases in AUTO_COLUMN_ALIASES.items():
        configured_value = configured.get(canonical)
        if configured_value:
            mapping[canonical] = configured_value
        else:
            mapping[canonical] = _first_existing(raw.columns, aliases)
    return mapping


def _parse_timestamp(raw: pd.DataFrame, mapping: Dict[str, str | None], cfg: Dict[str, Any]) -> pd.Series:
    session_cfg = cfg.get("session", {}) if cfg else {}
    tz = session_cfg.get("timezone")
    if mapping.get("timestamp"):
        ts = pd.to_datetime(raw[mapping["timestamp"]], errors="coerce")
    elif mapping.get("date") and mapping.get("time"):
        ts = pd.to_datetime(raw[mapping["date"]].astype(str) + " " + raw[mapping["time"]].astype(str), errors="coerce")
    else:
        raise ValueError("No timestamp column found. Configure column_mapping.timestamp or column_mapping.date/time.")
    if ts.isna().any():
        raise ValueError(f"Unparseable timestamps found: {int(ts.isna().sum())}")
    if tz:
        if getattr(ts.dt, "tz", None) is None:
            ts = ts.dt.tz_localize(tz)
        else:
            ts = ts.dt.tz_convert(tz)
    return ts


def infer_session_date(timestamp: pd.Series, cfg: Dict[str, Any]) -> pd.Series:
    session_cfg = cfg.get("session", {}) if cfg else {}
    tz = session_cfg.get("timezone")
    ts = timestamp
    if tz and getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert(tz)
    return ts.dt.date.astype(str)


def load_csv(path: str | Path, cfg: Dict[str, Any] | None = None) -> pd.DataFrame:
    cfg = cfg or {}
    path = Path(path)
    raw = pd.read_csv(path)
    mapping = _mapping_for(raw, cfg)

    out = pd.DataFrame()
    out["timestamp"] = _parse_timestamp(raw, mapping, cfg)
    for col in ["open", "high", "low", "close", "volume"]:
        source = mapping.get(col)
        if not source:
            raise ValueError(f"No source column found for required field '{col}'")
        out[col] = pd.to_numeric(raw[source], errors="coerce")
        if out[col].isna().any():
            raise ValueError(f"Non-numeric values found in {col}: {int(out[col].isna().sum())}")

    if mapping.get("symbol"):
        out["symbol"] = raw[mapping["symbol"]].astype(str)
    else:
        out["symbol"] = str(cfg.get("default_symbol", "UNKNOWN"))

    if mapping.get("timeframe"):
        out["timeframe"] = raw[mapping["timeframe"]].astype(str)
    else:
        out["timeframe"] = str(cfg.get("default_timeframe", "1m"))

    optional_passthrough = ["vwap", "bid", "ask", "spread", "commission", "slippage", "session_id"]
    lower = {c.lower(): c for c in raw.columns}
    for col in optional_passthrough:
        if col in lower:
            out[col] = raw[lower[col]]

    if mapping.get("session_date") and mapping["session_date"] in raw.columns:
        out["session_date"] = raw[mapping["session_date"]].astype(str)
    elif "session_date" not in out.columns:
        out["session_date"] = infer_session_date(out["timestamp"], cfg)

    out["source_file"] = str(path)
    out = out.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    result = validate_ohlcv_schema(out)
    for issue in result.issues:
        if issue.level.upper() == "WARNING":
            warnings.warn(issue.message, RuntimeWarning)
    if not result.ok:
        errors = "; ".join(i.message for i in result.issues if i.level.upper() == "ERROR")
        raise ValueError(errors)
    return out[REQUIRED_COLUMNS + [c for c in out.columns if c not in REQUIRED_COLUMNS]]


def resolve_data_paths(data: str | Path) -> List[Path]:
    path = Path(data)
    if path.is_dir():
        return sorted([p for p in path.glob("*.csv") if p.is_file()])
    return [path]


def load_dataset(data: str | Path, cfg: Dict[str, Any] | None = None) -> pd.DataFrame:
    frames = [load_csv(p, cfg) for p in resolve_data_paths(data)]
    if not frames:
        raise ValueError(f"No CSV files found at {data}")
    return pd.concat(frames, ignore_index=True).sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def save_processed(df: pd.DataFrame, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path

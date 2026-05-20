from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe"]
OPTIONAL_COLUMNS = ["session_date", "session_id", "vwap", "bid", "ask", "spread", "commission", "slippage"]
LABEL_COLUMNS = {
    "expected_direction",
    "reversed_toward_vwap",
    "return_next_horizon",
    "bars_to_vwap_touch",
    "max_adverse_excursion",
    "max_favorable_excursion",
    "label_status",
}


@dataclass
class ValidationIssue:
    level: str
    message: str


@dataclass
class SchemaResult:
    ok: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def add(self, level: str, message: str) -> None:
        self.issues.append(ValidationIssue(level, message))
        if level.upper() == "ERROR":
            self.ok = False


def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def feature_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return cfg.get("features", cfg)


def validate_ohlcv_schema(df) -> SchemaResult:
    result = SchemaResult(ok=True)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        result.add("ERROR", f"Missing required columns: {missing}")
        return result

    if df.empty:
        result.add("ERROR", "DataFrame is empty")
        return result

    for col in ["open", "high", "low", "close", "volume"]:
        if not hasattr(df[col], "dtype"):
            result.add("ERROR", f"Column {col} is not a Series")
        elif not str(df[col].dtype).startswith(("float", "int")):
            result.add("ERROR", f"Column {col} must be numeric, got {df[col].dtype}")

    bad_ohlc = df[(df["high"] < df[["open", "close", "low"]].max(axis=1)) | (df["low"] > df[["open", "close", "high"]].min(axis=1))]
    if not bad_ohlc.empty:
        result.add("ERROR", f"Impossible OHLC bars found: {len(bad_ohlc)}")

    if (df["volume"] < 0).any():
        result.add("ERROR", "Negative volume values found")
    if (df["volume"] == 0).any():
        result.add("WARNING", f"Zero-volume bars found: {int((df['volume'] == 0).sum())}")

    duplicated = df.duplicated(subset=["symbol", "timestamp"], keep=False)
    if duplicated.any():
        result.add("ERROR", f"Duplicate symbol/timestamp rows found: {int(duplicated.sum())}")

    unsorted = False
    for _, group in df.groupby("symbol", sort=False):
        if not group["timestamp"].is_monotonic_increasing:
            unsorted = True
            break
    if unsorted:
        result.add("WARNING", "Rows were not monotonic by symbol/timestamp before sorting")

    return result


def assert_no_label_leakage(df) -> None:
    leaked = sorted(LABEL_COLUMNS.intersection(df.columns))
    if leaked:
        raise AssertionError(f"Label columns leaked into signal features: {leaked}")

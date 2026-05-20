from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pandas as pd


def _json_safe(obj):
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    if isinstance(obj, tuple):
        return "|".join(map(str, obj))
    return str(obj)


def make_run_dir(base_dir: str | Path, prefix: str) -> Path:
    base = Path(base_dir)
    run_id = datetime.now(timezone.utc).strftime(f"{prefix}_%Y%m%d_%H%M%S")
    run_dir = base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    latest = base.parent / "latest_run.txt" if base.name != "reports" else base / "latest_run.txt"
    latest.write_text(str(run_dir), encoding="utf-8")
    return run_dir


def markdown_summary(summary: Dict[str, Any]) -> str:
    lines = ["# Post-Absorption VWAP Reversal Report", ""]
    lines.append(f"Validation status: `{summary.get('validation_status')}`")
    lines.append("")
    lines.append("## Important limitation")
    lines.append("This engine detects a high-volume/low-displacement structural proxy consistent with possible absorption. It does not prove hidden orders and does not provide live-trading recommendations.")
    if summary.get("source_type") == "synthetic_smoke_only":
        lines.append("")
        lines.append("**Synthetic data warning:** this run used synthetic data for parser/schema smoke testing only. Do not treat the metrics as evidence of profitability.")
    lines.append("")
    lines.append("## Metrics")
    for k, v in (summary.get("metrics") or {}).items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## Verdict reasons")
    for reason in summary.get("validation_reasons", []):
        lines.append(f"- {reason}")
    lines.append("")
    lines.append("## Diagnostics")
    for k, v in (summary.get("diagnostics") or {}).items():
        lines.append(f"- `{k}`: {v}")
    return "\n".join(lines) + "\n"


def write_validation_report(result: Dict[str, Any], cfg: Dict[str, Any], run_type: str = "validate") -> Path:
    out_dir = cfg.get("reports", {}).get("output_dir", "reports/walk_forward")
    run_dir = make_run_dir(out_dir, run_type)
    summary = {
        "run_type": run_type,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_type": cfg.get("source_type", "unknown"),
        "validation_status": result["validation_status"],
        "validation_reasons": result["validation_reasons"],
        "metrics": result["metrics"],
        "diagnostics": result["diagnostics"],
        "config": cfg,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=_json_safe), encoding="utf-8")
    (run_dir / "summary.md").write_text(markdown_summary(summary), encoding="utf-8")
    if cfg.get("reports", {}).get("write_html", True):
        html = "<html><body><pre>" + markdown_summary(summary).replace("&", "&amp;").replace("<", "&lt;") + "</pre></body></html>"
        (run_dir / "report.html").write_text(html, encoding="utf-8")
    result["trades"].to_csv(run_dir / "trades.csv", index=False)
    result["labels"].to_csv(run_dir / "labels.csv", index=False)
    result["fold_table"].to_csv(run_dir / "fold_metrics.csv", index=False)
    result["baseline_table"].to_csv(run_dir / "baseline_compare.csv", index=False)
    result["features"].to_csv(run_dir / "features.csv", index=False)
    return run_dir


def write_plateau_report(result: Dict[str, Any], grid_cfg: Dict[str, Any]) -> Path:
    out_dir = grid_cfg.get("output_dir", "reports/parameter_plateaus")
    run_dir = make_run_dir(out_dir, "plateau")
    result["grid_results"].to_csv(run_dir / "grid_results.csv", index=False)
    (run_dir / "plateau.json").write_text(json.dumps(result["plateau"], indent=2, default=_json_safe), encoding="utf-8")
    md = "# Parameter Plateau Report\n\n" + f"Status: `{result['plateau'].get('status')}`\n\n```json\n{json.dumps(result['plateau'], indent=2, default=_json_safe)}\n```\n"
    (run_dir / "summary.md").write_text(md, encoding="utf-8")
    return run_dir


def latest_run_path(base: str | Path = "reports") -> Path | None:
    candidates = [Path(base) / "latest_run.txt", Path(base) / "walk_forward" / "latest_run.txt", Path(base) / "parameter_plateaus" / "latest_run.txt"]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        return None
    latest_file = max(existing, key=lambda p: p.stat().st_mtime)
    return Path(latest_file.read_text(encoding="utf-8").strip())

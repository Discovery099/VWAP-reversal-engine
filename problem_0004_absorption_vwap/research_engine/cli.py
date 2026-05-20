from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from .data_loader import load_dataset, save_processed
from .plateau import load_grid, run_plateau
from .reports import latest_run_path, write_plateau_report, write_validation_report
from .schemas import load_yaml
from .validation import run_validation


def _load_config(path: str | Path | None) -> Dict[str, Any]:
    if path is None:
        path = Path("configs/default_config.yaml")
    return load_yaml(path)


def cmd_validate(args) -> int:
    cfg = _load_config(args.config)
    df = load_dataset(args.data, cfg)
    if args.save_processed:
        save_processed(df, args.save_processed)
    result = run_validation(df, cfg)
    run_dir = write_validation_report(result, cfg, "validate")
    print(f"validation_status={result['validation_status']}")
    print(f"run_dir={run_dir}")
    for reason in result["validation_reasons"]:
        print(f"reason={reason}")
    return 0


def cmd_backtest(args) -> int:
    cfg = _load_config(args.config)
    df = load_dataset(args.data, cfg)
    result = run_validation(df, cfg)
    run_dir = write_validation_report(result, cfg, "backtest")
    print(f"validation_status={result['validation_status']}")
    print(f"trades={result['metrics']['trade_count']}")
    print(f"expectancy_after_cost={result['metrics']['expectancy_after_cost']}")
    print(f"run_dir={run_dir}")
    return 0


def cmd_plateau(args) -> int:
    cfg = _load_config(args.config)
    grid_cfg = load_grid(args.grid)
    df = load_dataset(args.data, cfg)
    result = run_plateau(df, cfg, grid_cfg)
    run_dir = write_plateau_report(result, grid_cfg)
    print(f"plateau_status={result['plateau'].get('status')}")
    print(f"run_dir={run_dir}")
    return 0


def cmd_report(args) -> int:
    if args.run == "latest":
        run_dir = latest_run_path("reports")
    else:
        run_dir = Path(args.run)
    if not run_dir or not run_dir.exists():
        print("No report run found.", file=sys.stderr)
        return 1
    summary = run_dir / "summary.md"
    if summary.exists():
        print(summary.read_text(encoding="utf-8"))
    else:
        print(f"Report directory: {run_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m research_engine", description="Post-Absorption VWAP Reversal research engine")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Run feature, label, baseline, and walk-forward validation")
    validate.add_argument("--data", required=True)
    validate.add_argument("--config", default="configs/default_config.yaml")
    validate.add_argument("--save-processed", default=None)
    validate.set_defaults(func=cmd_validate)

    backtest = sub.add_parser("backtest", help="Run event-based paper/backtest diagnostics")
    backtest.add_argument("--data", required=True)
    backtest.add_argument("--config", default="configs/default_config.yaml")
    backtest.set_defaults(func=cmd_backtest)

    plateau = sub.add_parser("plateau", help="Run parameter plateau search")
    plateau.add_argument("--data", required=True)
    plateau.add_argument("--grid", required=True)
    plateau.add_argument("--config", default="configs/default_config.yaml")
    plateau.set_defaults(func=cmd_plateau)

    report = sub.add_parser("report", help="Print an existing report summary")
    report.add_argument("--run", default="latest")
    report.set_defaults(func=cmd_report)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from .data_loader import load_dataset, save_processed
from .diagnostics import run_diagnostics, write_diagnostic_report
from .holdout import run_holdout_confirmation, write_holdout_report
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


def cmd_diagnose(args) -> int:
    cfg = _load_config(args.config)
    df = load_dataset(args.data, cfg)
    result = run_diagnostics(df, cfg, args.grid, args.plateau_dir)
    run_dir = write_diagnostic_report(result, cfg)
    summary = result["summary"]
    print(f"diagnostic_classification={summary['final_diagnostic_classification']['classification']}")
    print(f"default_expectancy_after_cost={summary['default_metrics']['expectancy_after_cost']}")
    print(f"default_profit_factor={summary['default_metrics']['profit_factor']}")
    print(f"top_candidates={len(summary['plateau_diagnostics'].get('top_candidates', []))}")
    print(f"run_dir={run_dir}")
    return 0


def cmd_holdout(args) -> int:
    cfg = _load_config(args.config)
    df = load_dataset(args.data, cfg)
    result = run_holdout_confirmation(
        df,
        cfg,
        args.grid,
        train_end=args.train_end,
        holdout_start=args.holdout_start,
        top_n=args.top_n,
    )
    run_dir = write_holdout_report(result, cfg)
    verdict = result["summary"]["final_verdict"]
    print(f"holdout_verdict={verdict['verdict']}")
    print(f"reason={verdict['reason']}")
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

    diagnose = sub.add_parser("diagnose", help="Run diagnostic decomposition without changing strategy logic")
    diagnose.add_argument("--data", required=True)
    diagnose.add_argument("--config", default="configs/default_config.yaml")
    diagnose.add_argument("--grid", default="configs/grid.yaml")
    diagnose.add_argument("--plateau-dir", default=None)
    diagnose.set_defaults(func=cmd_diagnose)

    holdout = sub.add_parser("holdout", help="Run strict training-selection / holdout confirmation")
    holdout.add_argument("--data", required=True)
    holdout.add_argument("--config", default="configs/default_config.yaml")
    holdout.add_argument("--grid", default="configs/grid.yaml")
    holdout.add_argument("--train-end", default="2023-12-31 23:59:59")
    holdout.add_argument("--holdout-start", default="2024-01-01 00:00:00")
    holdout.add_argument("--top-n", type=int, default=10)
    holdout.set_defaults(func=cmd_holdout)

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

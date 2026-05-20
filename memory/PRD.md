# PRD — Post-Absorption VWAP Reversal Engine V1

## Scope
Research-first Pine + Python engine under `/app/problem_0004_absorption_vwap/`. V1 excludes React UI, live execution, broker integrations, webhook execution, and auto-trading.

## Delivered
- Configurable CSV importer for raw futures data variants (`timestamp`, `ts_event`, date+time combine).
- Session VWAP, ATR, volume percentile, displacement/ATR, VWAP-relative location, absorption proxy detector.
- Forward-only labels for validation only.
- Event-based paper/backtest diagnostics, baselines, walk-forward validation, plateau search, diagnostics, strict holdout confirmation, and reports.
- Pine v6-compatible warning/paper module with confirmed-bar logic and manual QA notes.

## Real MNQ Validation / Diagnostics / Holdout
- Data: `/app/problem_0004_absorption_vwap/data/raw/MNQ_5min_RTH_6year.csv`
- Config: `/app/problem_0004_absorption_vwap/configs/mnq_5min_rth.yaml`
- Default full-sample verdict: `NOT_VALIDATED` due to negative after-cost expectancy and PF < 1.15.
- Diagnostics report: `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`
- Strict train/holdout report: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_150013/`

## Strict Holdout Result
- Training/selection: 2020-01-02 to 2023-12-29 (79,233 bars).
- Holdout: 2024-01-02 to 2026-03-06 (43,062 bars).
- Frozen candidates: 8 predefined diagnostic filters + 10 training-selected plateau candidates.
- Final holdout verdict: `NOT_VALIDATED`.
- Reason: no frozen training-selected candidate passed all hard gates.
- Best-looking holdout row: `default_above_vwap_shorts_only` with `fixed_horizon` exit had expectancy +43.31 and PF 1.606, but failed hard gates due only 81 trades and negative lift vs same-universe baseline.
- Preserve MNQ as filter/exit research candidate only; no validation or trading recommendation.

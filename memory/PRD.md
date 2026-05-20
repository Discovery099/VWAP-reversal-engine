# PRD — Post-Absorption VWAP Reversal Engine V1

## Scope
Research-first Pine + Python engine under `/app/problem_0004_absorption_vwap/`. V1 excludes React UI, live execution, broker integrations, webhook execution, and auto-trading.

## Delivered
- Configurable CSV importer for raw futures data variants (`timestamp`, `ts_event`, date+time combine).
- Session VWAP, ATR, volume percentile, displacement/ATR, VWAP-relative location, absorption proxy detector.
- Forward-only labels for validation only.
- Event-based paper/backtest diagnostics, baselines, walk-forward validation, plateau search, diagnostics, strict holdout confirmation, cross-instrument summaries, and reports.
- Pine v6-compatible warning/paper module with confirmed-bar logic and manual QA notes.

## Real MNQ Status
- Data: `/app/problem_0004_absorption_vwap/data/raw/MNQ_5min_RTH_6year.csv`
- Default full-sample verdict: `NOT_VALIDATED`.
- Strict train/holdout report: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_150013/`
- Final MNQ status: `NOT_VALIDATED`; preserve as filter/exit research candidate only.

## Cross-Instrument Holdout Status
- Symbols tested: RTY, MYM, ES, MCL, MGC.
- Split: train/selection 2020-01-02 to 2023-12-31; holdout 2024-01-01 to 2026-03-06.
- Reports:
  - RTY: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_151731/`
  - MYM: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152057/`
  - ES: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152416/`
  - MCL: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152618/`
  - MGC: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152912/`
  - Cross summary: `/app/problem_0004_absorption_vwap/reports/holdout/cross_instrument_20260520_152935/`
- All five additional symbols are `NOT_VALIDATED`; zero candidates passed all hard gates.
- Notable near-misses: MYM below-VWAP longs fixed-horizon positive but concentration >50%; MGC above-VWAP shorts positive but lift insufficient for fixed horizon and training support not enough for validation.
- Testing: independent report `/app/test_reports/iteration_5.json`; pytest 14 passed; lint passed.

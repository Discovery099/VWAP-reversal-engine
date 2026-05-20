# PRD — Post-Absorption VWAP Reversal Engine V1

## Scope
Research-first Pine + Python engine under `/app/problem_0004_absorption_vwap/`. V1 excludes React UI, live execution, broker integrations, webhook execution, and auto-trading.

## Final Recorded Status
- Problem 0004 is **NOT_VALIDATED** as a standalone strategy across strict cross-instrument holdout.
- Do not optimize further to force validation.
- Repositioned use case: **VWAP Absorption Reversion Warning Module**.

## Delivered
- Configurable CSV importer for raw futures data variants.
- Session VWAP, ATR, volume percentile, displacement/ATR, VWAP-relative location, absorption proxy detector.
- Forward-only labels for validation only.
- Event-based paper/backtest diagnostics, baselines, walk-forward validation, plateau search, diagnostics, strict holdout confirmation, cross-instrument summaries, and reports.
- Pine v6-compatible warning/filter module with optional paper mode disabled by default.

## Final Report
- Final report: `/app/problem_0004_absorption_vwap/FINAL_REPORT.md`
- Cross summary: `/app/problem_0004_absorption_vwap/reports/holdout/cross_instrument_20260520_152935/`
- Pine warning/filter script: `/app/problem_0004_absorption_vwap/pine/problem_0004_absorption_vwap_v1.pine`

## Pine Warning Booleans
- `absorptionWarning`
- `aboveVwapAbsorption`
- `belowVwapAbsorption`
- `nearVwapAbsorption`
- `vwapReversionCandidate`

Default mode is warning/filter only. No live trading recommendation is made.

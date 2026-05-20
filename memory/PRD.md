# PRD — Post-Absorption VWAP Reversal Engine V1

## Scope
Research-first Pine + Python engine under `/app/problem_0004_absorption_vwap/`. V1 excludes React UI, live execution, broker integrations, webhook execution, and auto-trading.

## Delivered
- Configurable CSV importer for raw futures data variants (`timestamp`, `ts_event`, date+time combine).
- Session VWAP, ATR, volume percentile, displacement/ATR, VWAP-relative location, absorption proxy detector.
- Forward-only labels for validation only.
- Event-based paper/backtest diagnostics, baselines, walk-forward validation, plateau search, and reports.
- Pine v6-compatible warning/paper module with confirmed-bar logic and manual QA notes.
- Tests and smoke data for schema/pipeline validation only.

## Validation Status
Synthetic smoke data correctly returns `INSUFFICIENT_DATA` / `NO_STABLE_PLATEAU`; no performance claims are made from synthetic data. Real futures data is needed for MNQ-first validation.

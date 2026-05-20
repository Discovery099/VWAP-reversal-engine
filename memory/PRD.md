# PRD — Post-Absorption VWAP Reversal Engine V1

## Scope
Research-first Pine + Python engine under `/app/problem_0004_absorption_vwap/`. V1 excludes React UI, live execution, broker integrations, webhook execution, and auto-trading.

## Delivered
- Configurable CSV importer for raw futures data variants (`timestamp`, `ts_event`, date+time combine).
- Session VWAP, ATR, volume percentile, displacement/ATR, VWAP-relative location, absorption proxy detector.
- Forward-only labels for validation only.
- Event-based paper/backtest diagnostics, baselines, walk-forward validation, plateau search, and reports.
- Pine v6-compatible warning/paper module with confirmed-bar logic and manual QA notes.
- Diagnostics-only decomposition command: `python -m research_engine diagnose`.

## Real MNQ Validation Run
- Data: `/app/problem_0004_absorption_vwap/data/raw/MNQ_5min_RTH_6year.csv`
- Config: `/app/problem_0004_absorption_vwap/configs/mnq_5min_rth.yaml`
- Bars: 122,295; date range 2020-01-02 09:30 ET to 2026-03-06 15:55 ET.
- Default absorption event count: 825; directional trades: 558.
- Default validation verdict: `NOT_VALIDATED` due to negative after-cost expectancy and PF < 1.15.

## MNQ Diagnostic Decomposition
- Report: `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`
- Default payoff leak: high hit rate but average loser (~-169.44) is much larger than average winner (~51.68), win/loss ratio ~0.305.
- Default current exit expectancy: -0.3233 after cost; pure fixed-horizon diagnostic expectancy: +4.4892, but not validated due fold instability and not a new strategy.
- Above/short side is positive; below/long side is negative.
- 204 stable parameter-region candidates passed diagnostic fold gates in evaluated set, but this remains diagnostic-only and needs separate forward/OOS confirmation before validation language.
- Diagnostic classification: `standalone strategy candidate`, not `VALIDATED`.

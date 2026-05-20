# PRD — Post-Absorption VWAP Reversal Engine V1

## Final Recorded Status
- Problem 0004 remains **NOT_VALIDATED** as a standalone strategy across strict cross-instrument holdout.
- Do not optimize further to force validation.
- Repositioned use case: **VWAP Absorption Reversion Warning Module**.

## Recent-Regime Add-on Analysis
- Purpose: answer whether the current signal appears active in recent 1-month, 3-month, 6-month, and 12-month regimes.
- This add-on does **not** modify the original specification, final report, strategy logic, or global verdict.
- Reports:
  - `/app/problem_0004_absorption_vwap/reports/recent_regime/recent_regime_all_results.csv`
  - `/app/problem_0004_absorption_vwap/reports/recent_regime/recent_regime_summary.csv`
  - `/app/problem_0004_absorption_vwap/reports/recent_regime/recent_regime_summary.md`
  - `/app/problem_0004_absorption_vwap/reports/recent_regime/recent_regime_summary.html`
  - `/app/problem_0004_absorption_vwap/reports/latest.html`
- Results: 0 RECENT_REGIME_ACTIVE, 0 RECENT_REGIME_WEAK, 10 WARNING_ONLY, 26 INSUFFICIENT_RECENT_DATA.
- Available symbols: MNQ, RTY, MYM, ES, MCL, MGC.
- Not available: MES, M2K, GC.
- Recent posture: warning/filter only; global verdict remains NOT_VALIDATED.

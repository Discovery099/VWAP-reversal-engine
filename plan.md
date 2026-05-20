# plan.md — Post-Absorption VWAP Reversal Engine (V1) — Updated (Post Cross-Instrument Holdout)

## 1. Objectives
- Build a **research-first** Pine + Python engine under `/app/problem_0004_absorption_vwap/` to test the hypothesis: **high volume + low displacement ⇒ possible absorption proxy**, interpreted via **session VWAP context**.
- Deliver a **reproducible CLI workflow** that:
  - imports raw futures CSVs with **configurable column mapping** (incl. `timestamp` vs `ts_event`, and `date+time` combination),
  - computes **session VWAP** (reset by configurable session inference; default calendar date in timestamp timezone),
  - detects **absorption proxy** events (high volume percentile + low displacement/ATR),
  - classifies **above/below/near VWAP** context,
  - generates **forward-only labels** for evaluation (**no lookahead**),
  - runs **walk-forward validation** with event-count gates,
  - compares against **baselines after costs**,
  - runs **sensitivity + parameter plateau search** with stable-neighborhood rejection,
  - runs **diagnostic decomposition** (payoff leak, bucket breakdowns),
  - runs **strict train/holdout confirmation** (true leakage control),
  - outputs **JSON + Markdown + CSV** reports (+ HTML when enabled), including cross-instrument support.
- Enforce validation discipline:
  - **no lookahead**, labels used **only** for evaluation,
  - no repainting claims in Pine; **confirmed-bar only**,
  - no forced optimization, no trading recommendation,
  - honest verdicts: `VALIDATED_STRONG / VALIDATED_WEAK / NOT_VALIDATED / REJECTED / INSUFFICIENT_DATA`.

**Updated objective (based on MNQ + cross-instrument results):**
- The absorption/VWAP concept appears **directionally meaningful in places**, but is **not validated** under strict holdout across MNQ/RTY/MYM/ES/MCL/MGC.
- Preserve the project as:
  - a **VWAP-reversion warning module** and
  - a **filter/exit research candidate generator**,
  until a pre-registered hypothesis passes strict holdout gates and replicates across instruments.

**Current status:**
- V1 core implementation is complete and independently verified.
  - Core verification report: `/app/test_reports/iteration_1.json`.
- **MNQ real-data pipeline completed:** default parameters = `NOT_VALIDATED`.
  - MNQ verification report: `/app/test_reports/iteration_2.json`.
- **MNQ diagnostic decomposition completed** (no strategy changes; diagnosis only).
  - Diagnostic report: `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`
  - Diagnostics verification report: `/app/test_reports/iteration_3.json`.
- **Strict true train/holdout confirmation completed on MNQ** (no data reuse for selection).
  - Holdout report: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_150013/`
  - Holdout verification report: `/app/test_reports/iteration_4.json`.
- **Cross-instrument strict holdout confirmation completed** for RTY/MYM/ES/MCL/MGC.
  - Cross-instrument verification report: `/app/test_reports/iteration_5.json`.
- Test status: `pytest -q` **14 passed**, lint passed.
- Synthetic data remains **smoke-only** (schema/pipeline validation only) and is not used for performance claims.

## 2. Implementation Steps

### Phase 1 — Core POC (isolation, must work before scaling) ✅ Completed
User stories:
1. Import a raw futures CSV with arbitrary column names via a YAML mapping.
2. Compute session VWAP with correct daily resets.
3. Flag absorption proxy bars (high volume + low displacement) deterministically.
4. Classify absorption bars as above/below/near VWAP without repaint.
4. Generate forward-only labels (VWAP-touch / return) without using future info in features.

Delivered in repo `/app/problem_0004_absorption_vwap/`:
- Repo skeleton + packaging.
- Data contract + schema validation.
- CSV importer (configurable mapping):
  - Supports `timestamp` or `ts_event`.
  - Supports combining separate `date` + `time` via explicit mapping.
  - Supports missing `symbol/timeframe` via defaults.
  - Robustness upgrades for real data:
    - Mixed timezone offsets normalized via `utc=True` parse.
    - Missing symbol values filled with `default_symbol`.
- Session inference: default calendar date (timezone configurable).
- VWAP module with session resets and zero-volume handling.
- Feature engine: ATR, displacement/ATR, rolling volume percentile, VWAP distance/ATR, VWAP-relative location.
- Forward-only labels and event-based paper-backtest conventions.

### Phase 2 — V1 Research Pipeline (validation, baselines, reporting, plateau search) ✅ Completed
User stories:
1. Validate one or many instruments and get a cross-instrument summary.
2. Compare absorption-VWAP logic vs multiple baselines after costs.
3. Run walk-forward folds with event-count gates and inspect fold consistency.
4. Run plateau search and avoid isolated parameter spikes.
5. Export JSON/MD/CSV (+HTML) reports.

Delivered:
- CLI: `validate`, `backtest`, `plateau`, `report --run latest`.
- Baselines (same mechanics/cost model): RSI reversal, high-volume-only, low-displacement-only, VWAP fade, random direction.
- Walk-forward fold metrics and verdict logic.
- Plateau search with stability detection.

### Phase 3 — Pine v6 module (conservative, confirmed bars, warnings) ✅ Completed
Delivered:
- Pine v6 script: `pine/problem_0004_absorption_vwap_v1.pine`.
- Manual QA checklist: `tests/test_pine_checklist.md`.

### Phase 4 — Tests + smoke validation ✅ Completed (and independently verified)
Delivered:
- Tests expanded to cover core, diagnostics, and holdout.
- Current status:
  - `pytest -q`: **14 passed**.
  - Independent verification reports:
    - Core V1: `/app/test_reports/iteration_1.json`
    - MNQ run: `/app/test_reports/iteration_2.json`
    - Diagnostics: `/app/test_reports/iteration_3.json`
    - MNQ Holdout: `/app/test_reports/iteration_4.json`
    - Cross-instrument holdout: `/app/test_reports/iteration_5.json`

### Phase 5 — Real-data MNQ Validation (5-min RTH, ~6 years) ✅ Completed
- Data: `/app/problem_0004_absorption_vwap/data/raw/MNQ_5min_RTH_6year.csv`
- Config: `/app/problem_0004_absorption_vwap/configs/mnq_5min_rth.yaml`
- Default parameters verdict: `NOT_VALIDATED`.

### Phase 6 — MNQ Diagnostic Decomposition (root-cause analysis, no strategy changes) ✅ Completed
Purpose:
- Explain why **directional hit rate is high** but **expectancy/PF are weak**.

Key findings (default parameters; unchanged costs):
- Payoff asymmetry: average loser substantially larger than average winner.
- Not-touch tail risk dominates losses.
- Above-VWAP shorts materially healthier than below-VWAP longs.
- “Last 30 minutes” bucket is structurally weak on MNQ.
- Some strength buckets (e.g., displacement 0.10–0.20, VWAP distance 1–2 ATR) look better.

Delivered:
- Diagnostics module: `research_engine/diagnostics.py`
- CLI: `python -m research_engine diagnose ...`
- Report: `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`

### Phase 7 — Strict True Train/Holdout Confirmation (leakage-controlled) ✅ Completed
Purpose:
- Prevent selection/validation leakage by **selecting candidates only on training**, freezing them, then evaluating only on holdout.

Protocol used:
- Training/selection: 2020-01-02 → 2023-12-31 (actual last bar varies by instrument)
- Holdout: 2024-01-01 → 2026-03-06 (actual first bar varies by instrument)
- Frozen candidates evaluated (frozen):
  - `target_or_horizon` (current)
  - `fixed_horizon` (diagnostic style)

Delivered:
- Holdout module: `research_engine/holdout.py`
- CLI: `python -m research_engine holdout ...`

**MNQ holdout status:**
- Report: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_150013/`
- Final verdict: `NOT_VALIDATED`.

### Phase 8 — Cross-Instrument Strict Holdout Replication ✅ Completed
Purpose:
- Test whether any training-selected candidates survive strict holdout **across instruments**.

Enhancements (methodology correctness):
- Updated diagnostic session bucket logic to use configured `session.rth_start` / `session.rth_end` so “last 30 minutes” filters work correctly for markets with non-09:30 opens (MCL/MGC).

Data/configs:
- Downloaded raw files to `data/raw/`:
  - `RTY_5min_RTH_6year.csv`, `MYM_5min_RTH_6year.csv`, `ES_5min_RTH_6year.csv`, `MCL_5min_RTH_6year.csv`, `MGC_5min_RTH_6year.csv`
- Created per-symbol configs with `ts_event` mapping and standard tick/point values:
  - RTY: `/app/problem_0004_absorption_vwap/configs/rty_5min_rth.yaml`
  - MYM: `/app/problem_0004_absorption_vwap/configs/mym_5min_rth.yaml`
  - ES: `/app/problem_0004_absorption_vwap/configs/es_5min_rth.yaml`
  - MCL: `/app/problem_0004_absorption_vwap/configs/mcl_5min_rth.yaml`
  - MGC: `/app/problem_0004_absorption_vwap/configs/mgc_5min_rth.yaml`

Session configs:
- RTY/MYM/ES: 09:30–16:00
- MCL: 09:00–14:30
- MGC: 08:20–13:30

Holdout reports:
- RTY: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_151731/`
- MYM: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152057/`
- ES: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152416/`
- MCL: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152618/`
- MGC: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152912/`

Cross-instrument summary:
- Directory: `/app/problem_0004_absorption_vwap/reports/holdout/cross_instrument_20260520_152935/`
  - `cross_instrument_all_candidates.csv`
  - `cross_instrument_best_summary.csv`
  - `cross_instrument_summary.md`

Results:
- All 5 additional symbols final verdict: `NOT_VALIDATED`.
- Zero candidates passed all hard gates in holdout.

Near-miss examples (holdout “best rows” by instrument; still NOT_VALIDATED):
- RTY: `default_above_vwap_shorts_only / fixed_horizon` — 85 trades, lift +7.06pp, PF 1.196, but low positive months (13/26) + extreme concentration (75%).
- MYM: `default_below_vwap_longs_only / fixed_horizon` — 103 trades, lift +4.85pp, PF 1.359, but concentration ~51% and lacks stable training support required.
- ES: `train_plateau_05 / target_or_horizon` — 57 trades (fails min trades) and high concentration.
- MCL: `train_plateau_07 / target_or_horizon` — 153 trades but expectancy negative and PF < 1.15.
- MGC: `default_above_vwap_shorts_only / fixed_horizon` — 138 trades, PF 1.494, but lift < 4pp and not training-stable.

## 3. Next Actions
1. **Preserve all instruments as research candidates; do not use validation language:**
   - Current posture is **research-only**: warning module + hypothesis generator.

2. **Pre-registered hypothesis iteration (no forced optimization):**
   Based strictly on diagnostics + holdout failures, propose a small number of *pre-registered* hypotheses to test next (each as a new hypothesis requiring re-validation):
   - Side/regime split: evaluate above-VWAP shorts separately from below-VWAP longs.
   - Tail-risk characterization: identify conditions correlated with “not-touch” large losses.
   - Session hypothesis: exclude last 30 minutes (must be re-selected on training, then holdout).
   - Strength-bucket hypothesis: displacement 0.10–0.20 and VWAP distance 1–2 ATR; avoid extreme 99–100 volume bucket.

3. **Improve confirmation methodology (still not changing strategy logic):**
   - Add a **rolling walk-forward selection** protocol:
     - select exactly one candidate on each training segment,
     - evaluate on the next segment,
     - accumulate performance without reusing validation data for selection.
   - Add cross-instrument “pre-registration”: select candidate rules on one instrument’s training, test on other instruments’ holdout.

4. **Cost sensitivity (explicitly later, after structural stability):**
   - Re-run strict holdout with more realistic costs (commission + spread + slippage per instrument).

5. **Data quality notes:**
   - Many files contain small counts of zero-volume bars; VWAP uses `carry_forward` for those bars.
   - Session bucket logic now uses configured RTH windows (important for MCL/MGC).

## 4. Success Criteria
- Repo remains reproducible and disciplined:
  - `validate`, `backtest`, `plateau`, `diagnose`, `holdout`, `report`, `pytest` all run.
  - No lookahead / label leakage.
  - No live execution or trading recommendations.

- For any claim of validation (hard rule, holdout-based):
  - ≥100 holdout trades,
  - ≥+4pp lift over best baseline in the same subset/universe,
  - positive after-cost expectancy,
  - profit factor > 1.15,
  - acceptable drawdown,
  - ≥60% positive months (or equivalent consistency) with no single month dominating profit,
  - stable out-of-sample plateau support,
  - plus cross-instrument replication.

## 5. Artifacts (for traceability)

### MNQ
- Data: `/app/problem_0004_absorption_vwap/data/raw/MNQ_5min_RTH_6year.csv`
- Config: `/app/problem_0004_absorption_vwap/configs/mnq_5min_rth.yaml`
- Validate report: `/app/problem_0004_absorption_vwap/reports/walk_forward/validate_20260520_141142/`
- Backtest report: `/app/problem_0004_absorption_vwap/reports/walk_forward/backtest_20260520_141308/`
- Plateau report: `/app/problem_0004_absorption_vwap/reports/parameter_plateaus/plateau_20260520_141004/`
- Diagnostic report: `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`
- Holdout report: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_150013/`

### Cross-instrument holdout
- Holdout reports:
  - RTY: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_151731/`
  - MYM: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152057/`
  - ES: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152416/`
  - MCL: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152618/`
  - MGC: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_152912/`
- Cross summary directory:
  - `/app/problem_0004_absorption_vwap/reports/holdout/cross_instrument_20260520_152935/`

### Independent test reports
- Core V1: `/app/test_reports/iteration_1.json`
- MNQ run: `/app/test_reports/iteration_2.json`
- Diagnostics: `/app/test_reports/iteration_3.json`
- MNQ Holdout: `/app/test_reports/iteration_4.json`
- Cross-instrument holdout: `/app/test_reports/iteration_5.json`

# plan.md — Post-Absorption VWAP Reversal Engine (V1) — Updated (Post MNQ Holdout)

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

**Updated objective (based on MNQ results):**
- MNQ is **directionally meaningful** (hit-rate lift) but **not validated** under strict confirmation. Preserve the project as a **filter/exit research candidate and VWAP-reversion warning module** until holdout gates can be met and cross-instrument replication succeeds.

**Current status:**
- V1 core implementation is complete and independently verified.
  - Core verification report: `/app/test_reports/iteration_1.json`.
- **Real-data MNQ run completed (5-min RTH, ~6 years):** default parameters = `NOT_VALIDATED`.
  - MNQ verification report: `/app/test_reports/iteration_2.json`.
- **MNQ diagnostic decomposition completed** (no strategy changes; diagnosis only).
  - Diagnostic report: `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`
  - Diagnostics verification report: `/app/test_reports/iteration_3.json`.
- **Strict true train/holdout confirmation completed** (no data reuse for selection).
  - Holdout report: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_150013/`
  - Holdout verification report: `/app/test_reports/iteration_4.json`.
- Test status: `pytest -q` **14 passed**, lint passed.
- Synthetic data remains **smoke-only** (schema/pipeline validation only) and is not used for performance claims.

## 2. Implementation Steps

### Phase 1 — Core POC (isolation, must work before scaling) ✅ Completed
User stories:
1. Import a raw futures CSV with arbitrary column names via a YAML mapping.
2. Compute session VWAP with correct daily resets.
3. Flag absorption proxy bars (high volume + low displacement) deterministically.
4. Classify absorption bars as above/below/near VWAP without repaint.
5. Generate forward-only labels (VWAP-touch / return) without using future info in features.

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
    - Holdout: `/app/test_reports/iteration_4.json`

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
- Last 30 minutes is structurally weak.
- Some strength buckets (e.g., displacement 0.10–0.20, VWAP distance 1–2 ATR) look better.

Delivered:
- Diagnostics module: `research_engine/diagnostics.py`
- CLI: `python -m research_engine diagnose ...`
- Report: `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`

### Phase 7 — Strict True Train/Holdout Confirmation (leakage-controlled) ✅ Completed
Purpose:
- Prevent selection/validation leakage by **selecting candidates only on training**, freezing them, then evaluating only on holdout.

Protocol used:
- Training/selection: 2020-01-02 → 2023-12-31 (actual last bar: 2023-12-29 15:55 ET)
- Holdout: 2024-01-01 → 2026-03-06 (actual first bar: 2024-01-02 09:30 ET)
- Training bars: **79,233**; holdout bars: **43,062**.

Training-only selection:
- Plateau selection on training only: `STABLE_PLATEAU_FOUND` with centroid:
  - `volume_lookback=150, high_volume_percentile_threshold=95, atr_length=40, max_displacement_atr=0.3, near_vwap_threshold_atr=0.25, reversal_horizon_bars=15`
  - `stable_count=2190`.

Frozen candidates:
- 8 predefined protocol filters + 10 training plateau top candidates.

Holdout evaluation:
- Exit styles evaluated (frozen):
  - `target_or_horizon` (current)
  - `fixed_horizon` (diagnostic style)
- Final holdout verdict: **`NOT_VALIDATED`**.
  - Reason: no frozen candidate passed all strict holdout hard gates.

Notable holdout observations (examples):
- `default_above_vwap_shorts_only` showed positive expectancy and PF, but failed hard gates (e.g., trades < 100; lift issues; month-domination / positive-month threshold; and not plateau-stable).
- Several candidates had too few trades in holdout despite good metrics.
- Some training plateau candidates had >100 trades and positive expectancy but failed lift vs same-universe baseline.

Delivered:
- Holdout module: `research_engine/holdout.py`
- CLI: `python -m research_engine holdout ...`
- Report: `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_150013/`

## 3. Next Actions
1. **Do not reject the project; preserve MNQ as research candidate (no validation language):**
   - Treat the current absorption/VWAP logic as a **directional/structural warning module** and as a source of **filters/exits hypotheses**.

2. **Pre-registered hypothesis iteration (no forced optimization):**
   Based strictly on diagnostics + holdout failures, propose a small number of *pre-registered* hypotheses to test next (each as a new hypothesis requiring re-validation):
   - Separate regime evaluation: above-VWAP shorts vs below-VWAP longs.
   - Tail-risk controls: characterize and potentially filter conditions leading to non-touch losses.
   - Session filter hypothesis: avoid last 30 minutes (must confirm on training, then holdout).
   - Strength bucket hypothesis: displacement 0.10–0.20 and VWAP distance 1–2 ATR; avoid extreme 99–100 volume bucket.

3. **Improve the strict confirmation protocol (methodology, not strategy):**
   - Add a “training-time model selection” pass that selects a *single* candidate per training window and evaluates it on the next window (rolling walk-forward selection), rather than picking from the full-period training set once.
   - Keep the same hard gates and baseline discipline.

4. **Cross-instrument replication (required before any stronger claim):**
   - Run the same pipeline (validate/diagnose/holdout) on RTY, MYM, MCL, M2K, ES, MES, MGC if available.
   - Require the same hard gates to avoid MNQ-only overfit.

5. **Cost sensitivity (explicitly later, after structure stabilizes):**
   - Evaluate robustness to more realistic commissions/slippage/spread.

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

## 5. MNQ Artifacts (for traceability)
- Data:
  - `/app/problem_0004_absorption_vwap/data/raw/MNQ_5min_RTH_6year.csv`
- Config:
  - `/app/problem_0004_absorption_vwap/configs/mnq_5min_rth.yaml`
- Validate report:
  - `/app/problem_0004_absorption_vwap/reports/walk_forward/validate_20260520_141142/`
- Backtest report:
  - `/app/problem_0004_absorption_vwap/reports/walk_forward/backtest_20260520_141308/`
- Plateau report:
  - `/app/problem_0004_absorption_vwap/reports/parameter_plateaus/plateau_20260520_141004/`
- Diagnostic report:
  - `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`
- Holdout report:
  - `/app/problem_0004_absorption_vwap/reports/holdout/holdout_20260520_150013/`
- Independent test reports:
  - Core V1: `/app/test_reports/iteration_1.json`
  - MNQ run: `/app/test_reports/iteration_2.json`
  - Diagnostics: `/app/test_reports/iteration_3.json`
  - Holdout: `/app/test_reports/iteration_4.json`

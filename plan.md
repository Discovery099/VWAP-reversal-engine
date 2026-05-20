# plan.md — Post-Absorption VWAP Reversal Engine (V1) — Updated (Post MNQ Diagnostics)

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
  - outputs **JSON + Markdown + CSV** reports (+ HTML when enabled), including cross-instrument support.
- Enforce validation discipline:
  - **no lookahead**, labels used **only** for evaluation,
  - no repainting claims in Pine; **confirmed-bar only**,
  - no forced optimization, no trading recommendation,
  - honest verdicts: `VALIDATED_STRONG / VALIDATED_WEAK / NOT_VALIDATED / REJECTED / INSUFFICIENT_DATA`.

**Current status:**
- V1 core implementation is complete and independently verified:
  - `testing_agent_v3` passed repo structure, CLI commands, reporting, no label leakage, Pine structure/safety.
  - Report: `/app/test_reports/iteration_1.json`.
- **Real-data MNQ run completed (5-min RTH, ~6 years):**
  - Data: `/app/problem_0004_absorption_vwap/data/raw/MNQ_5min_RTH_6year.csv`
  - Config: `/app/problem_0004_absorption_vwap/configs/mnq_5min_rth.yaml`
  - Default parameters verdict: **NOT_VALIDATED** (negative after-cost expectancy; PF < strong threshold; fold inconsistency) despite **directional hit-rate lift**.
  - Report: `/app/test_reports/iteration_2.json`.
- **MNQ diagnostic decomposition completed (no core-strategy changes):**
  - Added diagnostics-only module and CLI: `python -m research_engine diagnose`
  - Diagnostic report: `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`
  - `pytest -q`: **12 passed**, lint passed, diagnostics verified by testing agent: `/app/test_reports/iteration_3.json`.
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
- Repo skeleton + packaging:
  - `research_engine/(__init__.py, __main__.py, cli.py, data_loader.py, schemas.py, vwap.py, features.py, signal_logic.py, labels.py, backtest.py, validation.py, plateau.py, reports.py)`
  - `configs/default_config.yaml`, `configs/grid.yaml`
  - `data/raw/ data/processed/ data/examples/ reports/* pine/ tests/`
- Data contract + schema validation:
  - Canonical columns: `timestamp, open, high, low, close, volume, symbol, timeframe`.
  - Optional passthrough: `session_date, session_id, vwap, bid, ask, spread, commission, slippage`.
- CSV importer (configurable mapping):
  - Supports `timestamp` or `ts_event`.
  - Supports combining separate `date` + `time` via explicit mapping.
  - Supports missing `symbol/timeframe` via defaults.
  - Robustness upgrades for real data:
    - Mixed timezone offsets normalized via `utc=True` parse.
    - Missing symbol values filled with `default_symbol`.
- Session inference:
  - Default: `session_date = calendar date in timestamp timezone`.
  - Timezone configurable via YAML.
- VWAP module:
  - typical price = `(H+L+C)/3`.
  - Reset by `symbol + session_date`.
  - Zero-volume policy implemented (`carry_forward` default).
- Feature engine:
  - ATR, displacement/ATR, rolling volume percentile, VWAP distance/ATR.
  - VWAP-relative location classification.
  - Absorption proxy flag + block reasons.
- Forward-only labels:
  - For absorption events only: expected direction (fade), VWAP-touch/return-style outcomes.
  - Costs-aware thresholding for label “movement vs noise”.

### Phase 2 — V1 Research Pipeline (validation, baselines, reporting, plateau search) ✅ Completed
User stories:
1. Validate one or many instruments and get a cross-instrument summary.
2. Compare absorption-VWAP logic vs multiple baselines after costs.
3. Run walk-forward folds with event-count gates and inspect fold consistency.
4. Run plateau search and avoid isolated parameter spikes.
5. Export JSON/MD/CSV (+HTML) reports and re-open the latest run.

Delivered:
- CLI orchestration (`cli.py`):
  - `validate`, `backtest`, `plateau`, `report --run latest`.
  - Multi-file/folder input via loader (folder reads `*.csv`).
- Baselines (same mechanics/cost model):
  - RSI reversal.
  - High-volume-only.
  - Low-displacement-only.
  - VWAP fade without absorption filter.
  - Random direction on absorption bars (seeded).
- Walk-forward:
  - Fold metrics table emitted.
  - Validation gates: `>=100` events overall and `>=20` per fold, else `INSUFFICIENT_DATA`.
- Verdict logic:
  - Lift threshold vs best baseline, after-cost expectancy, profit factor threshold, fold consistency checks.
  - Explicit “plateau support required” reason when plateau support is not present.
- Reporting (`reports.py`):
  - Per-run directory with `summary.json`, `summary.md`, `trades.csv`, `labels.csv`, `features.csv`, `fold_metrics.csv`, `baseline_compare.csv`, optional `report.html`.
- Plateau search (`plateau.py`):
  - Grid from `configs/grid.yaml`.
  - Stable-neighborhood rejection via neighbor-count criterion.
  - Performance optimizations to handle larger real datasets without changing strategy rules.

### Phase 3 — Pine v6 module (conservative, confirmed bars, warnings) ✅ Completed
User stories:
1. Visualize session VWAP and absorption proxy markers on confirmed bars.
2. Enable/disable fade candidates above/below VWAP; classify near-VWAP separately.
3. View debug info to compare with Python.
4. Optionally run paper strategy (TradingView only), not live execution.
5. Follow QA notes to validate Pine vs Python.

Delivered:
- `pine/problem_0004_absorption_vwap_v1.pine` with confirmed-bar logic, session VWAP, markers, alerts, optional paper strategy, debug table, and explicit limitations.
- Manual checklist: `tests/test_pine_checklist.md`.

### Phase 4 — Tests + smoke validation ✅ Completed (and independently verified)
User stories:
1. Run `pytest` and confirm VWAP resets and labels are correct.
2. Detect schema violations early.
3. Ensure labels never leak into features.
4. Ensure verdict logic returns `INSUFFICIENT_DATA` correctly.
5. Ensure plateau selection rejects isolated spikes.

Delivered:
- Tests implemented and passing.
- Updated status:
  - `pytest -q`: **12 passed**.
  - Independent verification reports:
    - Core V1: `/app/test_reports/iteration_1.json`
    - MNQ run: `/app/test_reports/iteration_2.json`
    - Diagnostics: `/app/test_reports/iteration_3.json`

### Phase 5 — Real-data MNQ Validation (5-min RTH, ~6 years) ✅ Completed
User stories:
1. Load real MNQ futures data via configurable mapping and timezone-aware session inference.
2. Run validate/backtest/plateau/report with no strategy logic changes.
3. Produce an honest verdict against gates and baselines after costs.

Delivered / executed:
- Data placed under: `data/raw/MNQ_5min_RTH_6year.csv`.
- MNQ-specific config created: `configs/mnq_5min_rth.yaml`.
- Commands run successfully:
  - `python -m research_engine validate ...`
  - `python -m research_engine backtest ...`
  - `python -m research_engine plateau ...`
  - `python -m research_engine report --run latest`
- Outcome summary (default config):
  - Directional hit rate: **~76.34%**, lift over best global baseline: **~+5.02pp**, but **after-cost expectancy negative** and **PF ~0.992**.
  - Fold inconsistency (3/5 positive folds).
  - Plateau search found stable in-sample regions (stable_count=1621), which is *not* itself validation.

### Phase 6 — MNQ Diagnostic Decomposition (root-cause analysis, no strategy changes) ✅ Completed
Purpose:
- Explain **why directional hit rate is high but expectancy/PF are weak** under the current fixed entry + VWAP-touch-or-horizon exit.
- Produce decompositions by VWAP location, direction, session bucket, strength buckets, horizon sensitivity, and plateau candidate screening.

Delivered:
- New diagnostics module: `research_engine/diagnostics.py`.
- New CLI command:
  - `python -m research_engine diagnose --data ... --config ... --grid configs/grid.yaml --plateau-dir <plateau_run_dir>`
- Diagnostic report generated:
  - `/app/problem_0004_absorption_vwap/reports/diagnostics/diagnostic_20260520_143421/`
- Key MNQ diagnostic findings (default parameters; unchanged costs):
  - **Payoff asymmetry leak:** avg winner **~+51.68** vs avg loser **~-169.44** (win/loss ratio **~0.305**).
  - **Expectancy leak:** expectancy before cost **~+0.6767**, after cost **~-0.3233**; cost drag **~1.0** per trade.
  - **VWAP touch behavior:** VWAP touched **~71.7%**;
    - touched trades have strongly positive average,
    - not-touched trades have very negative average (fat-tail loss driver).
  - **Location/direction split:**
    - Above VWAP / shorts: positive expectancy and PF > 1.
    - Below VWAP / longs: negative expectancy and PF < 1.
  - **Session regime:** last 30 minutes is severely negative; first 30 minutes slightly positive; afternoon strongest.
  - **Strength buckets:** displacement 0.10–0.20 ATR and VWAP distance 1–2 ATR are materially better than other buckets.
  - **Horizon sensitivity:** some horizons turn positive, but default fold stability remains insufficient for validation.
  - **Plateau diagnostics:** stable_count=1621; evaluated top 300 stable candidates; **204** pass the diagnostic fold gates in the evaluated set.
    - Top 10 candidates exported: `top_plateau_candidates.csv`.
- Diagnostic classification (explicitly not validation language):
  - **“standalone strategy candidate”** (meaning: warrants further OOS confirmation work), while default remains `NOT_VALIDATED`.

## 3. Next Actions
1. **Convert diagnostics into disciplined next experiments (no forced optimization):**
   - Freeze the current default as “baseline hypothesis.”
   - Use diagnostics to propose *pre-registered* hypotheses for filters/exits (e.g., avoid last 30m, separate above vs below regimes) and re-run full walk-forward validation.
   - Maintain strict rule: no new “VALIDATED” label unless all gates pass.

2. **Plateau OOS confirmation protocol (required before any validation language):**
   - Take top plateau candidates and run a true walk-forward / holdout protocol (e.g., reserve last N years as final holdout, or rolling walk-forward where parameters are selected only on training windows).
   - Confirm “stable out-of-sample plateau support” (not just in-sample stability).

3. **Entry/exit leak isolation (research only):**
   - Using the diagnostic `default_trades.csv`, quantify whether losses are dominated by:
     - non-touch tail events,
     - specific session buckets,
     - specific VWAP distance regimes,
     - specific fold periods.
   - Only after that, propose minimal exit/filter hypotheses.

4. **Cross-instrument replication (next once MNQ protocol is defined):**
   - Apply the same pipeline and diagnostics to RTY, MYM, MCL, M2K, ES, MES, MGC if available.
   - Require similar directional lift and expectancy gates to avoid MNQ-only overfitting.

5. **Cost sensitivity pass (explicitly later):**
   - After structural issues are understood, run a separate cost sensitivity analysis (commission/spread/slippage scenarios).

## 4. Success Criteria
- Repo remains reproducible and disciplined:
  - `validate`, `backtest`, `plateau`, `diagnose`, `report`, `pytest` all run.
  - No lookahead / label leakage.
  - No live execution or trading recommendations.
- For any claim of validation (hard rule):
  - ≥100 events total,
  - ≥20 events per fold,
  - ≥+4pp lift over best baseline in the same universe,
  - **positive after-cost expectancy**,
  - **profit factor > 1**,
  - **≥4/5 positive folds**,
  - **stable out-of-sample plateau support**.

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
- Independent test reports:
  - Core V1: `/app/test_reports/iteration_1.json`
  - MNQ run: `/app/test_reports/iteration_2.json`
  - Diagnostics: `/app/test_reports/iteration_3.json`

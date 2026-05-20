# plan.md — Post-Absorption VWAP Reversal Engine (V1) — Updated

## 1. Objectives
- Build a **research-first** Pine + Python engine under `/app/problem_0004_absorption_vwap/` to test the hypothesis: **high volume + low displacement ⇒ possible absorption proxy**, interpreted via **session VWAP context**.
- Deliver a **reproducible CLI workflow** that:
  - imports raw futures CSVs with **configurable column mapping** (incl. `timestamp` vs `ts_event`, and `date+time` combination) from `data/raw/` later,
  - computes **session VWAP** (reset by configurable session inference; default calendar date in timestamp timezone),
  - detects **absorption proxy** events (high volume percentile + low displacement/ATR),
  - classifies **above/below/near VWAP** context,
  - generates **forward-only labels** for evaluation (no lookahead),
  - runs **walk-forward validation** with event-count gates,
  - compares against **baselines after costs**,
  - runs **sensitivity + parameter plateau search** with stable-neighborhood rejection,
  - outputs **JSON + Markdown + CSV** reports (+ HTML when enabled) with cross-instrument support.
- Enforce validation discipline:
  - **no lookahead**, labels used **only** for evaluation,
  - no repainting claims in Pine; **confirmed-bar only**,
  - no forced optimization, no live trading recommendation,
  - honest verdicts: `VALIDATED_STRONG / VALIDATED_WEAK / NOT_VALIDATED / REJECTED / INSUFFICIENT_DATA`.

**Current status:** Implementation is complete through Phase 4 (tests/smoke). Synthetic data is used only for smoke/schema checks and correctly yields `INSUFFICIENT_DATA` and `NO_STABLE_PLATEAU`. Remaining work is independent end-to-end validation with `testing_agent_v3`, followed by real-data validation (starting MNQ) once data is provided.

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
  - Supports missing symbol/timeframe via defaults.
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
- POC runner:
  - `python -m research_engine validate --data data/examples/synthetic_ohlcv_1m.csv --config configs/default_config.yaml`
  - Smoke run on synthetic data succeeds and honestly returns `INSUFFICIENT_DATA` (synthetic is smoke-only).

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
  - Fold metrics table emitted (time-ordered chunking).
  - Validation gates:
    - `>=100` events overall and `>=20` per fold, else `INSUFFICIENT_DATA`.
- Verdict logic:
  - Lift threshold vs best baseline, after-cost expectancy, profit factor threshold, fold consistency checks.
  - Includes explicit “plateau support required” reason when not supplied.
- Reporting (`reports.py`):
  - Per-run directory with `summary.json`, `summary.md`, `trades.csv`, `labels.csv`, `features.csv`, `fold_metrics.csv`, `baseline_compare.csv`, optional `report.html`.
  - `report --run latest` prints the latest report summary.
- Plateau search (`plateau.py`):
  - Grid from `configs/grid.yaml`.
  - Stable-neighborhood rejection via neighbor-count criterion.
  - Performance optimized by caching heavy feature computations and re-evaluating threshold parameters cheaply.
  - Synthetic run correctly yields `NO_STABLE_PLATEAU`.

### Phase 3 — Pine v6 module (conservative, confirmed bars, warnings) ✅ Completed
User stories:
1. Visualize session VWAP and absorption proxy markers on confirmed bars.
2. Enable/disable fade candidates above/below VWAP; classify near-VWAP separately.
3. View debug info to compare with Python.
4. Optionally run paper strategy (TradingView only), not live execution.
5. Follow QA notes to validate Pine vs Python.

Delivered:
- `pine/problem_0004_absorption_vwap_v1.pine`
  - Session VWAP, ATR, displacement/ATR, rolling percentile approximation.
  - Confirmed-bar signals only; alerts for absorption proxy and fade candidates.
  - Optional paper strategy with time stop and VWAP target.
  - Debug table: volume percentile, displacement/ATR, VWAP distance/ATR, location label, block reason.
  - Clear limitations and manual QA notes.
- Manual checklist: `tests/test_pine_checklist.md`.

### Phase 4 — Tests + smoke validation ✅ Completed
User stories:
1. Run `pytest` and confirm VWAP resets and labels are correct.
2. Detect schema violations early.
3. Ensure labels never leak into features.
4. Ensure verdict logic returns `INSUFFICIENT_DATA` correctly.
5. Ensure plateau selection rejects isolated spikes.

Delivered:
- Tests implemented and passing:
  - Loader mapping variants (incl. date+time combine).
  - VWAP reset and zero-volume carry-forward.
  - Absorption proxy feature calculation.
  - VWAP location classification.
  - Forward-only label behavior.
  - Validation verdict gates and plateau isolation rejection.
- Local results:
  - `pytest -q`: 11 passed (one expected zero-volume warning).
  - Lint: passes.

## 3. Next Actions
1. **Independent end-to-end validation (required next):**
   - Run `testing_agent_v3` against the repo.
   - Fix any issues found (CLI ergonomics, schema corner cases, report outputs, fold logic, leakage risks).
2. **Real-data validation (after you provide data):**
   - Import MNQ 1m/5m CSV under `data/raw/` using a mapping config.
   - Confirm timestamp timezone/session assumptions; adjust YAML session settings as needed.
   - Run:
     - `validate` (primary) + review baseline comparisons and fold consistency.
     - `plateau` to look for stable regions (not isolated peaks).
   - If MNQ fails gates, preserve useful warning/filter behavior and mark as `REJECTED/NOT_VALIDATED` as appropriate.
3. **Cross-instrument replication (if data available):**
   - Apply same pipeline to RTY, MYM, MCL, M2K, ES, MES, MGC.
   - Produce combined summaries to assess generalization.
4. **(Later, after validation) Enhance session config:**
   - Optional RTH session windows / futures session IDs (kept out of V1 core, but config hooks exist).

## 4. Success Criteria
- Repository exists at `/app/problem_0004_absorption_vwap/` and all commands work:
  - `python -m research_engine validate --data ... --config ...`
  - `python -m research_engine backtest --data ... --config ...`
  - `python -m research_engine plateau --data ... --grid ... --config ...`
  - `python -m research_engine report --run latest`
- Importer supports the expected raw CSV variants with configurable column mapping (incl. `ts_event`, `timestamp`, and date+time). Canonical schema enforced.
- Session VWAP correct with configurable session inference and correct resets.
- Absorption proxy detection + VWAP context classification reproducible and non-repainting.
- Labels are forward-only and isolated from feature generation.
- Walk-forward validation includes event-count gates, baseline comparisons after costs, and honest verdict logic.
- Plateau search rejects isolated spikes and can identify stable neighborhoods when they exist.
- Reports emitted as JSON+MD+CSV (+HTML when enabled), and cross-instrument support works.
- Pine v6 module mirrors Python logic as closely as feasible, uses confirmed-bar logic, and documents limitations clearly.
- **Final readiness gate for claiming validation:** must satisfy user-defined strong validation gates on real data (≥100 events, ≥20/fold, ≥4pp lift, positive after-cost expectancy, PF≥1.15, fold consistency, plateau support).
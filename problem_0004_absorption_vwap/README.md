# Problem 0004 — Post-Absorption VWAP Reversal Engine

## Executive Summary

This repository contains the complete research implementation for **Problem 0004: Post-Absorption VWAP Reversal Engine**.

The original hypothesis was:

> High volume + low displacement may be consistent with possible absorption. VWAP-relative context may indicate whether price is more likely to revert toward VWAP after that event.

The project was built as a **research-first Pine + Python system**, not a live trading bot. Pine handles chart-time warnings, markers, optional paper/backtest behavior, and visualization. Python handles data import, feature construction, validation, diagnostics, plateau analysis, strict holdout confirmation, and reporting.

### Final Recorded Verdict

**Problem 0004 is NOT_VALIDATED as a standalone strategy.**

This verdict was reached after strict train/holdout and cross-instrument testing across:

- MNQ
- RTY
- MYM
- ES
- MCL
- MGC

No candidate passed all required holdout validation gates.

### Repositioned Use Case

The project should be treated as a:

> **VWAP Absorption Reversion Warning Module**

Appropriate uses:

- chart warning/filter module,
- research candidate generator,
- discretionary review aid,
- future pre-registered hypothesis engine.

Inappropriate uses:

- validated standalone trading strategy,
- live trading system,
- broker execution system,
- guaranteed signal engine.

No live execution, broker integration, webhook execution, or auto-trading was added.

---

## Repository Location

Main project directory:

```text
/app/problem_0004_absorption_vwap/
```

Final packaged zip:

```text
/app/problem_0004_absorption_vwap_final_with_recent_regime.zip
```

Important files:

```text
/app/problem_0004_absorption_vwap/README.md
/app/problem_0004_absorption_vwap/FINAL_REPORT.md
/app/problem_0004_absorption_vwap/pine/problem_0004_absorption_vwap_v1.pine
/app/problem_0004_absorption_vwap/pine/problem_0004_absorption_vwap_v1_1.pine
/app/problem_0004_absorption_vwap/pine/problem_0004_absorption_vwap_v1_2.pine
/app/problem_0004_absorption_vwap/reports/holdout/cross_instrument_20260520_152935/
/app/problem_0004_absorption_vwap/reports/recent_regime/
```

---

## Original User Request and Project Scope

The user asked for a full implementation of a **Post-Absorption VWAP Reversal Engine**.

Original required scope included:

- Pine Script v6 module,
- Python package named `research_engine`,
- CSV OHLCV loader,
- VWAP calculator,
- absorption feature engine,
- forward-label engine,
- walk-forward validator,
- plateau search,
- reporting,
- tests,
- honest validation language.

The user explicitly required:

- no live execution,
- no broker API,
- no webhook execution,
- no hidden future labels in signal logic,
- no forced optimization,
- no unsupported institutional claims,
- honest `VALIDATED / NOT_VALIDATED / INSUFFICIENT_DATA` style outputs.

The user later clarified that V1 should be built under:

```text
/app/problem_0004_absorption_vwap/
```

The user also clarified:

- do **not** build a React UI in V1,
- focus on research engine, reports, tests, and Pine first,
- use synthetic CSV only for smoke/schema testing,
- use real futures data later for validation,
- first real validation target should be MNQ,
- then test RTY, MYM, MCL, M2K, ES, MES, MGC if available.

---

## Required Data Contract

Canonical required columns:

```csv
timestamp,open,high,low,close,volume,symbol,timeframe
```

Supported raw variants include:

```csv
timestamp,open,high,low,close,volume,symbol
```

and:

```csv
ts_event,symbol,open,high,low,close,volume
```

Also supported:

- separate `date` + `time` columns,
- configurable YAML column mapping,
- missing `symbol` filled from config default,
- missing `timeframe` filled from config default,
- calendar-date session inference by timestamp timezone.

Optional columns supported:

```csv
session_date,session_id,vwap,bid,ask,spread,commission,slippage
```

If VWAP is absent, session VWAP is computed as:

```text
typical_price = (high + low + close) / 3
session_vwap = cumulative(typical_price * volume) / cumulative(volume)
```

---

## Repository Structure Delivered

Implemented structure:

```text
problem_0004_absorption_vwap/
  README.md
  FINAL_REPORT.md
  requirements.txt
  pine/
    problem_0004_absorption_vwap_v1.pine
    problem_0004_absorption_vwap_v1_1.pine
    problem_0004_absorption_vwap_v1_2.pine
    WARNING_FILTER_MODE_NOTES.md
    V1_1_UPDATE_NOTES.md
    V1_2_UPDATE_NOTES.md
  research_engine/
    __init__.py
    __main__.py
    cli.py
    data_loader.py
    features.py
    vwap.py
    signal_logic.py
    labels.py
    backtest.py
    validation.py
    plateau.py
    diagnostics.py
    holdout.py
    recent_regime.py
    reports.py
    schemas.py
  configs/
    default_config.yaml
    grid.yaml
    mnq_5min_rth.yaml
    rty_5min_rth.yaml
    mym_5min_rth.yaml
    es_5min_rth.yaml
    mcl_5min_rth.yaml
    mgc_5min_rth.yaml
  data/
    raw/
    processed/
    examples/
  reports/
    walk_forward/
    parameter_plateaus/
    diagnostics/
    holdout/
    recent_regime/
    charts/
    latest.html
  tests/
    test_data_loader.py
    test_vwap.py
    test_features.py
    test_signal_logic.py
    test_labels.py
    test_validation.py
    test_diagnostics.py
    test_holdout.py
    test_recent_regime.py
    test_pine_checklist.md
```

---

## Main Python CLI Commands

Core commands implemented:

```bash
python -m research_engine validate --data data/examples/synthetic_ohlcv_1m.csv --config configs/default_config.yaml
python -m research_engine backtest --data data/examples/synthetic_ohlcv_1m.csv --config configs/default_config.yaml
python -m research_engine plateau --data data/examples/synthetic_ohlcv_1m.csv --grid configs/grid.yaml
python -m research_engine report --run latest
```

Additional research commands added during the project:

```bash
python -m research_engine diagnose --data data/raw/MNQ_5min_RTH_6year.csv --config configs/mnq_5min_rth.yaml --grid configs/grid.yaml
```

```bash
python -m research_engine holdout --data data/raw/MNQ_5min_RTH_6year.csv --config configs/mnq_5min_rth.yaml --grid configs/grid.yaml --train-end '2023-12-31 23:59:59' --holdout-start '2024-01-01 00:00:00' --top-n 10
```

```bash
python -m research_engine recent-regime
```

---

## Signal Definition Implemented

### Core Features

Implemented in `research_engine/features.py`:

```text
ATR
body_displacement = abs(close - open)
bar_range = high - low
displacement_atr = body_displacement / ATR
volume_percentile = percentile_rank(volume, volume_lookback)
session_vwap
vwap_distance = close - session_vwap
vwap_distance_atr = vwap_distance / ATR
location_vs_vwap
is_absorption_bar
absorption_side
block_reason
```

### Default Parameters

```text
volume_lookback = 100
high_volume_percentile_threshold = 95
atr_length = 60
max_displacement_atr = 0.3
near_vwap_threshold_atr = 0.25
reversal_horizon_bars = 15
volume_percentile_min_periods = 20
```

### Absorption Proxy

```text
is_absorption_bar =
  volume_percentile >= high_volume_percentile_threshold
  AND displacement_atr <= max_displacement_atr
```

Important wording:

> The system detects a **structural proxy consistent with possible absorption**. It does not prove hidden liquidity or institutional activity.

### VWAP Context

```text
above_vwap = close > session_vwap and not near_vwap
below_vwap = close < session_vwap and not near_vwap
near_vwap = abs(vwap_distance_atr) <= near_vwap_threshold_atr
```

Absorption sides:

```text
above_vwap
below_vwap
near_vwap
unknown
```

---

## Forward Labels

Implemented in `research_engine/labels.py`.

Labels are computed **after** feature generation and are used only for validation.

Labels include:

- `expected_direction`,
- `reversed_toward_vwap`,
- `return_next_horizon`,
- `bars_to_vwap_touch`,
- `max_adverse_excursion`,
- `max_favorable_excursion`.

Label logic:

- above-VWAP absorption expects downward/VWAP reversion,
- below-VWAP absorption expects upward/VWAP reversion,
- near-VWAP absorption is neutral/ambiguous.

The code includes safeguards so label columns are not included in decision-time features.

---

## Baselines Implemented

Implemented in `validation.py` and related modules.

Baselines include:

1. Absorption + VWAP reversal candidate.
2. High-volume-only reversal baseline.
3. Low-displacement-only reversal baseline.
4. VWAP fade without absorption filter.
5. RSI reversal baseline.
6. Random direction on absorption event bars.
7. Opposite-direction and random same-universe baselines for diagnostics/holdout/recent-regime subsets.

---

## Validation Discipline and Hard Gates

The project enforced strict validation discipline.

A setup must not be called validated unless it passes hard gates such as:

- at least 100 events/trades,
- at least 20 events/trades per fold where applicable,
- at least +4 percentage-point lift over same-universe baseline,
- positive after-cost expectancy,
- profit factor greater than 1.15 for strong confirmation,
- acceptable drawdown,
- at least 60% positive months or equivalent consistency,
- no single month/fold dominating profit,
- stable parameter plateau support,
- no data leakage between selection and validation.

The final global result did **not** pass these gates.

---

## Phase-by-Phase Conversation and Build History

### Phase 1 — Initial Build Request

The user asked to start the task and build the complete repository for Problem 0004.

Clarifications received:

- Build under `/app/problem_0004_absorption_vwap/`.
- Do not add a React UI in V1.
- Use synthetic CSV only for smoke/schema validation.
- Build real CSV importer for later futures data under `data/raw/`.
- Support `timestamp` and `ts_event` formats.
- Support separate date/time columns.
- Pine should be conservative v6-compatible.
- Reports should be JSON + Markdown + CSV, HTML if easy.
- Default session assumption should be calendar date in timestamp timezone, configurable in YAML.

Delivered:

- repository skeleton,
- Python package,
- configs,
- synthetic example data,
- CSV importer,
- VWAP engine,
- feature engine,
- labels,
- backtest/validation/plateau/reporting,
- Pine v6 script,
- tests.

Initial smoke results on synthetic data:

- validate: `INSUFFICIENT_DATA`, as expected,
- backtest: `INSUFFICIENT_DATA`,
- plateau: `NO_STABLE_PLATEAU`,
- tests: passed.

Synthetic data was explicitly treated as schema/smoke data only, not performance evidence.

---

### Phase 2 — MNQ Real-Data Run

The user uploaded:

```text
MNQ_5min_RTH_6year.csv
```

The file was placed under:

```text
data/raw/MNQ_5min_RTH_6year.csv
```

A symbol-specific config was created:

```text
configs/mnq_5min_rth.yaml
```

Importer improvements were made for real data:

- parse mixed timezone offsets using `utc=True`,
- convert timestamps to `America/New_York`,
- fill missing symbol values from default symbol,
- preserve existing strategy logic.

MNQ data loaded:

```text
bars: 122,295
date range: 2020-01-02 09:30 ET to 2026-03-06 15:55 ET
```

MNQ default validation results:

```text
absorption events: 825
above VWAP: 248
below VWAP: 331
near VWAP: 246
directional trades: 558
hit rate: 76.34%
best baseline hit rate: 71.33%
lift: +5.02pp
after-cost expectancy: -0.3233
profit factor: 0.9919
max drawdown: -3778.92
verdict: NOT_VALIDATED
```

Reason:

- directional hit rate and lift were promising,
- but after-cost expectancy was negative,
- profit factor was below validation threshold,
- fold consistency was weak.

---

### Phase 3 — MNQ Diagnostic Decomposition

The user asked not to reject the project yet and requested diagnostic decomposition to understand why high hit rate did not translate into positive expectancy.

Diagnostics were added in:

```text
research_engine/diagnostics.py
```

CLI added:

```bash
python -m research_engine diagnose ...
```

MNQ diagnostic report:

```text
reports/diagnostics/diagnostic_20260520_143421/
```

Key MNQ payoff distribution:

| Metric | Value |
|---|---:|
| Trades | 558 |
| Hit rate | 76.34% |
| Average winner | +51.68 |
| Average loser | -169.44 |
| Median winner | +30.31 |
| Median loser | -120.50 |
| Win/loss ratio | 0.305 |
| Expectancy before cost | +0.6767 |
| Expectancy after cost | -0.3233 |
| Cost drag/trade | 1.00 |
| Profit factor | 0.9919 |

Diagnosis:

> The signal direction was meaningful, but payoff asymmetry was poor. Losses were much larger than wins, and cost drag pushed expectancy negative.

VWAP side breakdown:

| Side | Trades | Hit | Baseline Hit | Lift | Expectancy | PF | Folds |
|---|---:|---:|---:|---:|---:|---:|---:|
| Above VWAP / Shorts | 234 | 79.91% | 38.89% | +41.03pp | +7.02 | 1.213 | 3/5 |
| Below VWAP / Longs | 324 | 73.77% | 37.96% | +35.80pp | -5.63 | 0.874 | 1/5 |

Important finding:

> Above-VWAP shorts were healthier than below-VWAP longs. They should be treated separately.

Session findings:

- first 30 minutes: mildly positive,
- afternoon: promising but low sample,
- last 30 minutes: structurally poor,
- midday: weak and low sample.

Strength bucket findings:

- displacement/ATR 0.10–0.20 was strongest,
- VWAP distance 1.00–2.00 ATR was stronger,
- extreme 99–100 volume percentile bucket was not necessarily better.

Exit/target findings:

```text
VWAP touch rate: 71.68%
average bars to VWAP touch: 2.75
median bars to VWAP touch: 1
avg MFE: 72.62 points
avg MAE: 69.38 points
touched-trade expectancy: +51.69
not-touched-trade expectancy: -132.01
current target-or-horizon expectancy: -0.3233
pure fixed-horizon diagnostic expectancy: +4.4892
```

Diagnosis:

> VWAP touch occurred often, but non-touch trades caused large losses. The problem appeared related to exit/tail-risk handling rather than pure directional failure.

Top diagnostic candidates were identified, but explicitly not validated.

---

### Phase 4 — Strict MNQ Train/Holdout Confirmation

The user requested a strict true holdout protocol.

Protocol:

```text
training/selection: 2020-01-02 to 2023-12-31
holdout validation: 2024-01-01 to 2026-03-06
```

Module added:

```text
research_engine/holdout.py
```

CLI added:

```bash
python -m research_engine holdout ...
```

MNQ holdout report:

```text
reports/holdout/holdout_20260520_150013/
```

MNQ split:

```text
training bars: 79,233
holdout bars: 43,062
actual training end: 2023-12-29 15:55 ET
actual holdout start: 2024-01-02 09:30 ET
```

Training-only plateau centroid:

```text
volume_lookback: 150
high_volume_percentile_threshold: 95
atr_length: 40
max_displacement_atr: 0.3
near_vwap_threshold_atr: 0.25
reversal_horizon_bars: 15
stable_count: 2190
```

Final MNQ holdout verdict:

```text
NOT_VALIDATED
```

Reason:

> No frozen training-selected candidate passed all holdout hard gates.

Best-looking MNQ row:

```text
default_above_vwap_shorts_only + fixed_horizon
trades: 81
hit rate: 48.15%
baseline hit: 51.85%
lift: -3.70pp
expectancy: +43.31
PF: 1.606
positive months: 16/27 = 59.26%
```

It failed because:

- fewer than 100 trades,
- negative lift vs same-universe baseline,
- positive months just below 60%,
- not sufficient for validation.

Conclusion:

> MNQ remained NOT_VALIDATED but useful as a filter/exit research candidate.

---

### Phase 5 — Cross-Instrument Strict Holdout

The user uploaded additional futures datasets:

- RTY
- MYM
- ES
- MCL
- MGC

Files placed under `data/raw/`:

```text
RTY_5min_RTH_6year.csv
MYM_5min_RTH_6year.csv
ES_5min_RTH_6year.csv
MCL_5min_RTH_6year.csv
MGC_5min_RTH_6year.csv
```

Configs created:

```text
configs/rty_5min_rth.yaml
configs/mym_5min_rth.yaml
configs/es_5min_rth.yaml
configs/mcl_5min_rth.yaml
configs/mgc_5min_rth.yaml
```

Session windows:

```text
RTY/MYM/ES: 09:30–16:00 ET
MCL:        09:00–14:30 ET
MGC:        08:20–13:30 ET
```

The same strict train/holdout protocol was run on each symbol.

Cross-instrument summary:

```text
reports/holdout/cross_instrument_20260520_152935/
```

Best holdout rows by symbol:

| Symbol | Candidate | Trades | Hit | Baseline Hit | Lift | Expectancy | PF | Max DD | Positive Months | Concentration | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| RTY | above-VWAP shorts / fixed horizon | 85 | 52.94% | 45.88% | +7.06pp | +43.94 | 1.196 | -5540.00 | 13/26 | 75.2% | NOT_VALIDATED |
| MYM | below-VWAP longs / fixed horizon | 103 | 58.25% | 53.40% | +4.85pp | +9.65 | 1.359 | -952.50 | 18/27 | 51.3% | NOT_VALIDATED |
| ES | train plateau 05 / target-or-horizon | 57 | 61.40% | 29.82% | +31.58pp | +121.22 | 1.398 | -4512.50 | 15/22 | 63.2% | NOT_VALIDATED |
| MCL | train plateau 07 / target-or-horizon | 153 | 66.67% | 30.07% | +36.60pp | -0.09 | 0.994 | -357.86 | 14/26 | n/a | NOT_VALIDATED |
| MGC | above-VWAP shorts / fixed horizon | 138 | 50.72% | 47.83% | +2.90pp | +18.19 | 1.494 | -879.00 | 16/26 | 45.2% | NOT_VALIDATED |

Interpretation:

- RTY had good lift but insufficient trade count, weak positive-month consistency, and high concentration.
- MYM was the closest near-miss: enough trades, positive expectancy, PF > 1.15, and lift > 4pp, but concentration was just over the 50% limit and training-stable support was insufficient.
- ES had strong expectancy but too few trades and high concentration.
- MCL had enough trades but negative expectancy and PF below threshold.
- MGC had positive expectancy and PF but insufficient lift and training-stable support.

Final cross-instrument conclusion:

```text
All tested instruments: NOT_VALIDATED
Zero candidates passed all strict holdout gates.
```

---

### Phase 6 — Final Repositioning

The user asked to record Problem 0004 as NOT_VALIDATED across strict cross-instrument holdout and to reposition the use case.

Final report created:

```text
FINAL_REPORT.md
```

Final report section added:

```text
Repositioned Use Case: VWAP Absorption Reversion Warning Module
```

The report explains:

1. Standalone entries did not pass strict validation.
2. Directional structure exists in multiple instruments.
3. MYM and MGC are the strongest weak candidates.
4. The system is useful as a warning/filter/candidate generator, not a live trading strategy.
5. Above-VWAP shorts and below-VWAP longs should be treated separately.
6. No live trading recommendation is made.

---

### Phase 7 — Recent-Regime Analysis

The user requested a separate recent-regime analysis without changing the global verdict.

Purpose:

> Does the signal appear active in recent 1-month, 3-month, 6-month, and 1-year regimes?

Module added:

```text
research_engine/recent_regime.py
```

CLI added:

```bash
python -m research_engine recent-regime
```

Reports created:

```text
reports/recent_regime/recent_regime_all_results.csv
reports/recent_regime/recent_regime_summary.csv
reports/recent_regime/recent_regime_summary.md
reports/recent_regime/recent_regime_summary.html
reports/latest.html
```

Requested symbols:

- MNQ
- RTY
- MYM
- ES
- MES
- MCL
- M2K
- MGC
- GC

Available:

- MNQ
- RTY
- MYM
- ES
- MCL
- MGC

Not available:

- MES
- M2K
- GC

Recent-regime classification counts:

```text
RECENT_REGIME_ACTIVE: 0
RECENT_REGIME_WEAK: 0
WARNING_ONLY: 10
INSUFFICIENT_RECENT_DATA: 26
RECENT_REGIME_INACTIVE: 0
```

Summary by symbol:

| Symbol | Active Windows | Weak Windows | Warning-Only Windows | Insufficient Windows | Recent Posture |
|---|---:|---:|---:|---:|---|
| MNQ | 0 | 0 | 1 | 3 | warning/filter only |
| RTY | 0 | 0 | 1 | 3 | warning/filter only |
| MYM | 0 | 0 | 1 | 3 | warning/filter only |
| ES | 0 | 0 | 1 | 3 | warning/filter only |
| MCL | 0 | 0 | 3 | 1 | warning/filter only |
| MGC | 0 | 0 | 3 | 1 | warning/filter only |
| MES | 0 | 0 | 0 | 4 | not available |
| M2K | 0 | 0 | 0 | 4 | not available |
| GC | 0 | 0 | 0 | 4 | not available |

Recent-regime interpretation:

- No recent window qualified as `RECENT_REGIME_ACTIVE`.
- No recent window qualified as `RECENT_REGIME_WEAK`.
- Several 12-month windows had directional lift but negative expectancy or PF <= 1, so they were `WARNING_ONLY`.
- Recent behavior did not change the global verdict.

Global verdict remained:

```text
NOT_VALIDATED
```

---

## Pine Script Evolution

### Pine V1

File:

```text
pine/problem_0004_absorption_vwap_v1.pine
```

V1 was a conservative Pine Script v6 strategy script with:

- session VWAP,
- absorption markers,
- above/below/near VWAP classification,
- optional paper strategy behavior,
- debug table,
- alerts,
- confirmed-bar logic.

It was a `strategy()` script, not a pure `indicator()` script, but paper entries were disabled by default.

---

### Pine V1.1

File:

```text
pine/problem_0004_absorption_vwap_v1_1.pine
```

V1.1 improvements:

- used `timeframe.change("D")` for daily boundary logic,
- added comments about TradingView commission/slippage being manually configured unless hardcoded,
- added preset notes for diagnostic candidates:
  - default research setup,
  - Candidate 1,
  - Candidate 4,
  - Candidate 8,
- kept warning/filter mode as default,
- kept paper strategy optional and disabled by default,
- added no live execution.

---

### Pine V1.2

File:

```text
pine/problem_0004_absorption_vwap_v1_2.pine
```

V1.2 was created after identifying a possible mismatch between Python RTH data and TradingView extended-session charts.

V1.2 added RTH session matching:

```text
useRthOnly = true
RTH session = 0930-1600
RTH timezone = America/New_York
```

When `useRthOnly = true`:

1. VWAP resets at RTH session start.
2. VWAP accumulates only RTH bars.
3. Absorption warnings only trigger during RTH.
4. Candidate booleans only trigger during RTH.
5. Paper entries only occur during RTH.
6. Daily trade counter resets at RTH start.
7. Outside RTH, no new signals or entries are created.

When `useRthOnly = false`:

- V1.1 daily reset behavior is used with `timeframe.change("D")`.

Pine V1.2 is the recommended TradingView testing version.

Important Pine limitation:

> I cannot compile Pine inside this environment. The syntax is written as conservative Pine Script v6 as far as possible, but final compile confirmation must be done inside TradingView.

---

## TradingView Testing Instructions

Recommended Pine file:

```text
pine/problem_0004_absorption_vwap_v1_2.pine
```

Steps:

1. Open TradingView.
2. Open the futures chart, preferably 5-minute.
3. Open Pine Editor.
4. Paste the full V1.2 Pine code.
5. Save.
6. Add to chart.
7. Keep default mode first:

```text
Mode = Warning/filter only
enablePaperStrategy = false
useRthOnly = true
RTH session = 0930-1600
RTH timezone = America/New_York
```

8. Confirm markers appear.
9. Only for paper/backtest mode, explicitly set:

```text
Mode = Paper strategy optional
enablePaperStrategy = true
```

10. Configure TradingView Strategy Properties manually:

```text
Slippage = 1 tick
Commission = 0
```

Important:

- Pine is for warning/filter research and optional paper testing.
- It is not live execution.
- It is not a validated strategy.

---

## Diagnostic Candidate Parameter Notes

Pine V1.1 and V1.2 include preset notes for manual parameter entry.

### Default Research Setup

```text
volumeLookback = 100
highVolumePercentileThreshold = 95
atrLength = 60
maxDisplacementAtr = 0.3
nearVwapThresholdAtr = 0.25
reversalHorizonBars = 15
```

### Candidate 1

```text
volumeLookback = 75
highVolumePercentileThreshold = 97.5
atrLength = 60
maxDisplacementAtr = 0.5
nearVwapThresholdAtr = 0.5
reversalHorizonBars = 20
```

### Candidate 4

```text
volumeLookback = 100
highVolumePercentileThreshold = 97.5
atrLength = 60
maxDisplacementAtr = 0.2
nearVwapThresholdAtr = 0.1
reversalHorizonBars = 10
```

### Candidate 8

```text
volumeLookback = 100
highVolumePercentileThreshold = 97.5
atrLength = 20
maxDisplacementAtr = 0.3
nearVwapThresholdAtr = 0.25
reversalHorizonBars = 5
```

These are research diagnostics only, not validated strategies.

---

## Full-Sample MNQ Default Result

MNQ full dataset:

```text
bars: 122,295
range: 2020-01-02 09:30 ET to 2026-03-06 15:55 ET
```

Default event definition:

```text
volume percentile >= 95 over 100 bars
body displacement / ATR(60) <= 0.30
near VWAP threshold = 0.25 ATR
horizon = 15 bars
```

Result:

```text
absorption events: 825
above VWAP: 248
below VWAP: 331
near VWAP: 246
directional trades: 558
hit rate: 76.34%
best baseline hit rate: 71.33%
lift: +5.02pp
after-cost expectancy: -0.3233
profit factor: 0.9919
max drawdown: -3778.92
verdict: NOT_VALIDATED
```

Interpretation:

- Directional lift existed.
- Payoff did not validate.
- Losses were too large relative to wins.

---

## Key Research Conclusions

### What Worked

- The feature detector successfully identifies high-volume/low-displacement events.
- VWAP-relative location classification works.
- Directional lift appeared in multiple datasets and windows.
- Above-VWAP shorts often behaved differently from below-VWAP longs.
- MYM and MGC produced the strongest weak research leads.
- The system is useful for warning/filter research.

### What Failed

- No standalone candidate passed strict holdout validation.
- Default MNQ strategy had negative expectancy and PF below 1.
- Several promising candidates failed due to:
  - insufficient trade count,
  - concentration risk,
  - unstable positive months,
  - insufficient lift,
  - negative expectancy,
  - lack of stable training-selected support.

### Final Interpretation

The absorption/VWAP concept appears **structurally meaningful**, but the implemented standalone trade entry/exit logic is **not validated**.

Best final positioning:

```text
Research-only VWAP Absorption Reversion Warning Module
```

---

## Test and Verification History

Independent test reports created during the conversation:

```text
/app/test_reports/iteration_1.json  # core V1 verification
/app/test_reports/iteration_2.json  # MNQ real-data verification
/app/test_reports/iteration_3.json  # diagnostic decomposition verification
/app/test_reports/iteration_4.json  # MNQ holdout verification
/app/test_reports/iteration_5.json  # cross-instrument holdout verification
/app/test_reports/iteration_6.json  # final report + Pine warning/filter verification
/app/test_reports/iteration_7.json  # recent-regime verification
```

Latest Python test count after recent-regime additions:

```text
pytest -q: 17 passed
```

Python lint passed.

---

## Output Reports

### Final Report

```text
FINAL_REPORT.md
```

### MNQ Reports

```text
reports/walk_forward/validate_20260520_141142/
reports/walk_forward/backtest_20260520_141308/
reports/parameter_plateaus/plateau_20260520_141004/
reports/diagnostics/diagnostic_20260520_143421/
reports/holdout/holdout_20260520_150013/
```

### Cross-Instrument Holdout Reports

```text
reports/holdout/holdout_20260520_151731/  # RTY
reports/holdout/holdout_20260520_152057/  # MYM
reports/holdout/holdout_20260520_152416/  # ES
reports/holdout/holdout_20260520_152618/  # MCL
reports/holdout/holdout_20260520_152912/  # MGC
reports/holdout/cross_instrument_20260520_152935/
```

### Recent-Regime Reports

```text
reports/recent_regime/recent_regime_all_results.csv
reports/recent_regime/recent_regime_summary.csv
reports/recent_regime/recent_regime_summary.md
reports/recent_regime/recent_regime_summary.html
reports/latest.html
```

---

## Final Zip Package

The final packaged repository including recent-regime reports and Pine V1.2 is:

```text
/app/problem_0004_absorption_vwap_final_with_recent_regime.zip
```

The package includes:

- source code,
- configs,
- tests,
- synthetic example data,
- uploaded futures data in `data/raw/`,
- reports,
- Pine V1/V1.1/V1.2 scripts,
- final report,
- recent-regime reports.

---

## Important Warnings

1. **Not validated as a standalone strategy**

Problem 0004 remains:

```text
NOT_VALIDATED
```

2. **No live trading recommendation**

No output should be interpreted as a recommendation to trade live.

3. **No hidden liquidity proof**

The term absorption is a structural proxy only.

Correct wording:

```text
This bar has high volume and low displacement, consistent with possible absorption.
```

Incorrect wording:

```text
Institutions are absorbing here.
```

4. **TradingView results may differ from Python**

Reasons include:

- session settings,
- extended-hours bars,
- chart data source differences,
- Pine percentile approximation,
- manual commission/slippage settings,
- symbol rollover behavior.

Pine V1.2 was created specifically to reduce RTH session mismatch.

5. **Recent-regime testing is not validation**

Recent-regime testing showed warning-only behavior, not validation.

---

## Recommended Next Research Steps

Do not optimize further just to force validation.

If future research continues, use pre-registered hypotheses such as:

1. Separate above-VWAP shorts and below-VWAP longs.
2. Study not-touch tail risk before designing new exits.
3. Test displacement/ATR 0.10–0.20 as a pre-registered filter.
4. Test VWAP-distance 1–2 ATR as a pre-registered filter.
5. Avoid extreme volume percentile 99–100 unless separately validated.
6. Add rolling walk-forward selection where each candidate is chosen only on prior data.
7. Re-test with more realistic commissions/spread/slippage after structural robustness is established.
8. Replicate across additional instruments only with strict holdout discipline.

---

## Final Status Statement

Problem 0004 successfully produced a complete, reproducible research engine and Pine warning module.

The research found that the signal has directional structure but does not pass strict validation as a standalone trading strategy.

Final status:

```text
NOT_VALIDATED as standalone strategy
```

Repositioned status:

```text
VWAP Absorption Reversion Warning Module
```

No live execution, broker integration, webhook execution, auto-trading, or trading recommendation is included.

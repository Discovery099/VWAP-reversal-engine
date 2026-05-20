# Problem 0004 Final Report — Post-Absorption VWAP Reversal Engine

## Final Research Verdict

Problem 0004 is recorded as **NOT_VALIDATED** across strict cross-instrument holdout testing.

The tested instruments were:

- MNQ
- RTY
- MYM
- ES
- MCL
- MGC

No frozen candidate passed all strict holdout gates:

- at least 100 holdout trades,
- at least +4 percentage-point lift over the same-universe baseline,
- positive after-cost expectancy,
- profit factor > 1.15,
- at least 60% positive months,
- no single month dominating profit,
- stable training-selected parameter support.

This project should **not** be represented as a validated standalone trading strategy.

## Repositioned Use Case: VWAP Absorption Reversion Warning Module

### 1. Standalone entries did not pass strict validation

The absorption/VWAP reversal entries failed strict holdout confirmation across MNQ, RTY, MYM, ES, MCL, and MGC. Some candidates showed attractive isolated metrics, but each failed at least one hard gate such as sample count, concentration risk, insufficient lift, unstable month consistency, weak profit factor, or lack of stable training-selected support.

### 2. Directional structure exists in multiple instruments

The signal was not random noise. Multiple instruments showed directional structure, especially when absorption was interpreted relative to VWAP. Several subsets produced meaningful directional lift or positive expectancy in holdout, but not with enough consistency to justify validation language.

### 3. MYM and MGC are the strongest weak candidates

The strongest weak cross-instrument candidates were:

- **MYM** below-VWAP longs with fixed-horizon diagnostic exit:
  - 103 holdout trades,
  - +4.85pp lift,
  - positive expectancy,
  - PF 1.359,
  - failed due concentration risk above the threshold and insufficient stable training support.

- **MGC** above-VWAP shorts:
  - 138 holdout trades,
  - positive expectancy,
  - PF 1.494 under fixed-horizon measurement,
  - failed because lift was below +4pp and training support was insufficient.

These are research leads, not validated strategies.

### 4. Appropriate use: warning/filter/candidate generator

The correct use case is a **VWAP Absorption Reversion Warning Module**:

- flag possible absorption proxy bars,
- classify the VWAP context as above / below / near,
- warn when VWAP reversion risk may be elevated,
- support discretionary review, downstream filters, or future pre-registered research,
- avoid presenting the event itself as a trade entry.

### 5. Treat above-VWAP shorts and below-VWAP longs separately

Above-VWAP absorption and below-VWAP absorption behaved differently across instruments. They should not be pooled as one generic strategy without separate validation. Future research should evaluate:

- above-VWAP absorption as possible short-side VWAP reversion warning,
- below-VWAP absorption as possible long-side VWAP reversion warning,
- near-VWAP absorption as ambiguous context with no directional claim by default.

### 6. No live trading recommendation

No live trading recommendation is made. The Pine module defaults to warning/filter mode only. Paper strategy behavior is optional and disabled by default. No broker integration, webhook execution, or auto-trading feature is included.

## Final Artifact Paths

- Cross-instrument summary: `reports/holdout/cross_instrument_20260520_152935/`
- Pine warning/filter script: `pine/problem_0004_absorption_vwap_v1.pine`
- MNQ holdout: `reports/holdout/holdout_20260520_150013/`
- RTY holdout: `reports/holdout/holdout_20260520_151731/`
- MYM holdout: `reports/holdout/holdout_20260520_152057/`
- ES holdout: `reports/holdout/holdout_20260520_152416/`
- MCL holdout: `reports/holdout/holdout_20260520_152618/`
- MGC holdout: `reports/holdout/holdout_20260520_152912/`

## Status

**Final status: NOT_VALIDATED as standalone strategy.**

**Repositioned status: research-only VWAP absorption reversion warning/filter module.**

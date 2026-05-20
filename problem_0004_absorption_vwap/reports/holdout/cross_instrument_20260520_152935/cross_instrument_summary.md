# Cross-Instrument Strict Holdout Summary

All candidates were selected/frozen using training windows only, then evaluated on holdout. No strategy logic was changed.

| symbol | candidate type | trades | hit | baseline hit | lift pp | expectancy | PF | max DD | positive months | concentration risk | final verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| RTY | default_above_vwap_shorts_only / fixed_horizon | 85 | 52.94% | 45.88% | 7.06 | 43.94 | 1.196 | -5540.00 | 13/26 (50.0%) | 75.2% | NOT_VALIDATED |
| MYM | default_below_vwap_longs_only / fixed_horizon | 103 | 58.25% | 53.40% | 4.85 | 9.65 | 1.359 | -952.50 | 18/27 (66.7%) | 51.3% | NOT_VALIDATED |
| ES | train_plateau_05 / target_or_horizon | 57 | 61.40% | 29.82% | 31.58 | 121.22 | 1.398 | -4512.50 | 15/22 (68.2%) | 63.2% | NOT_VALIDATED |
| MCL | train_plateau_07 / target_or_horizon | 153 | 66.67% | 30.07% | 36.60 | -0.09 | 0.994 | -357.86 | 14/26 (53.8%) | n/a | NOT_VALIDATED |
| MGC | default_above_vwap_shorts_only / fixed_horizon | 138 | 50.72% | 47.83% | 2.90 | 18.19 | 1.494 | -879.00 | 16/26 (61.5%) | 45.2% | NOT_VALIDATED |

## Report directories
- RTY: `reports/holdout/holdout_20260520_151731/`
- MYM: `reports/holdout/holdout_20260520_152057/`
- ES: `reports/holdout/holdout_20260520_152416/`
- MCL: `reports/holdout/holdout_20260520_152618/`
- MGC: `reports/holdout/holdout_20260520_152912/`
# Pine Warning / Filter Mode Notes

The Pine module now exposes explicit warning/filter booleans:

```text
absorptionWarning
aboveVwapAbsorption
belowVwapAbsorption
nearVwapAbsorption
vwapReversionCandidate
```

Default mode is `Warning/filter only` and `enablePaperStrategy` is `false` by default.

These booleans are intended for chart warnings, alert creation, and downstream filtering. They are not validated trade instructions and make no live-trading recommendation.

Interpretation:

- `absorptionWarning`: high-volume + low-displacement proxy bar confirmed.
- `aboveVwapAbsorption`: absorption proxy above VWAP; possible short-side VWAP reversion warning.
- `belowVwapAbsorption`: absorption proxy below VWAP; possible long-side VWAP reversion warning.
- `nearVwapAbsorption`: absorption proxy near VWAP; ambiguous, no directional claim.
- `vwapReversionCandidate`: above or below VWAP directional warning candidate.

Paper strategy mode remains optional and must be explicitly enabled with `Mode = Paper strategy optional` and `enablePaperStrategy = true`.

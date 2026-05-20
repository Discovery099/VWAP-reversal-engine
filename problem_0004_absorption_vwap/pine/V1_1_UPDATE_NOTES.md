# Pine V1.1 Update Notes

File: `pine/problem_0004_absorption_vwap_v1_1.pine`

Changes from V1:

1. Uses Pine v6 daily boundary helper:

```pine
newSession = timeframe.change("D")
```

2. Adds explicit comment that TradingView strategy slippage/commission must be configured manually in Strategy Properties unless hardcoded in `strategy()`.

3. Adds preset input notes for manually entering diagnostic candidate settings:

- Default research setup: `VL100 / VP95 / ATR60 / Disp0.3 / Near0.25 / H15`
- Candidate 1: `VL75 / VP97.5 / ATR60 / Disp0.5 / Near0.5 / H20`
- Candidate 4: `VL100 / VP97.5 / ATR60 / Disp0.2 / Near0.1 / H10`
- Candidate 8: `VL100 / VP97.5 / ATR20 / Disp0.3 / Near0.25 / H5`

4. Default mode remains `Warning/filter only`.

5. Paper strategy entries remain optional and disabled by default. They require:

```text
Mode = Paper strategy optional
enablePaperStrategy = true
```

6. No live execution, webhook execution, broker execution, or auto-trading was added.

Note: preset input notes are labels/reminders only. Pine inputs are not dynamically changed by selecting a note; manually enter the corresponding parameter values.

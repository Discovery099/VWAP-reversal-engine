# Pine V1.2 Update Notes

File: `pine/problem_0004_absorption_vwap_v1_2.pine`

V1.2 is based on V1.1 and focuses only on RTH session matching.

New inputs:

```text
useRthOnly = true
RTH session = 0930-1600
RTH timezone = America/New_York
```

When `useRthOnly = true`:

1. VWAP resets at RTH session start.
2. VWAP accumulates only RTH bars.
3. `absorptionWarning` and candidate booleans only trigger during RTH.
4. Paper entries only occur during RTH.
5. Daily trade counter resets at RTH session start.
6. Outside RTH, no new signals or entries are created.

When `useRthOnly = false`:

- V1.1 daily reset behavior is used with `timeframe.change("D")`.

Unchanged:

- warning/filter mode remains default,
- `enablePaperStrategy` remains false by default,
- preset notes are retained,
- no live execution,
- no webhook execution,
- no broker integration,
- no verdict change.

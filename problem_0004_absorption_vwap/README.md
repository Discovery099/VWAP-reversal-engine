# Post-Absorption VWAP Reversal Engine V1

Research-first engine for testing whether high-volume, low-displacement bars are a useful **possible absorption proxy** when interpreted relative to session VWAP.

This project does **not** prove hidden liquidity, does **not** place live orders, and does **not** make trading recommendations. It produces research diagnostics and honest validation verdicts.

## Quick start

```bash
cd /app/problem_0004_absorption_vwap
python -m research_engine validate --data data/examples/synthetic_ohlcv_1m.csv --config configs/default_config.yaml
python -m research_engine backtest --data data/examples/synthetic_ohlcv_1m.csv --config configs/default_config.yaml
python -m research_engine plateau --data data/examples/synthetic_ohlcv_1m.csv --grid configs/grid.yaml
python -m research_engine report --run latest
pytest -q
```

The bundled synthetic CSV is only for schema, parser, and smoke testing. It is never evidence of profitability.

## Real data workflow

Place futures CSV exports under `data/raw/`, then point the CLI at a file or directory. The importer supports configurable column mapping, including:

- `timestamp, open, high, low, close, volume, symbol`
- `ts_event, symbol, open, high, low, close, volume`
- separate `date` and `time` columns combined into one timestamp

Default session inference is calendar date in the timestamp timezone; configure this in `configs/default_config.yaml` for UTC/RTH futures workflows.

## Core hypothesis

- High volume + low displacement = **consistent with possible absorption**.
- Below VWAP may imply sellers were absorbed and price may revert upward toward VWAP.
- Above VWAP may imply buyers were absorbed and price may revert downward toward VWAP.
- Near VWAP is ambiguous and classified separately.

The engine tests this hypothesis and can reject it.

## Validation gates

A signal cannot be `VALIDATED_STRONG` unless it has at least:

- 100 labelled absorption events,
- 20 events per walk-forward fold,
- +4 percentage-point lift over the best baseline,
- positive after-cost expectancy,
- profit factor >= 1.15 for strong validation,
- meaningful fold consistency,
- stable plateau support.

## Pine

`pine/problem_0004_absorption_vwap_v1.pine` is a conservative Pine v6-compatible warning/paper-strategy module. It uses confirmed-bar logic and does not use future labels.

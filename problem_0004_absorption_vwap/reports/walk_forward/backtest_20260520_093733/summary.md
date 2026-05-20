# Post-Absorption VWAP Reversal Report

Validation status: `INSUFFICIENT_DATA`

## Important limitation
This engine detects a high-volume/low-displacement structural proxy consistent with possible absorption. It does not prove hidden orders and does not provide live-trading recommendations.

**Synthetic data warning:** this run used synthetic data for parser/schema smoke testing only. Do not treat the metrics as evidence of profitability.

## Metrics
- `trade_count`: 14
- `hit_rate`: 0.5
- `expectancy_after_cost`: -0.5530004160679839
- `total_net_pnl`: -7.742005824951775
- `profit_factor`: 0.708947149437927
- `max_drawdown`: -18.18999999999869

## Verdict reasons
- Only 14 directional absorption trades; need at least 100 for full validation.

## Diagnostics
- `absorption_event_count`: 14
- `by_side`: {'above_vwap': 4, 'below_vwap': 10}
- `by_session`: {'MNQ|2024-01-02': 8, 'MNQ|2024-01-03': 6}
- `by_volume_bucket`: {'(90.0, 95.0]': 0.0, '(95.0, 97.5]': 0.4, '(97.5, 100.0]': 0.625}
- `by_time_bucket`: {'midday': 0.5}

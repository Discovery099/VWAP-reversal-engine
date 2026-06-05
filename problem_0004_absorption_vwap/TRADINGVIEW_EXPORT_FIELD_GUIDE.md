# TradingView Data Export Field Recommendations

**Document Purpose**: Identify additional data fields to export from TradingView Strategy Tester for enhanced diagnostic analysis.

**Date Created**: 2026-06-05  
**Status**: PRE-TEST CONFIGURATION GUIDE

---

## Standard TradingView Export Fields (Currently Available)

Based on the prior 6 CSV uploads, TradingView Strategy Tester exports include:

### Per-Trade Fields (Standard)
1. **Trade number** - Unique trade identifier
2. **Type** - Entry long, Exit long, Entry short, Exit short
3. **Date and time** - Timestamp of trade execution
4. **Signal** - Strategy signal label (L, XL, S, XS)
5. **Price USD** - Execution price
6. **Size (qty)** - Contract quantity
7. **Size (value)** - Notional value
8. **Net PnL USD** - Per-trade profit/loss after costs
9. **Net PnL %** - Percentage return
10. **Favorable excursion USD** - Maximum favorable excursion (MFE)
11. **Favorable excursion %** - MFE as percentage
12. **Adverse excursion USD** - Maximum adverse excursion (MAE)
13. **Adverse excursion %** - MAE as percentage
14. **Cumulative PnL USD** - Running total PnL
15. **Cumulative PnL %** - Running percentage PnL

### Summary-Level Metrics (Available in Strategy Tester UI)
- Total Closed Trades
- Percent Profitable
- Profit Factor
- Max Drawdown (USD & %)
- Average Trade
- Average # Bars in Trade
- Net Profit
- Gross Profit
- Gross Loss
- Sharpe Ratio (if available)
- Commission & Slippage totals

---

## Recommended Additional Export Fields

If TradingView Strategy Tester allows custom export configuration or if accessible via TradingView API/Pine Script logging, the following fields would significantly enhance diagnostic analysis:

### Priority 1: Trade Execution Diagnostics

#### 1.1 Entry Bar Metadata
- **Entry Bar Index** - Absolute bar number at entry
- **Entry Bar Time** - Exact timestamp (with seconds precision if available)
- **Entry Session Hour** - Hour of trading day (e.g., 09:30 → 9, 15:45 → 15)
- **Entry Day of Week** - Monday=1, Friday=5
- **Entry Intrabar Position** - If using lower timeframe for entries, position within parent bar

**Rationale**: Enables time-of-day distribution analysis, session-specific performance evaluation, and detection of concentration in specific trading hours.

#### 1.2 Exit Bar Metadata
- **Exit Bar Index** - Absolute bar number at exit
- **Exit Reason** - [Target, Stop, Time, Signal Flip, EOD] - critical for understanding exit mode distribution
- **Bars in Trade** - Duration (already available in summary, but per-trade export is better)
- **Exit Session Hour** - Hour of trading day at exit

**Rationale**: Per-trade exit reason breakdown enables precise analysis of which exit logic components are working (e.g., are most winners hitting targets or time exits? Are most losers hitting stops or reversing?).

### Priority 2: Signal Generation Context

#### 2.1 Entry Conditions at Signal Bar
- **VWAP Distance at Entry** - Price distance from VWAP in points/ticks
- **VWAP Distance %** - As percentage of price
- **Volume Delta at Entry** - If absorption logic uses volume delta
- **Bar Range at Entry** - High - Low of signal bar (for low-displacement detection)
- **Bar Volume Percentile** - Volume rank relative to recent N-bar lookback (for high-volume requirement)

**Rationale**: These fields enable post-hoc validation that entries truly matched the intended signal criteria (high volume, low displacement, specific VWAP distance). Also useful for detecting signal degradation if entry conditions drift over time.

#### 2.2 Market State at Entry
- **Session VWAP Value** - Exact VWAP level at entry bar
- **Cumulative Volume** - Session cumulative volume at entry
- **Price vs VWAP Direction** - [ABOVE / BELOW]
- **Recent Trend** - If Pine script tracks trend state (e.g., +1 = uptrend, -1 = downtrend)

**Rationale**: Allows segmentation of trades by market regime (above/below VWAP, trending vs ranging) to identify if edge is regime-specific.

### Priority 3: Risk & Excursion Details

#### 3.1 Excursion Timing
- **Bars to MFE** - Number of bars from entry until maximum favorable excursion reached
- **Bars to MAE** - Number of bars from entry until maximum adverse excursion reached
- **MFE Occurred Before Exit** - Boolean [TRUE if MFE was reached before final exit]
- **MAE Occurred Before Exit** - Boolean [TRUE if MAE was reached before final exit]

**Rationale**: Understanding when MFE/MAE occur relative to trade duration and exit reveals whether exits are premature (closing before peak MFE) or delayed (holding through large MAE).

#### 3.2 Realized vs Potential
- **Exit Efficiency** - Ratio of (Exit PnL / MFE) for winners, (Exit PnL / MAE) for losers
- **Realized R-Multiple** - Exit PnL / Initial Risk (if stop loss is defined)

**Rationale**: Exit efficiency metrics reveal whether the strategy is capturing a good proportion of available moves. Low efficiency suggests exits are too early or too reactive.

### Priority 4: Cost & Slippage Breakdown

#### 4.1 Per-Trade Cost Components
- **Commission Paid (Entry)** - Exact commission paid at entry
- **Commission Paid (Exit)** - Exact commission paid at exit
- **Slippage Estimate (Entry)** - Estimated slippage in USD at entry
- **Slippage Estimate (Exit)** - Estimated slippage in USD at exit
- **Total Trade Cost** - Sum of all transaction costs for the round-trip

**Rationale**: Enables precise cost attribution per trade. Useful for identifying if certain trade durations or times of day incur higher slippage, and for validating total cost assumptions.

### Priority 5: Portfolio Context (If Multi-Symbol)

#### 5.1 Concurrent Trades
- **Active Trades at Entry** - How many other positions were open when this trade entered
- **Max Concurrent Trades** - Peak number of simultaneous open trades during this trade's lifetime

**Rationale**: Important for portfolio-level risk management. Identifies periods of high exposure and enables analysis of whether correlation between symbols is creating unwanted concentration.

---

## Practical Export Recommendations for User

### Option A: TradingView Strategy Tester CSV Export
**Current capability**: TradingView's standard export button provides the 15 standard fields listed above.

**If custom fields are NOT available in UI**:
- Proceed with standard export (already sufficient for Test A, B, C analysis).
- Accept that certain deep diagnostics (exit reason breakdown, MFE timing) will require manual inspection of charts or Pine Script modifications.

### Option B: Pine Script Custom Logging
**If more granular data is needed**:
Modify the V9.1 Pine Script to include `log()` or `table` outputs that capture:
- Entry bar VWAP distance
- Exit reason per trade
- Bars in trade
- Session hour at entry

These can be logged to TradingView's Pine Script output panel and manually transcribed or exported via TradingView's alert system.

**Feasibility**: Medium complexity. Requires Pine Script code changes and may require alerts to export data.

### Option C: Backtest Data via TradingView API (Advanced)
**If programmatic access is available**:
- Use TradingView's broker integration or API (if accessible) to export raw backtest results with extended metadata.
- Most users do not have API access for historical backtest data, so this is typically not viable.

---

## Recommended Configuration for Upcoming Tests

### For Test A, B, C (Realistic Costs, Long Filter, Cross-Instrument):
**Minimum Required Fields**: Standard 15-field TradingView export is **sufficient**.

**Ideal Additional Fields** (if available via custom Pine logging):
1. **Exit Reason** (Target / Stop / Time / Signal Flip / EOD)
2. **Bars in Trade** (per trade, not just average)
3. **Session Hour at Entry** (0-23)
4. **VWAP Distance at Entry** (points or %)

**Rationale**: 
- Exit reason breakdown will reveal if Test B (long-only filter) shifts exit mode distribution.
- Bars in trade will show if cross-instrument tests (Test C) exhibit different trade duration profiles.
- Session hour distribution can identify if MGC/MYM exhibit different intraday patterns than ES/MES/YM.

### Suggested TradingView Export Workflow

#### Step 1: Run Backtest in Strategy Tester
- Apply V9.1 strategy to the instrument
- Configure commission & slippage per Test A specifications
- Set date range (1-year + recent regime)

#### Step 2: Review Summary Metrics
Before exporting CSV, screenshot or note the **Overview** tab metrics:
- Net Profit
- Total Closed Trades
- Percent Profitable
- Profit Factor
- Max Drawdown
- Average Trade
- Average # Bars in Trade
- Sharpe Ratio (if available)

**Rationale**: These summary metrics sometimes contain fields (like Sharpe Ratio or Average Bars in Trade) that are not included in the per-trade CSV export.

#### Step 3: Export Trade List CSV
- Click **List of Trades** tab
- Export to CSV
- Verify the CSV contains all 15 standard fields

#### Step 4: (Optional) Extract Additional Fields via Pine Script Logging
If you need:
- Per-trade exit reason
- Entry VWAP distance
- Session hour

Modify V9.1 Pine script to output these via:
```pine
if strategy.position_size[1] != 0 and strategy.position_size == 0
    log.info("EXIT | Reason: " + exit_reason + " | Bars: " + str.tostring(bar_index - entry_bar))
```

Then manually export from Pine Logs or set up alerts to capture the data.

---

## Summary: Data Sufficiency Assessment

| Analysis Requirement                     | Standard CSV | +Exit Reason | +Session Hour | +VWAP Distance |
|------------------------------------------|--------------|--------------|---------------|----------------|
| Test A: Cost impact on PnL, PF, Exp      | ✅ Sufficient | -            | -             | -              |
| Test B: Long-filter performance          | ✅ Sufficient | ⭐ Helpful   | -             | -              |
| Test C: Cross-instrument generalization  | ✅ Sufficient | ⭐ Helpful   | ⭐ Helpful    | ⭐ Helpful     |
| Exit mode distribution analysis          | ❌ Limited    | ✅ Required  | -             | -              |
| Time-of-day concentration analysis       | ❌ Limited    | -            | ✅ Required   | -              |
| Entry signal validation                  | ❌ Limited    | -            | -             | ✅ Required    |

**Recommendation for Upcoming Tests**:
- **Minimum**: Export standard TradingView CSV (15 fields) → **Sufficient for Test A, B, C core analysis**
- **Optional Enhancement**: If feasible, add per-trade exit reason and session hour via Pine logging → **Enables deeper diagnostics**

---

## Quick Reference: Field Request Template

If you have the ability to customize TradingView export or modify Pine Script logging, request/add these fields in priority order:

### Tier 1 (High Value, Moderate Effort)
1. **Exit Reason** (string: "Target", "Stop", "Time", "Signal", "EOD")
2. **Bars in Trade** (integer)
3. **Session Hour at Entry** (integer 0-23)

### Tier 2 (Medium Value, Higher Effort)
4. **VWAP Distance at Entry** (float, in points or %)
5. **Bar Range at Entry** (float, High - Low)
6. **Bars to MFE** (integer)
7. **Bars to MAE** (integer)

### Tier 3 (Nice to Have, Significant Effort)
8. **Entry Bar Volume Percentile** (float 0-100)
9. **Exit Efficiency Ratio** (float)
10. **Realized R-Multiple** (float)

---

**Document Status**: Ready for user review before running TradingView tests.  
**Last Updated**: 2026-06-05  
**Analyst**: Neo (Agent Handoff)

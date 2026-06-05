# V10 Enhancement Guide

**Pine Script Version**: V10 Research Build  
**Base**: V9.1 Live-Ready Engine  
**Purpose**: Testable enhancements for isolated A/B testing in TradingView  
**Date**: 2026-06-05

---

## Overview

V10 adds 7 toggleable enhancements on top of the validated V9.1 baseline. Each enhancement addresses a specific hypothesis about improving strategy performance (profit factor, expectancy, drawdown, or win rate) while maintaining the core absorption + VWAP reversion logic.

**Critical**: Default settings have ALL enhancements OFF. This allows you to verify that V10 with defaults produces identical results to V9.1, establishing a trusted baseline before testing enhancements.

---

## Baseline Validation Protocol

### Step 1: Verify V10 = V9.1 Baseline
1. Load V10 script in TradingView
2. Verify all enhancement toggles are OFF (default state):
   - `enableHtfFilter` = false
   - `enableVolFilter` = false
   - `enableDecayExit` = false
   - `enableTrailStop` = false
   - `enablePartialExit` = false
   - `enableScoreFilter` = false
3. Set all other inputs to match your V9.1 configuration (preset, session filters, risk gates, etc.)
4. Run backtest on ES 3-minute ETH for 1-year period
5. Compare results to V9.1 baseline:
   - **Total Trades** should match exactly
   - **Net PnL** should match within rounding ($1-2 variance acceptable due to fill timing)
   - **Profit Factor** should match to 2 decimal places
   - **Max Drawdown** should match to 2 decimal places

**If baseline does NOT match**: Contact support. V10 has a logic bug.

**If baseline matches**: Proceed to enhancement testing.

---

## Enhancement Testing Protocol

For each enhancement:
1. **Isolate**: Enable ONLY that enhancement, keep all others OFF
2. **Backtest**: Run full 1-year + recent period tests
3. **Metrics**: Compare to V10 baseline (all OFF):
   - Net PnL delta
   - Profit Factor delta
   - Max Drawdown delta
   - Total trades delta
   - Win rate delta
   - Average bars in trade delta
4. **Document**: Record which symbols and periods showed improvement
5. **Hypothesis**: Note whether results support or reject the enhancement hypothesis

After testing all 7 individually, test promising combinations (e.g., HTF Filter + Vol Filter).

---

## Enhancement A: Higher-Timeframe Trend Filter

### What It Does
Fetches price data from a higher timeframe (default 60-minute) to determine trend bias. Blocks absorption signals that fade against strong trends.

**Logic**:
- **EMA method**: Compares fast EMA (default 20) vs slow EMA (default 50) on HTF
- **VWAP method**: Compares current price vs HTF session VWAP
- Calculates separation in ATR units
- If separation > threshold (default 0.5 ATR):
  - Blocks short fades when HTF trend is strongly UP
  - Blocks long fades when HTF trend is strongly DOWN
  - Allows all signals when HTF trend is NEUTRAL

### Hypothesis
**Absorption-against-trend signals have lower win rate than absorption-in-neutral-or-counter-trend signals.**

Reasoning: Post-absorption mean reversion works best when the larger trend is not overwhelming. Fading strong trends increases the risk of getting run over.

### When to Enable
Enable if you suspect V9.1 is taking too many counter-trend signals during strong directional sessions, leading to large stop-outs.

### Input Configuration
| Input | Default | Recommendation |
|-------|---------|----------------|
| `enableHtfFilter` | false | **true** to test |
| `htfTimeframe` | "60" | 60 for ES/YM; 30 for faster instruments |
| `htfTrendMethod` | "EMA" | EMA for trend-following; VWAP for intraday bias |
| `htfEmaFast` | 20 | 20 (standard) |
| `htfEmaSlow` | 50 | 50 (standard) |
| `htfTrendThresh` | 0.5 | 0.5 ATR (moderate); 1.0 ATR (strict) |

### Expected Impact
- **Fewer trades**: 10-30% reduction (blocks strong-trend signals)
- **Higher win rate**: +2-5% if hypothesis is correct
- **Lower max drawdown**: Avoids large trend-following losses
- **Profit factor**: Should improve if avoided trades were net-negative

### How to Interpret Results
✅ **Success**: PF improves by ≥0.10, win rate improves, DD decreases  
⚠️ **Mixed**: Trades decrease significantly but PF unchanged → filter too strict  
❌ **Failure**: PF degrades, win rate decreases → absorption works BETTER against trend (counter-hypothesis)

### Dashboard Indicator
Row 12: "HTF Trend"
- Shows: UP / DOWN / NEUTRAL (or OFF if disabled)
- Color: Yellow if trend active, gray if disabled
- Detail: Trend strength in ATR units, HTF timeframe and method

---

## Enhancement B: Volatility Regime Filter

### What It Does
Computes ATR percentile over a rolling lookback window (default 100 bars). Blocks signals when volatility is outside the acceptable range.

**Logic**:
- Calculates 14-period ATR percentile rank vs last 100 bars
- Blocks signals if ATR percentile < `minVolPercentile` (default 25)
- Blocks signals if ATR percentile > `maxVolPercentile` (default 90)

### Hypothesis
**Absorption strategies fail in extreme volatility regimes: too low (chop) and too high (event risk).**

Reasoning:
- **Low vol** (chop): High volume but low displacement may be intrabar noise, not true absorption
- **High vol** (event risk): Volatility spikes from news/macro → mean reversion breaks down, trends extend

### When to Enable
Enable if V9.1 shows poor performance during:
- Pre-market low-volatility grind sessions
- Post-Fed announcement explosive moves

### Input Configuration
| Input | Default | Recommendation |
|-------|---------|----------------|
| `enableVolFilter` | false | **true** to test |
| `volLookback` | 100 | 100 bars (standard) |
| `minVolPercentile` | 25.0 | 25th percentile (avoids bottom quartile chop) |
| `maxVolPercentile` | 90.0 | 90th percentile (avoids top decile event risk) |

### Expected Impact
- **Fewer trades**: 15-25% reduction
- **Higher expectancy**: Avoids low-quality chop and high-risk events
- **More stable equity curve**: Reduces large outlier losses

### How to Interpret Results
✅ **Success**: Expectancy improves, fewer large losses, PF improves  
⚠️ **Mixed**: Trades decrease but performance flat → filter neutral  
❌ **Failure**: PF degrades → absorption works across all vol regimes

### Dashboard Indicator
Row 13: "Vol Regime"
- Shows: ATR percentile (0-100) or OFF
- Color: Green if pass, red if blocked, gray if disabled
- Detail: Min-Max range, PASS/BLOCK status

---

## Enhancement C: Time-Decay Exit

### What It Does
Replaces the fixed ATR stop with a progressively tightening stop if the trade shows no progress toward the VWAP target by mid-horizon.

**Logic**:
- After `decayStartBars` (default 5) bars in trade, checks progress toward VWAP target
- If progress < 30% of total distance, begins tightening stop
- Stop decays linearly from original ATR stop toward entry price
- At `decayEndBars` (default 15), stop is 70% closer to entry than original stop

### Hypothesis
**Trades that haven't moved toward target by mid-horizon are less likely to recover. Reducing risk on slow trades improves risk-adjusted returns.**

Reasoning: If absorption signal was correct, price should begin moving toward VWAP within first 5-10 bars. Trades that stall may be false signals or overwhelmed by other forces.

### When to Enable
Enable if V9.1 shows many trades that:
- Hit time stop at full loss (horizon reached without movement)
- Slowly grind against position before final stop-out

### Input Configuration
| Input | Default | Recommendation |
|-------|---------|----------------|
| `enableDecayExit` | false | **true** to test |
| `decayStartBars` | 5 | 5 bars (⅓ of 15-bar horizon) |
| `decayEndBars` | 15 | Match `effReversalHorizonBars` (default 15) |

### Expected Impact
- **Smaller average loss**: Cuts losses earlier on stalled trades
- **Lower max drawdown**: Prevents full ATR stop-outs on slow losers
- **Profit factor**: Should improve if losing trades are trimmed
- **Trade count**: Unchanged (affects exits only)

### How to Interpret Results
✅ **Success**: Avg loss decreases, PF improves, DD improves  
⚠️ **Mixed**: Avg loss decreases but so does avg win (cutting winners early too)  
❌ **Failure**: Avg loss unchanged or PF degrades → trades need full horizon

### Dashboard Indicator
Row 15: "Enhancements" → Shows "DECAY" if enabled  
Row 15 Detail: Shows current effective stop price when in trade

---

## Enhancement D: Trailing Stop on Favorable Excursion

### What It Does
Once trade has moved favorably by a threshold (default 0.5 ATR), replaces the original stop with a trailing stop that follows price at a distance (default 1.0 ATR).

**Logic**:
- Monitors unrealized profit on open position
- When favorable move ≥ `trailActivationAtr` (default 0.5 ATR), activates trailing stop
- Trailing stop follows price at `trailDistanceAtr` (default 1.0 ATR) behind current price
- For longs: stop trails below price; for shorts: stop trails above price
- Stop only moves in favorable direction (never loosens)

### Hypothesis
**Trades that exceed average favorable excursion should lock in partial gains. Trailing stops capture extended moves while protecting profits.**

Reasoning: V9.1 uses fixed VWAP target or time exit. Some trades overshoot VWAP significantly. Trailing stop allows capturing extended moves while protecting against reversals.

### When to Enable
Enable if V9.1 shows:
- Many trades with large MFE (favorable excursion) that later reverse and hit stops
- Winners that reach VWAP then continue beyond, leaving money on table

### Input Configuration
| Input | Default | Recommendation |
|-------|---------|----------------|
| `enableTrailStop` | false | **true** to test |
| `trailActivationAtr` | 0.5 | 0.5 ATR (activates on moderate winners) |
| `trailDistanceAtr` | 1.0 | 1.0 ATR (standard stop distance) |

### Expected Impact
- **Higher average win**: Captures extended moves beyond VWAP
- **Fewer VWAP limit fills**: Some trades will trail and exit before hitting VWAP
- **Profit factor**: Should improve if extension trades are common
- **Trade count**: Unchanged

### How to Interpret Results
✅ **Success**: Avg win increases, PF improves, MFE captured more efficiently  
⚠️ **Mixed**: Avg win increases but win rate decreases (some trades hit trail before VWAP)  
❌ **Failure**: Avg win unchanged or PF degrades → most moves stop at VWAP

### Dashboard Indicator
Row 15: "Enhancements" → Shows "TRAIL" if enabled  
Row 15 Detail: Shows trailing stop price when active

---

## Enhancement E: Multi-Contract Partial Exit

### What It Does
**Requires `paperQty` ≥ 2**. Exits a fraction of the position (default 50%) at a first target (default 0.5 ATR), holds the "runner" to VWAP target with a breakeven stop.

**Logic**:
- When trade moves `tp1AtrDistance` (default 0.5 ATR) in favor, exits `tp1Fraction` (default 0.5 = half) of contracts
- Remaining runner continues with:
  - VWAP limit exit (original target)
  - Breakeven stop (entry price) or original stop, whichever is more favorable
- Only fires once per trade (first TP1 hit)

### Hypothesis
**Scaling out improves risk-reward by banking early wins while holding runners for full target.**

Reasoning: Not all signals reach VWAP. Partial exit ensures some profit capture on partial moves, while runner participates in full reversions.

### When to Enable
Enable if:
- You trade ≥2 contracts
- V9.1 shows many trades that move halfway to VWAP then reverse

### Input Configuration
| Input | Default | Recommendation |
|-------|---------|----------------|
| `enablePartialExit` | false | **true** to test (requires qty ≥2) |
| `tp1Fraction` | 0.5 | 0.5 (exit half at TP1) |
| `tp1AtrDistance` | 0.5 | 0.5 ATR (early target); 0.75 for more conservative |
| `paperQty` | 1 | **Set to 2 or more** |

### Expected Impact
- **More wins**: TP1 converts partial moves into wins that would have reversed
- **Lower average win**: Full position doesn't always ride to VWAP
- **Lower max drawdown**: Runner breakeven stop reduces risk
- **Profit factor**: Likely improves due to more wins and smaller losses
- **Expectancy**: May decrease per contract but increase risk-adjusted

### How to Interpret Results
✅ **Success**: Win rate increases significantly, PF improves, DD decreases  
⚠️ **Mixed**: Win rate improves but net PnL decreases (TP1 too early)  
❌ **Failure**: Win rate improves but expectancy worse → full position to VWAP is better

### Dashboard Indicator
Row 15: "Enhancements" → Shows "PART" if enabled  
Row 15 Note: Shows "TP1 fired" when partial exit has occurred

---

## Enhancement F: Signal-Quality Score Filter

### What It Does
Computes a composite quality score (0-100) for each absorption signal based on:
1. **Volume excess**: How far above threshold percentile
2. **Displacement ratio**: How "tight" the absorption (lower = better)
3. **VWAP distance**: How extended price is from VWAP (further = better reversion setup)
4. **Time-of-day**: Best trading windows score higher (opening/closing hours)

Only takes signals scoring ≥ `minSignalScore` (default 60).

**Logic**:
```
volumeScore       = (volumePercentile - threshold) × 10 (capped at 100)
displacementScore = 100 if ≤0.1 ATR, 75 if ≤0.3, 50 if ≤0.5, else 25
vwapDistanceScore = |VWAP distance / ATR| × 100 (capped at 100)
timeOfDayScore    = 100 if 9:30-10:30 or 13:30-15:30, else 80 if 13:00-15:00, else 50

signalScore = volumeScore × 0.3 + displacementScore × 0.3 + vwapDistanceScore × 0.2 + timeScore × 0.2
```

### Hypothesis
**Not all absorption signals are equal. Ranking signals by composite quality and filtering low-scorers improves expectancy.**

Reasoning: Some absorption bars are marginal (barely meet thresholds), while others are extreme outliers. Filtering to top-quality signals should increase win rate and reduce false positives.

### When to Enable
Enable if V9.1 shows:
- Many marginal signals that barely meet thresholds
- Win rate varies significantly by time-of-day or VWAP distance

### Input Configuration
| Input | Default | Recommendation |
|-------|---------|----------------|
| `enableScoreFilter` | false | **true** to test |
| `minSignalScore` | 60.0 | 60 (moderate); 70-80 (strict) |
| `scoreWeightVol` | 0.3 | 0.3 (volume is critical) |
| `scoreWeightDisp` | 0.3 | 0.3 (displacement is critical) |
| `scoreWeightDist` | 0.2 | 0.2 (VWAP distance helps) |
| `scoreWeightTime` | 0.2 | 0.2 (time-of-day helps) |

### Expected Impact
- **Fewer trades**: 20-40% reduction (filters low-quality signals)
- **Higher win rate**: Significantly higher if quality scoring works
- **Higher profit factor**: Top signals should be more reliable
- **Expectancy**: Should improve if low-scorers are net-negative

### How to Interpret Results
✅ **Success**: Win rate improves >5%, PF improves significantly, fewer but better trades  
⚠️ **Mixed**: Trades decrease but performance flat → scoring neutral  
❌ **Failure**: Win rate unchanged or PF degrades → all signals are equal quality

### Dashboard Indicator
Row 14: "Signal Score"
- Shows: Current bar's score (0-100) or OFF
- Color: Green if pass threshold, red if blocked, gray if disabled
- Detail: Minimum score threshold, PASS/BLOCK status

---

## Enhancement G: Dashboard Score Display

### What It Does
Adds 3 rows to the dashboard (rows 12-14) displaying real-time telemetry from the active enhancements:
- Row 12: HTF trend bias (UP/DOWN/NEUTRAL), trend strength, timeframe
- Row 13: ATR percentile, vol range, pass/block status
- Row 14: Signal quality score, min threshold, pass/block status
- Row 15: Active enhancements list, effective stop price, TP1 status

### Purpose
Visual confirmation that enhancements are functioning during forward testing or live trading. Helps diagnose why signals are blocked or allowed.

**Always ON** when any enhancement is enabled. No separate toggle.

---

## Testing Workflow

### Phase 1: Baseline Verification (Critical)
1. Load V10 with all enhancements OFF
2. Backtest ES 3m ETH, 1-year period
3. Verify results match V9.1 exactly
4. **Do not proceed until baseline matches**

### Phase 2: Individual Enhancement Tests
For each enhancement (A through F):
1. Enable ONLY that enhancement
2. Run backtest on ES 3m ETH, 1-year + recent
3. Export CSV and document:
   - Net PnL vs baseline
   - PF vs baseline
   - Win rate vs baseline
   - Max DD vs baseline
   - Total trades vs baseline
4. Verdict: PASS (improve), NEUTRAL (no change), FAIL (degrade)

### Phase 3: Cross-Instrument Validation
For enhancements that PASS on ES:
1. Test on MES, YM (same enhancement, same inputs)
2. Verify enhancement generalizes across instruments
3. Document any instrument-specific tuning needed

### Phase 4: Combination Testing
Combine enhancements that individually PASS:
- Start with pairs (e.g., HTF + Vol)
- Test triples if pairs work
- Goal: Find the optimal enhancement stack

### Phase 5: Cost Verification
Run winning enhancement combinations with realistic costs:
- ES: $2.50 comm + 2 tick slip
- MES: $1.25 comm + 2 tick slip
- YM: $2.50 comm + 4 tick slip
- Verify edge survives costs

---

## Common Pitfalls

### 1. Testing Multiple Enhancements Simultaneously
❌ **Wrong**: Enable HTF + Vol + Score all at once  
✅ **Right**: Test each individually first to isolate impact

### 2. Not Verifying Baseline
❌ **Wrong**: Assume V10 = V9.1 and start testing enhancements  
✅ **Right**: Verify V10 with all OFF matches V9.1 exactly

### 3. Overfitting to One Period
❌ **Wrong**: Optimize enhancement inputs on 1-year period only  
✅ **Right**: Test on 1-year, verify on recent regime, validate on holdout

### 4. Ignoring Trade Count Changes
❌ **Wrong**: Focus only on PF/expectancy  
✅ **Right**: Check if trade count dropped significantly (fewer signals = less robust)

### 5. Not Testing with Realistic Costs
❌ **Wrong**: Declare enhancement successful without cost check  
✅ **Right**: Always re-run with commissions and slippage before final verdict

---

## Expected Outcomes by Enhancement

| Enhancement | Trade Δ | PF Δ | WR Δ | DD Δ | Hypothesis Likelihood |
|-------------|---------|------|------|------|-----------------------|
| A: HTF Trend | -20% | +0.10 | +3% | -15% | **High** (trend-against is risky) |
| B: Vol Regime | -20% | +0.05 | +2% | -10% | **Medium** (regime matters) |
| C: Decay Exit | 0% | +0.08 | 0% | -10% | **High** (cut slow losers) |
| D: Trail Stop | 0% | +0.05 | -1% | 0% | **Medium** (if extensions common) |
| E: Partial Exit | 0% | +0.10 | +5% | -15% | **High** (scale-out improves RR) |
| F: Score Filter | -30% | +0.15 | +5% | -20% | **High** (quality over quantity) |

**Note**: These are directional expectations, not guarantees. Your actual results will vary by symbol, period, and market regime.

---

## Recommended Testing Order

1. **Enhancement C (Decay Exit)** — Easiest to interpret, immediate DD benefit if working
2. **Enhancement E (Partial Exit)** — Requires qty ≥2 but high likelihood of improvement
3. **Enhancement F (Score Filter)** — Biggest potential impact (quality filtering)
4. **Enhancement A (HTF Trend)** — Strong hypothesis, widely applicable
5. **Enhancement B (Vol Regime)** — Regime awareness is valuable
6. **Enhancement D (Trail Stop)** — Test last (most dependent on instrument behavior)

---

## Final Notes

- **V10 is a research tool, not a production release.** Do not deploy to live trading until you've validated enhancements in forward testing.
- **Document everything.** Keep a spreadsheet of each backtest result. Track which enhancements work, which don't, and why.
- **Be skeptical of large improvements.** If an enhancement improves PF by >0.30 in backtest, it may be overfitted. Verify on holdout data.
- **Timeframe matters.** V10 is designed for 3-minute ETH (validated timeframe). Do not test on other timeframes without re-validating the core absorption logic first.
- **Combine with V9.1 real-test CSVs.** Once you run the 3 focused tests (costs, long-filter, cross-instrument) on V9.1, compare those results to V10 with enhancements enabled. This gives you a full picture of production readiness.

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-05  
**Author**: Neo (Research Agent)

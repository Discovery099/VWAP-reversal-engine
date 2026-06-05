# V10 Quick Reference

**Pine Script**: `problem_0004_absorption_vwap_v10.pine`  
**Guide**: `V10_ENHANCEMENT_GUIDE.md`  
**Status**: Research Build — Ready for TradingView Backtesting

---

## What Changed from V9.1 → V10

✅ **All V9.1 logic preserved** (risk gates, EOD flatten, next-bar entry, webhook payload)  
✅ **7 new toggleable enhancements** (all default OFF)  
✅ **Enhanced dashboard** (rows 12-15 show enhancement telemetry)  
✅ **Baseline reproducibility** (V10 with all OFF = V9.1 exactly)

---

## The 7 Enhancements

| ID | Name | Default | Input Group | Purpose |
|----|------|---------|-------------|---------|
| A | HTF Trend Filter | OFF | 11 Enhancement A | Block signals against strong higher-timeframe trends |
| B | Volatility Regime | OFF | 12 Enhancement B | Skip signals in extreme vol (too low = chop, too high = event) |
| C | Time-Decay Exit | OFF | 13 Enhancement C | Tighten stop on trades that stall (no progress to target) |
| D | Trailing Stop | OFF | 14 Enhancement D | Lock in winners that exceed activation threshold |
| E | Partial Exit | OFF | 15 Enhancement E | Scale out at TP1, hold runner to VWAP (needs qty ≥2) |
| F | Signal Quality Score | OFF | 16 Enhancement F | Filter signals by composite quality score |
| G | Dashboard Display | Auto | N/A | Shows enhancement telemetry in rows 12-15 |

---

## How to Use

### Step 1: Load V10 in TradingView
1. Copy `problem_0004_absorption_vwap_v10.pine` into TradingView Pine Editor
2. Click "Add to Chart"
3. Symbol: ES, MES, or YM (3-minute chart, ETH session)

### Step 2: Verify Baseline (Critical)
1. Open strategy settings
2. Verify all enhancement toggles are OFF:
   - Group 11: `enableHtfFilter` = false
   - Group 12: `enableVolFilter` = false
   - Group 13: `enableDecayExit` = false
   - Group 14: `enableTrailStop` = false
   - Group 15: `enablePartialExit` = false
   - Group 16: `enableScoreFilter` = false
3. Set all other inputs to match your V9.1 configuration
4. Run backtest (1-year period)
5. **Verify**: Net PnL, PF, trades, DD match V9.1 within rounding

**If baseline does not match**: Stop. Contact support. V10 has a bug.

### Step 3: Test Enhancements (One at a Time)
1. Enable ONE enhancement
2. Run backtest
3. Export CSV
4. Compare to V10 baseline:
   - Net PnL delta
   - Profit Factor delta
   - Win Rate delta
   - Max Drawdown delta
   - Trade count delta
5. Document: PASS / NEUTRAL / FAIL
6. Disable that enhancement, enable next one
7. Repeat for all 7

### Step 4: Test Combinations
1. Combine enhancements that individually PASS
2. Test pairs, then triples
3. Find optimal stack

### Step 5: Validate with Costs
1. Add realistic commissions and slippage
2. Re-run backtest with winning enhancement stack
3. Verify edge survives costs

---

## Input Quick Reference

### Enhancement A: HTF Trend Filter
```
enableHtfFilter = true
htfTimeframe = "60"         // 60 min for ES/YM
htfTrendMethod = "EMA"      // EMA or VWAP
htfEmaFast = 20
htfEmaSlow = 50
htfTrendThresh = 0.5        // ATR multiple for "strong trend"
```

### Enhancement B: Volatility Regime
```
enableVolFilter = true
volLookback = 100
minVolPercentile = 25.0     // Block if ATR < 25th percentile
maxVolPercentile = 90.0     // Block if ATR > 90th percentile
```

### Enhancement C: Time-Decay Exit
```
enableDecayExit = true
decayStartBars = 5          // Start decay at 5 bars (⅓ horizon)
decayEndBars = 15           // Full decay at 15 bars (match horizon)
```

### Enhancement D: Trailing Stop
```
enableTrailStop = true
trailActivationAtr = 0.5    // Activate trail after 0.5 ATR favorable
trailDistanceAtr = 1.0      // Trail 1.0 ATR behind price
```

### Enhancement E: Partial Exit
```
enablePartialExit = true
tp1Fraction = 0.5           // Exit 50% at TP1
tp1AtrDistance = 0.5        // TP1 at 0.5 ATR
paperQty = 2                // REQUIRED: qty ≥ 2
```

### Enhancement F: Signal Quality Score
```
enableScoreFilter = true
minSignalScore = 60.0       // Only take signals ≥60 score
scoreWeightVol = 0.3
scoreWeightDisp = 0.3
scoreWeightDist = 0.2
scoreWeightTime = 0.2
```

---

## Dashboard Guide (Rows 12-15)

### Row 12: HTF Trend (Enhancement A)
- **Value**: UP / DOWN / NEUTRAL (or OFF)
- **Detail**: Trend strength (ATR units)
- **Notes**: Timeframe and method (e.g., "60m EMA")

### Row 13: Vol Regime (Enhancement B)
- **Value**: ATR percentile (0-100) or OFF
- **Detail**: Min-Max range (e.g., "25-90")
- **Notes**: PASS / BLOCK

### Row 14: Signal Score (Enhancement F)
- **Value**: Score (0-100) or OFF
- **Detail**: Min threshold (e.g., "min 60")
- **Notes**: PASS / BLOCK

### Row 15: Enhancements Summary
- **Value**: Active enhancements list (e.g., "HTF VOL DECAY")
- **Detail**: Effective stop price (when in trade)
- **Notes**: "TP1 fired" (if Enhancement E partial exit occurred)

---

## Expected Results (Directional)

| Enhancement | Hypothesis | Likely Δ Trades | Likely Δ PF | Likely Δ WR | Likely Δ DD |
|-------------|------------|-----------------|-------------|-------------|-------------|
| A: HTF      | Fade-against-trend loses | -20% | +0.10 | +3% | -15% |
| B: Vol      | Extreme vol = bad setups | -20% | +0.05 | +2% | -10% |
| C: Decay    | Cut slow losers early | 0% | +0.08 | 0% | -10% |
| D: Trail    | Capture extended moves | 0% | +0.05 | -1% | 0% |
| E: Partial  | Scale-out improves RR | 0% | +0.10 | +5% | -15% |
| F: Score    | Quality > quantity | -30% | +0.15 | +5% | -20% |

**Note**: These are hypotheses, not guarantees. Your results will vary.

---

## Testing Checklist

- [ ] V10 baseline matches V9.1 (all enhancements OFF)
- [ ] Enhancement A tested individually
- [ ] Enhancement B tested individually
- [ ] Enhancement C tested individually
- [ ] Enhancement D tested individually
- [ ] Enhancement E tested individually (with qty ≥2)
- [ ] Enhancement F tested individually
- [ ] Passing enhancements tested in combination
- [ ] Winning stack tested with realistic costs
- [ ] Results documented in spreadsheet
- [ ] Cross-instrument validation (ES, MES, YM)

---

## Common Mistakes

❌ Testing multiple enhancements at once (can't isolate impact)  
❌ Not verifying baseline first (trust but verify)  
❌ Ignoring trade count changes (fewer trades = less robust)  
❌ Declaring success without cost check (costs matter)  
❌ Overfitting to one period (validate on holdout)

---

## Files in This Package

```
/app/problem_0004_absorption_vwap/pine/
├── problem_0004_absorption_vwap_v10.pine    # Pine Script V10
├── V10_ENHANCEMENT_GUIDE.md                 # Full guide (this document's parent)
└── V10_QUICK_REFERENCE.md                   # This quick reference
```

---

## Next Steps After Testing

1. **Document Results**: Create a spreadsheet of all enhancement test results
2. **Select Winners**: Choose enhancements that improve PF ≥0.10 and pass cost check
3. **Backport to Python** (optional): If you want to upgrade the research_engine to V10 logic
4. **Forward Test**: Paper trade winning enhancement stack for 2-4 weeks
5. **Go Live**: Only after forward test confirms backtest results

---

## Support

If V10 baseline does not match V9.1, or if any enhancement behaves unexpectedly, review:
1. Input settings (verify all match V9.1 baseline)
2. Symbol and timeframe (must be 3m ETH)
3. Date range (ensure same period as V9.1 test)
4. TradingView version (Pine Script v6 required)

---

**Version**: 1.0  
**Date**: 2026-06-05  
**Purpose**: Research Tool — Not for Live Trading Until Validated

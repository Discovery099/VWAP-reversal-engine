# Analysis Template: Three Focused TradingView Tests

**Document Purpose**: Structured analytical framework for evaluating the three upcoming TradingView test results.

**Date Created**: 2026-06-05  
**Status**: AWAITING CSV UPLOADS

---

## Test A: Realistic Execution Costs Impact

### Objective
Quantify how much edge survives when realistic execution costs (commissions + slippage) are applied to ES, MES, and YM.

### Baseline Reference (Cost-Free Results from Prior Analysis)
| Symbol | Period | Trades | Net PnL | PF | Expectancy | Win Rate |
|--------|--------|--------|---------|----|-----------|---------:|
| ES     | 1-year | TBD    | TBD     | TBD| TBD       | TBD      |
| ES     | Recent | TBD    | TBD     | TBD| TBD       | TBD      |
| MES    | 1-year | TBD    | TBD     | TBD| TBD       | TBD      |
| MES    | Recent | TBD    | TBD     | TBD| TBD       | TBD      |
| YM     | 1-year | TBD    | TBD     | TBD| TBD       | TBD      |
| YM     | Recent | TBD    | TBD     | TBD| TBD       | TBD      |

**Note**: Populate baseline from the original 6 TradingView CSVs analyzed in Enhancement Assessment Document.

### Test Configuration
- **ES**: Commission = $2.50/side, Slippage = 2 ticks (0.50 points = $25)
- **MES**: Commission = $1.25/side, Slippage = 2 ticks (0.50 points = $2.50)
- **YM**: Commission = $2.50/side, Slippage = 4 ticks (4 points = $20)

### Analysis Framework

#### A.1 Absolute Cost Impact
For each symbol and period:
```
Gross PnL         = [from cost-free baseline]
Total Costs       = (Commissions + Slippage) × Number of Trades × 2
Net PnL (costs)   = [from new CSV with costs applied]
Cost Drag         = Total Costs / Gross PnL (%)
```

#### A.2 Metric Degradation
Compare key metrics before and after costs:
```
ΔProfit Factor    = PF_baseline - PF_with_costs
ΔExpectancy       = Exp_baseline - Exp_with_costs
ΔWin Rate         = WR_baseline - WR_with_costs
ΔMax DD           = DD_with_costs - DD_baseline
```

#### A.3 Viability Assessment
For each symbol, determine:
- Does Net PnL remain positive after costs?
- Does PF remain above 1.20 after costs?
- Does Expectancy remain above $0/trade after costs?
- Which symbol is most/least sensitive to execution costs?

#### A.4 Recent Regime Resilience
```
Recent PF Ratio   = PF_recent_with_costs / PF_1year_with_costs
Recent Exp Ratio  = Exp_recent_with_costs / Exp_1year_with_costs
```
- If Recent Ratio < 0.85 → regime degradation under costs
- If Recent Ratio ≥ 1.00 → costs do not harm recent edge

### Expected Output Structure
```markdown
## Test A Results: Realistic Execution Costs

### ES (E-mini S&P 500)
- **Cost Configuration**: $2.50 comm/side, 2-tick slippage ($25)
- **1-Year Period**
  - Baseline (cost-free): [Trades], [Net PnL], [PF], [Exp]
  - With Costs: [Trades], [Net PnL], [PF], [Exp]
  - Cost Drag: [X%], ΔPF: [Y], ΔExp: [Z]
  - Verdict: [VIABLE / MARGINAL / NON-VIABLE]
- **Recent Period**
  - With Costs: [Net PnL], [PF], [Exp]
  - Recent Resilience: [Ratio analysis]
  - Verdict: [statement]

### MES (Micro E-mini S&P 500)
[Same structure as ES]

### YM (E-mini Dow)
[Same structure as ES]

### Cross-Symbol Comparison
- Most cost-sensitive: [Symbol] ([X%] drag)
- Most cost-resilient: [Symbol] ([Y%] drag)
- Rank by post-cost Sharpe/Expectancy: [1. X, 2. Y, 3. Z]

### Overall Test A Verdict
[Does the V9.1 strategy retain economic viability under realistic costs? Which symbols pass the cost filter?]
```

---

## Test B: Long-Side Filter Analysis

### Objective
Determine whether removing short trades from ES/MES improves combined portfolio metrics, while confirming YM benefits from both-sides trading.

### Baseline Reference (Both-Sides Results)
| Symbol | Period | Longs | Shorts | Long WR | Short WR | Long Exp | Short Exp | Combined PF |
|--------|--------|-------|--------|---------|----------|----------|-----------|-------------|
| ES     | 1-year | TBD   | TBD    | TBD     | TBD      | TBD      | TBD       | TBD         |
| MES    | 1-year | TBD   | TBD    | TBD     | TBD      | TBD      | TBD       | TBD         |
| YM     | 1-year | TBD   | TBD    | TBD     | TBD      | TBD      | TBD       | TBD         |

### Test Configuration
- **ES**: LONGS ONLY
- **MES**: LONGS ONLY
- **YM**: BOTH SIDES (control group)

### Analysis Framework

#### B.1 ES/MES Long-Only Metrics
From new CSVs, extract:
```
Long_Only_Trades     = [count from CSV]
Long_Only_Net_PnL    = [from CSV]
Long_Only_PF         = [from CSV]
Long_Only_Expectancy = [from CSV]
Long_Only_Win_Rate   = [from CSV]
Long_Only_Max_DD     = [from CSV]
```

Compare to baseline both-sides:
```
Δ Trades     = Long_Only_Trades - (Baseline_Longs + Baseline_Shorts)
Δ Net_PnL    = Long_Only_Net_PnL - Baseline_Net_PnL
Δ PF         = Long_Only_PF - Baseline_PF
Δ Expectancy = Long_Only_Expectancy - Baseline_Expectancy
```

#### B.2 Short Trade Contribution Analysis
For ES/MES baseline (from prior CSVs):
```
Short_Trade_PnL   = [sum of all short trades from original CSV]
Short_Trade_Count = [count of short trades]
Short_Avg_PnL     = Short_Trade_PnL / Short_Trade_Count
Short_Win_Rate    = [from original CSV analysis]
```

If `Short_Avg_PnL < 0` or `Short_Win_Rate < 40%`:
→ Shorts are dragging down portfolio performance.

#### B.3 YM Control Validation
Confirm YM both-sides metrics in new test match prior results:
- If YM metrics shift significantly → test setup issue
- If YM remains stable → validates test environment

#### B.4 Portfolio-Level Impact
If filtering ES/MES to longs-only:
```
Portfolio_Net_PnL_Both_Sides  = ES_both + MES_both + YM_both
Portfolio_Net_PnL_Long_Filter = ES_long + MES_long + YM_both

Portfolio_Improvement         = Long_Filter - Both_Sides
Portfolio_PF_Improvement      = PF_Long_Filter - PF_Both_Sides
```

### Expected Output Structure
```markdown
## Test B Results: Long-Side Filter

### ES Long-Only Analysis
- **Baseline (Both Sides)**: [Trades], [Net PnL], [PF], [Exp], [WR]
  - Long trades: [count], [avg PnL], [WR]
  - Short trades: [count], [avg PnL], [WR]
- **Long-Only Test**: [Trades], [Net PnL], [PF], [Exp], [WR]
- **Delta**: ΔNet PnL: [X], ΔPF: [Y], ΔExp: [Z]
- **Verdict**: [IMPROVED / DEGRADED / NEUTRAL]

### MES Long-Only Analysis
[Same structure as ES]

### YM Both-Sides Control
- **Prior Both-Sides**: [metrics]
- **Current Both-Sides**: [metrics]
- **Delta**: [comparison]
- **Verdict**: [STABLE / DIVERGENT]

### Portfolio Comparison
| Configuration      | ES    | MES   | YM    | Total Net PnL | Portfolio PF | Sharpe |
|--------------------|-------|-------|-------|---------------|--------------|--------|
| Both Sides (prior) | [X]   | [Y]   | [Z]   | [Total]       | [PF]         | [SR]   |
| Long Filter (new)  | [X']  | [Y']  | [Z]   | [Total']      | [PF']        | [SR']  |
| **Delta**          | [ΔX]  | [ΔY]  | -     | [ΔTotal]      | [ΔPF]        | [ΔSR]  |

### Overall Test B Verdict
[Does filtering ES/MES to longs-only improve portfolio metrics? Should the final production version implement direction filters?]
```

---

## Test C: Cross-Instrument Generalization (MGC/MYM)

### Objective
Answer whether V9.1 improvements transfer to commodity contracts (MGC gold, MYM micro Dow), and specifically whether MYM improves over its weak baseline.

### Baseline Reference
From original Python `research_engine` holdout evaluation and TradingView analysis:

**MYM (Micro E-mini Dow) - Original V1.2 Baseline**
- Trades: 103
- Net PnL: +4.85 percentage points lift
- Profit Factor: 1.359
- Validation Status: **FAILED** (concentration gate failure)
- Issue: Weak sample size, marginal edge

**MGC (Micro Gold) - Original V1.2 Baseline**
- [Extract from holdout reports if available]

### Test Configuration
- **MGC**: Run V9.1 logic on micro gold futures
- **MYM**: Run V9.1 logic on micro Dow futures
- Period: 1-year + recent regime

### Analysis Framework

#### C.1 MGC Generalization Assessment
```
MGC_Trades_V91       = [from new CSV]
MGC_Net_PnL_V91      = [from new CSV]
MGC_PF_V91           = [from new CSV]
MGC_Expectancy_V91   = [from new CSV]
MGC_Win_Rate_V91     = [from new CSV]
MGC_Max_DD_V91       = [from new CSV]
```

Evaluate against validation gates:
- Trade sample size: ≥ 150 trades for validation? [YES/NO]
- Profit Factor: ≥ 1.40? [YES/NO]
- Expectancy: > $0? [YES/NO]
- Max DD: < 20% of starting capital? [YES/NO]

#### C.2 MYM Baseline Comparison
```
                     V1.2 Baseline    V9.1 New Test    Delta       % Change
Trades               103              [X]              [X - 103]   [%]
Net PnL (pp lift)    +4.85pp          [Y]              [Y - 4.85]  [%]
Profit Factor        1.359            [Z]              [Z - 1.359] [%]
Win Rate             [TBD]            [W]              [ΔW]        [%]
Expectancy           [TBD]            [E]              [ΔE]        [%]
Max Drawdown         [TBD]            [DD]             [ΔDD]       [%]
```

Key Question: Does V9.1 upgrade MYM from "weak candidate" to "validated candidate"?
- If Trades ≥ 150, PF ≥ 1.40, DD < 20% → **VALIDATED**
- If marginal improvement but still fails gates → **IMPROVED BUT MARGINAL**
- If no improvement or degradation → **NON-GENERALIZABLE**

#### C.3 Recent Regime Performance
For both MGC and MYM:
```
Recent_PF_Ratio   = PF_recent / PF_1year
Recent_Exp_Ratio  = Exp_recent / Exp_1year
```
- If ratio ≥ 1.00 → recent regime maintains or improves edge
- If ratio < 0.85 → recent regime degradation

#### C.4 Cross-Instrument Pattern Analysis
Compare trade distribution across:
- Time of day (opening hour, mid-session, closing hour)
- Directional bias (long vs short win rates)
- Average trade duration
- Max favorable/adverse excursion

Identify if V9.1 logic exhibits consistent behavior patterns across MGC/MYM.

### Expected Output Structure
```markdown
## Test C Results: Cross-Instrument Generalization

### MGC (Micro Gold) - V9.1 Performance
- **1-Year Period**
  - Trades: [X], Net PnL: [Y], PF: [Z], Exp: [E], WR: [W%]
  - Max DD: [DD%], Sharpe: [SR]
- **Recent Period**
  - [Same metrics]
  - Recent Regime Ratio: PF [X], Exp [Y]
- **Validation Gate Assessment**
  - Sample Size (≥150): [PASS/FAIL]
  - Profit Factor (≥1.40): [PASS/FAIL]
  - Drawdown (<20%): [PASS/FAIL]
  - Overall: [VALIDATED / MARGINAL / FAILED]

### MYM (Micro E-mini Dow) - V1.2 → V9.1 Comparison
| Metric            | V1.2 Baseline | V9.1 Test | Delta    | % Change |
|-------------------|---------------|-----------|----------|----------|
| Trades            | 103           | [X]       | [X-103]  | [%]      |
| Net PnL (pp lift) | +4.85pp       | [Y]       | [Y-4.85] | [%]      |
| Profit Factor     | 1.359         | [Z]       | [Z-1.359]| [%]      |
| Win Rate          | [TBD]         | [W]       | [ΔW]     | [%]      |
| Expectancy        | [TBD]         | [E]       | [ΔE]     | [%]      |
| Max Drawdown      | [TBD]         | [DD]      | [ΔDD]    | [%]      |

**Baseline Issue**: V1.2 failed concentration gate (103 trades, marginal PF 1.359)

**V9.1 Verdict**: [VALIDATED / IMPROVED BUT MARGINAL / NO IMPROVEMENT]

### Cross-Instrument Pattern Analysis
| Pattern               | MGC        | MYM        | Consistency |
|-----------------------|------------|------------|-------------|
| Long vs Short WR      | [L% / S%]  | [L% / S%]  | [HIGH/LOW]  |
| Avg Trade Duration    | [X bars]   | [Y bars]   | [HIGH/LOW]  |
| Opening Hour Trades % | [X%]       | [Y%]       | [HIGH/LOW]  |
| Avg MFE/MAE Ratio     | [R1]       | [R2]       | [HIGH/LOW]  |

**Generalization Assessment**: [Does V9.1 logic transfer cleanly to commodities, or are results instrument-specific?]

### Overall Test C Verdict
1. **MGC Viability**: [VALIDATED / MARGINAL / FAILED]
2. **MYM Upgrade**: [V1.2 → V9.1 improvement: YES/NO]
3. **Generalization Confidence**: [HIGH / MEDIUM / LOW]
4. **Recommendation**: [Should MGC/MYM be added to the production portfolio?]
```

---

## Cross-Test Synthesis

After completing individual test analyses, synthesize findings:

### S.1 Cost-Filtered Portfolio Construction
```
Viable Symbols (post-cost PF ≥ 1.20):
1. [Symbol 1]: PF [X], Exp [Y], Cost Drag [Z%]
2. [Symbol 2]: PF [X], Exp [Y], Cost Drag [Z%]
...

Rejected Symbols (post-cost PF < 1.20):
- [Symbol]: PF [X], Cost Drag [Z%]
```

### S.2 Direction Filter Decision Matrix
| Symbol | Both Sides PF | Long-Only PF | Delta | Recommended Config |
|--------|---------------|--------------|-------|--------------------|
| ES     | [X]           | [Y]          | [Δ]   | [BOTH / LONG-ONLY] |
| MES    | [X]           | [Y]          | [Δ]   | [BOTH / LONG-ONLY] |
| YM     | [X]           | [X]          | -     | [BOTH]             |

### S.3 Final Production Portfolio Candidate List
Based on all three tests:
```
TIER 1 (Validated + Cost Viable + Direction Optimized):
- [Symbol 1]: [Config], [Post-Cost PF], [Expectancy]
- [Symbol 2]: [Config], [Post-Cost PF], [Expectancy]

TIER 2 (Marginal but Worth Monitoring):
- [Symbol 3]: [Config], [Post-Cost PF], [Expectancy]

REJECTED (Failed Cost or Sample Gates):
- [Symbol 4]: [Reason]
```

### S.4 Enhancement Priority Re-Ranking
Given test results, which of the 18 identified enhancements should be prioritized?

**HIGH PRIORITY** (directly address test findings):
- [Enhancement ID]: [Rationale based on test results]

**MEDIUM PRIORITY** (incremental improvements):
- [Enhancement ID]: [Rationale]

**LOW PRIORITY / DEFERRED** (not supported by test evidence):
- [Enhancement ID]: [Rationale]

---

## Next Steps After Analysis

1. **User Decision Gate**: Which enhancements from the list of 18 should be backported to Python `research_engine`?
2. **Build Sequence Planning**: Once enhancements are selected, create a phased implementation plan.
3. **Re-Validation**: After Python engine upgrade, re-run full walk-forward validation on updated logic.
4. **Pine Script V2.0**: Update Pine script to match upgraded Python engine with final production-ready config.

**CRITICAL**: Do NOT begin implementation until user explicitly approves the analysis and selects enhancements.

---

**Template Status**: Ready for CSV arrival.  
**Last Updated**: 2026-06-05  
**Analyst**: Neo (Agent Handoff)

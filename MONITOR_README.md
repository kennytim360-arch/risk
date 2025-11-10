# RORO Live Market Monitor

**Real-time market analysis system for Risk-On/Risk-Off correlation trading. Analysis only - no trading execution.**

---

## Quick Start

```cmd
# Activate environment
venv\Scripts\activate.bat

# Run live monitor
python scripts\live_analysis.py
```

---

## What It Monitors

### Primary Instruments
- **US500** - S&P 500 (equity benchmark)
- **USDJPY** - Risk sentiment gauge
- **VIX** - Volatility/fear index
- **US10Y** - Bond yields
- **DXY** - Dollar strength

### Analysis Output (Every 5 Seconds)

**1. Current Prices** - Live data with % change

**2. Market Regime**
- 🟢 STRONG RISK-ON → Bullish, go LONG
- 🟡 WEAK RISK-ON → Mildly bullish, 50% size
- ⚪ TRANSITION → Stay out, mixed signals
- 🟡 WEAK RISK-OFF → Mildly bearish, consider shorts
- 🔴 STRONG RISK-OFF → Bearish, go SHORT

**3. Correlation Health**
- 🟢 HEALTHY (>0.7) → Full size approved
- 🟡 DEGRADED (0.4-0.7) → 50% size only
- 🔴 BROKEN (<0.4) → NO TRADING

**4. Divergence Detection**
- 🔵 BULLISH → SPX down, USDJPY holds, VIX flat
- 🟠 BEARISH → SPX up, USDJPY weak, DXY strong
- Counter-trend signals, 50% max size

**5. Position Sizing Guidance**
- Calculated for hypothetical $100k account
- Shows regime × VIX × correlation multipliers
- Recommended stop loss levels

**6. Tier-1 Entry Checklist**
- ✓ Regime identified (not transition)
- ✓ Correlation healthy (>0.4)
- ✓ No adverse divergence
- Overall clearance status

---

## Dashboard Example

```
================================================================================
                         RORO LIVE MARKET ANALYSIS
================================================================================

┌────────────────────────────────────────────────────────────────────────────┐
│                            CURRENT PRICES                                  │
├────────────────────────────────────────────────────────────────────────────┤
│ US500   :    4515.23  ↑ +0.35%                                            │
│ USDJPY  :     150.45  ↑ +0.12%                                            │
│ VIX     :      17.85  ↓ -2.15%                                            │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                         MARKET REGIME ANALYSIS                             │
├────────────────────────────────────────────────────────────────────────────┤
│ Regime: 🟢 STRONG RISK-ON                                                 │
│ Confidence: 82.5%                                                          │
│ Trading Bias: BULLISH - Go LONG on indices                                │
│ VIX Level: 17.85 (Multiplier: 1.00x)                                      │
├────────────────────────────────────────────────────────────────────────────┤
│ Signal Breakdown:                                                          │
│   US500    ↑ ████████   80%                                               │
│   USDJPY   ↑ ████████   85%                                               │
│   VIX      ↑ ███████    75%                                               │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                       TIER-1 ENTRY CHECKLIST                               │
├────────────────────────────────────────────────────────────────────────────┤
│ ✓ REGIME IDENTIFIED: STRONG_RISK_ON                                       │
│ ✓ CORRELATION HEALTH: HEALTHY                                             │
│ ✓ DIVERGENCE: No adverse divergence                                       │
│                                                                            │
│ 🟢 OVERALL: APPROVED FOR TRADING                                          │
└────────────────────────────────────────────────────────────────────────────┘

Press Ctrl+C to exit | Updates every 5 seconds | ANALYSIS ONLY
```

---

## VIX-Adaptive Thresholds

System automatically adjusts sensitivity based on volatility:

| VIX Level | Multiplier | Strong Move | Time Confirm |
|-----------|------------|-------------|--------------|
| < 15      | 0.7x       | ±0.35%      | 3 min        |
| 15-20     | 1.0x       | ±0.50%      | 5 min        |
| 20-25     | 1.3x       | ±0.65%      | 7 min        |
| > 25      | 1.5x       | ±0.75%      | 10 min       |

---

## Trading Sessions (GMT)

| Session    | Time        | Size  | Focus                 |
|------------|-------------|-------|-----------------------|
| Asian      | 00:00-08:00 | 50%   | USDJPY monitoring     |
| European   | 08:00-13:00 | 100%  | EUR/JPY added         |
| **US Overlap** | **13:00-16:00** | **100%** | **Best opportunities** |
| US Only    | 16:00-21:00 | 50%   | Reduce at 19:30       |
| **FLAT**   | **20:55**   | **0%** | **Close all positions** |

---

## Position Sizing Logic

```
Final Size = Base(2%) × Regime × VIX × Correlation

Regime Multipliers:
- Strong: 1.0x
- Weak: 0.5x
- Divergence: 0.5x (counter-trend penalty)

VIX Adjustment:
- Lower VIX = Higher size (inverse relationship)
- Formula: min(20/VIX, 1.5x cap)

Correlation:
- Healthy: 1.0x
- Degraded: 0.5x
- Broken: 0.0x (no trading)
```

---

## Regime Classification Rules

**STRONG RISK-ON** (3 of 4 required):
- ✓ SPX up > threshold, above VWAP, 5+ min sustained
- ✓ USDJPY up > threshold, above MA, 5+ min sustained
- ✓ VIX down > 5%
- ✓ US10Y rising > 2 bps

**STRONG RISK-OFF** (3 of 4 required):
- ✓ SPX down > threshold, below VWAP, 5+ min sustained
- ✓ USDJPY down > threshold, below MA, 5+ min sustained
- ✓ VIX up > 5%
- ✓ US10Y falling > 3 bps

**TRANSITION:**
- Conflicting signals
- Correlation < 0.4
- No clear bias 15+ minutes

---

## Divergence Detection

### Bullish (Counter-Trend Long)
1. SPX makes new 30-min low
2. USDJPY fails to make new low (higher low)
3. VIX declining or flat during selloff
4. Volume declining on down-move
5. Must persist 10+ minutes

**Action:** Prepare LONG, max 50% size, 0.25% stop

### Bearish (Counter-Trend Short)
1. SPX makes new 30-min high
2. USDJPY fails to make new high (lower high)
3. DXY strengthening despite risk-on
4. Volume declining on rally
5. Must persist 10+ minutes

**Action:** Prepare SHORT, max 50% size, 0.25% stop

---

## Stop Loss Guide

| Setup Type | Initial Stop | Trailing Stop | Time Stop |
|------------|--------------|---------------|-----------|
| Strong Regime | 0.5% | 0.3% after +0.5% | 3 candles below VWAP |
| Weak Regime | 0.3% | 0.2% after +0.3% | 2 candles below VWAP |
| Divergence | 0.25% | Manual only | 30 min OR failed retest |

---

## Risk Management

- **Max Trade Risk:** 2% per trade
- **Max Daily Risk:** 3% total drawdown
- **Loss Limit:** Stop after 3 consecutive losses
- **News Events:** Reduce to 25% size within 30 min of HIA events
- **Correlation Broken:** No trading until reset

---

## Configuration

Edit `config\settings.yaml`:

```yaml
mode: paper  # Analysis mode

account:
  initial_capital: 100000.0
  max_trade_risk: 0.02  # 2%
  max_daily_risk: 0.03  # 3%

data_feed:
  primary: yfinance  # Free data source
```

---

## Troubleshooting

**Markets closed / No signals:**
- System correctly shows TRANSITION + BROKEN correlation
- Run during market hours (9:30 AM - 4:00 PM EST) for best results

**DXY symbol error:**
- Edit config, change `DX-Y.NYB` to `DX=F` or remove DXY

**Dependencies missing:**
```cmd
pip install -r requirements.txt
```

---

## What This Monitor Does NOT Do

- ❌ Execute trades
- ❌ Connect to brokers
- ❌ Send orders
- ❌ Manage real positions

## What It DOES Do

- ✅ Real-time market analysis
- ✅ Regime classification
- ✅ Correlation monitoring
- ✅ Divergence detection
- ✅ Position sizing calculations (educational)
- ✅ Entry checklist validation
- ✅ Risk parameter display

---

## Files

- **scripts\live_analysis.py** - Main monitor dashboard
- **config\settings.yaml** - Configuration
- **logs\roro_system.log** - Analysis logs

---

## Performance Benchmarks

| Metric | Minimum | Excellence |
|--------|---------|------------|
| Strong Regime Win Rate | 60% | 70% |
| Divergence Success | 55% | 65% |
| Average R:R | 1.8 | 2.5 |
| Correlation Accuracy | 70% | 80% |
| Max Daily Drawdown | 2.5% | 1.5% |

---

**Status:** Analysis-only monitor - Educational tool for studying RORO strategy in real-time.

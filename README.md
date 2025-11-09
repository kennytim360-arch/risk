# RORO Day Trading System v3.1

## Risk-On/Risk-Off Multi-Asset Correlation Trading Strategy

**Version:** 3.1 - Optimized Production
**Status:** Live Trading Ready
**Date:** November 2024

---

## Overview

The RORO Day Trading System is a sophisticated correlation-based trading platform that identifies market regime shifts and exploits divergence opportunities across multiple asset classes.

### Key Features

- **Real-time Market Regime Classification** - Automatic detection of Strong/Weak Risk-On/Risk-Off conditions
- **VIX-Adaptive Thresholds** - Dynamic threshold adjustment based on volatility levels
- **Multi-Asset Correlation Analysis** - Real-time correlation monitoring across 5 primary instruments
- **Divergence Detection** - Automated Tier-1 bullish/bearish divergence signals
- **Position Sizing Calculator** - Risk-adjusted sizing with regime and VIX multipliers
- **Live Dashboard** - Real-time monitoring with entry checklists and alerts
- **Backtesting Framework** - Historical validation with realistic slippage modeling
- **Emergency Protocols** - Automated risk management and circuit breakers

---

## Primary Instruments

| Instrument | Symbol | Weight | Purpose |
|------------|--------|--------|---------|
| S&P 500 CFD | US500 | 30% | Primary equity benchmark |
| USD/JPY Forex | USDJPY | 25% | Risk sentiment indicator |
| Volatility Index | VIX | 25% | Fear gauge |
| US 10-Year Yield | US10Y | 10% | Bond market signal |
| Dollar Index | DXY | 10% | Currency strength |

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd risk

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure settings
cp config/settings.example.yaml config/settings.yaml
# Edit config/settings.yaml with your API keys and preferences
```

### Running the System

```bash
# Start the live dashboard
python src/main.py --mode live

# Run backtesting
python src/main.py --mode backtest --start 2022-01-01 --end 2024-12-31

# Paper trading mode
python src/main.py --mode paper

# Pre-market analysis
python scripts/premarket_check.py
```

---

## System Architecture

```
risk/
├── config/              # Configuration files
│   ├── settings.yaml    # Main settings
│   ├── instruments.yaml # Instrument definitions
│   └── thresholds.yaml  # VIX-adaptive thresholds
├── src/
│   ├── data_feeds/      # Market data integration
│   ├── regime/          # Regime classification engine
│   ├── correlation/     # Correlation analysis
│   ├── divergence/      # Divergence detection
│   ├── position/        # Position sizing
│   ├── risk/            # Risk management
│   ├── dashboard/       # Live monitoring UI
│   ├── backtest/        # Backtesting framework
│   └── utils/           # Utilities
├── tests/               # Test suite
├── docs/                # Documentation
├── scripts/             # Operational scripts
└── data/                # Historical data cache
```

---

## Data Feed Requirements

### Professional Grade Required
- **Recommended:** IQFeed, Rithmic, Bloomberg, Direct Broker API
- **Minimum Latency:** <100ms
- **Update Frequency:** Tick data for US500 and USDJPY, 1-second for others

### Supported Providers
- Interactive Brokers (via ib_insync)
- Alpha Vantage (basic)
- Yahoo Finance (basic, demo only)
- Custom API integration

---

## Performance Benchmarks

| Metric | Minimum | Excellence | Current |
|--------|---------|------------|---------|
| Strong Regime Win Rate | 60% | 70% | - |
| Divergence Success | 55% | 65% | - |
| Average R:R | 1.8 | 2.5 | - |
| Correlation Accuracy | 70% | 80% | - |
| Max Daily Drawdown | 2.5% | 1.5% | - |

---

## Trading Hours

| Session | Time (GMT) | Size | Focus |
|---------|-----------|------|-------|
| Asian | 00:00-08:00 | 50% | USDJPY monitoring |
| European | 08:00-13:00 | 100% | EUR/JPY added |
| US Overlap | 13:00-16:00 | 100% | Maximum opportunities |
| US Only | 16:00-21:00 | 50% after 19:30 | Reduce exposure |

**FLAT BY:** 20:55 GMT daily

---

## Risk Management

- **Max Trade Risk:** 2% per trade
- **Max Daily Risk:** 3% total
- **Loss Limit:** Stop trading after 3 consecutive losses
- **News Events:** Reduce to 25% size within 30 minutes of HIA events
- **Correlation Threshold:** No trading if correlation <0.4

---

## Three-Phase Launch Plan

### Phase 1: Historical Backtest (4-6 Weeks)
- Test on 2022-2024 data
- Validate win rates and drawdown
- Refine thresholds

### Phase 2: Paper Trading (2-4 Weeks)
- Real-time simulation
- Test operational execution
- Identify friction points

### Phase 3: Live Execution (Staged)
- Week 1-2: 10% target size
- Week 3-4: 50% target size
- Week 5+: 100% target size

---

## Dashboard Features

- Real-time regime classification
- Correlation coefficient matrix
- Divergence alerts
- Position size calculator
- Tier-1 entry checklist
- Live P&L tracking
- Emergency flatten button

---

## Emergency Protocols

### Data Feed Failure
1. Flatten all positions immediately
2. Switch to backup feed
3. Cease trading if unresolved in 5 minutes

### Black Swan Event (>3% move in <5 mins)
1. Auto-flatten all positions
2. System suspension for 1 hour
3. Resume at 25% size only

---

## Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Guide](docs/configuration.md)
- [Trading Manual](docs/trading_manual.md)
- [API Documentation](docs/api.md)
- [Backtesting Guide](docs/backtesting.md)
- [Troubleshooting](docs/troubleshooting.md)

---

## Support & Updates

- **Issues:** Report bugs via GitHub Issues
- **Updates:** System reviewed every 100 trades or 90 days
- **Version:** Current v3.1 - Optimized Production

---

## Disclaimer

This software is for educational and research purposes. Trading involves substantial risk of loss. Always test thoroughly in paper trading before risking real capital. Past performance does not guarantee future results.

---

**System Status:** Optimized & Live Ready
**Next Review:** 100 Trades or 90 Days

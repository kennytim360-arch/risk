# Quick Start Guide

## 5-Minute Setup

### 1. Install (2 minutes)

```bash
git clone <repository-url>
cd risk
chmod +x scripts/install.sh
./scripts/install.sh
```

### 2. Configure (2 minutes)

Edit `config/settings.yaml`:

```yaml
mode: paper  # Start with paper trading

account:
  initial_capital: 100000.0  # Your starting capital

data_feed:
  primary: yfinance  # Free data feed
```

### 3. Run Pre-Market Check (1 minute)

```bash
python scripts/premarket_check.py
```

This will:
- ✓ Check system health
- ✓ Test data feeds
- ✓ Analyze overnight market action
- ✓ Mental readiness assessment

## First Trading Session

### Display Trading Playbook

Keep this open during trading:

```bash
python scripts/playbook.py
```

### Start Paper Trading

```bash
python src/main.py --mode paper
```

The system will:
1. Connect to data feeds
2. Start monitoring markets
3. Classify regimes in real-time
4. Detect divergences
5. Generate trading signals
6. Log all activity

### Monitor Output

You'll see logs like:

```
2024-11-09 14:30:15 | INFO | Regime: STRONG_RISK_ON (0.82) | Correlation: HEALTHY
2024-11-09 14:30:20 | INFO | Generated 1 trading signals
2024-11-09 14:30:20 | INFO |   Signal: REGIME - LONG
```

## Understanding the Output

### Regime Classification

- **STRONG_RISK_ON** - Markets rallying, low VIX → Go LONG
- **WEAK_RISK_ON** - Mild rally, uncertain → LONG but reduced size
- **TRANSITION** - Mixed signals → STAY OUT
- **WEAK_RISK_OFF** - Mild selloff → SHORT but reduced size
- **STRONG_RISK_OFF** - Markets falling, high VIX → Go SHORT

### Correlation Health

- **HEALTHY (>0.7)** - Full size trading allowed
- **DEGRADED (0.4-0.7)** - Trade at 50% size
- **BROKEN (<0.4)** - NO TRADING

### Trading Signals

When a signal is generated:

```
Signal: REGIME - LONG
Instruments: ['US500', 'NASDAQ', 'DAX']
Position Size: 2.0% (1 contract)
Confidence: 0.85
```

## Key Commands

```bash
# Pre-market preparation
python scripts/premarket_check.py

# Display playbook (keep open)
python scripts/playbook.py

# Paper trading
python src/main.py --mode paper

# Run tests
pytest tests/ -v

# View logs
tail -f logs/roro_system.log
```

## Daily Workflow

### Morning (30 min before market open)

1. Run pre-market check
2. Review overnight action
3. Check economic calendar
4. Mental readiness assessment
5. Display playbook

### During Session

1. Monitor system output
2. Follow signals (in paper mode, just observe)
3. Note any interesting patterns
4. Stay disciplined

### After Session

1. Review trade log
2. Check performance metrics
3. Update trading journal
4. Note improvements

## Safety Features

The system has multiple safety layers:

1. **Risk Manager** - Enforces max trade/daily risk limits
2. **Stop Losses** - Automatic for every trade
3. **Correlation Monitor** - Stops trading if broken
4. **Loss Limits** - Stops after 3 consecutive losses
5. **Emergency Flatten** - One command closes all positions

## Important Notes

### Paper Trading First

- Start with paper trading for minimum 2-4 weeks
- Learn the system behavior
- Test your discipline
- Build confidence

### Never Override Safety

- Don't disable stop losses
- Don't exceed position limits
- Don't trade on broken correlation
- Don't trade when locked out

### Position Sizing Example

For $100,000 account:

| Regime | VIX | Correlation | Size | Risk Amount |
|--------|-----|-------------|------|-------------|
| Strong | 15 | Healthy | 2.0% | $2,000 |
| Weak | 18 | Healthy | 1.0% | $1,000 |
| Divergence | 20 | Healthy | 0.5% | $500 |
| Any | Any | Broken | 0.0% | $0 |

## Getting Help

### Check Logs

```bash
# Real-time monitoring
tail -f logs/roro_system.log

# Search for errors
grep ERROR logs/roro_system.log
```

### Common Issues

**No signals generated:**
- Check if in TRANSITION regime (normal, wait for clarity)
- Verify correlation health
- Check risk manager status

**Data feed errors:**
- Verify internet connection
- Check if market is open
- Try backup feed

**Import errors:**
- Reinstall: `pip install -e .`
- Check Python version: `python --version`

## Next Steps

After paper trading successfully:

1. **Week 1-2**: Paper trade, 100% rule adherence
2. **Week 3-4**: Analyze all paper trades, refine process
3. **Week 5-6**: Begin live with 10% size
4. **Week 7+**: Scale to full size if profitable

See [Trading Manual](trading_manual.md) for detailed operational procedures.

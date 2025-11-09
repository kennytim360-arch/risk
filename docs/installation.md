# Installation Guide

## Prerequisites

- **Python 3.9+** (3.10 or 3.11 recommended)
- **pip** (latest version)
- **Git** (for cloning repository)
- **8GB+ RAM** recommended for backtesting
- **Stable internet connection** for data feeds

## Quick Installation (Linux/Mac)

```bash
# Clone repository
git clone <repository-url>
cd risk

# Run installation script
chmod +x scripts/install.sh
./scripts/install.sh
```

The installation script will:
1. Check Python version
2. Create virtual environment
3. Install all dependencies
4. Set up directories
5. Copy example configuration
6. Run tests

## Manual Installation

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Install Package

```bash
pip install -e .
```

### 4. Create Directories

```bash
mkdir -p logs data/cache data/historical backtest_results
```

### 5. Configure Settings

```bash
cp config/settings.example.yaml config/settings.yaml
# Edit config/settings.yaml with your settings
```

## Configuration

### Essential Configuration Steps

1. **Data Feed Setup** - Edit `config/settings.yaml`:

```yaml
data_feed:
  primary: yfinance  # Options: yfinance, ib, alphavantage
  backup: yfinance
```

2. **Account Settings**:

```yaml
account:
  initial_capital: 100000.0
  max_trade_risk: 0.02  # 2%
  max_daily_risk: 0.03  # 3%
```

3. **API Keys** (if using paid data feeds):

For Interactive Brokers:
```yaml
data_feed:
  ib:
    host: 127.0.0.1
    port: 7497  # Paper trading
    client_id: 1
```

For Alpha Vantage:
```yaml
data_feed:
  alphavantage:
    api_key: YOUR_API_KEY_HERE
```

## Verification

### Run Tests

```bash
pytest tests/ -v
```

### Run Pre-Market Check

```bash
python scripts/premarket_check.py
```

### Test Data Feeds

```bash
python -c "
import asyncio
from src.data_feeds.manager import DataFeedManager
from src.utils.config import get_config

async def test():
    config = get_config()
    manager = DataFeedManager(config.get('data_feed', {}))
    connected = await manager.initialize()
    print(f'Connected: {connected}')
    await manager.disconnect()

asyncio.run(test())
"
```

## Troubleshooting

### Import Errors

If you get import errors, ensure:
```bash
# Reinstall in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Data Feed Connection Issues

For Yahoo Finance (default):
- No API key needed
- May have rate limits
- 15-20 minute delay on some data

For Interactive Brokers:
- Ensure TWS or IB Gateway is running
- Check port number (7497 for paper, 7496 for live)
- Enable API connections in TWS settings

### Missing Dependencies

```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

### TA-Lib Installation Issues

On Linux:
```bash
# Install TA-Lib C library first
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

# Then install Python wrapper
pip install TA-Lib
```

On Mac:
```bash
brew install ta-lib
pip install TA-Lib
```

On Windows:
```bash
# Download pre-built wheel from
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib‑0.4.XX‑cpXX‑cpXX‑win_amd64.whl
```

## Next Steps

After installation:

1. **Review Configuration** - `config/settings.yaml`
2. **Run Pre-Market Check** - `python scripts/premarket_check.py`
3. **View Playbook** - `python scripts/playbook.py`
4. **Start Paper Trading** - `python src/main.py --mode paper`

See [Trading Manual](trading_manual.md) for operational guidance.

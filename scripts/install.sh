#!/bin/bash
# Installation script for RORO Trading System

set -e  # Exit on error

echo "=================================="
echo "RORO Trading System - Installation"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

required_version="3.9"
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo "ERROR: Python 3.9 or higher is required"
    exit 1
fi

echo "✓ Python version OK"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Install package in development mode
echo "Installing RORO Trading System..."
pip install -e .
echo "✓ Package installed"
echo ""

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs
mkdir -p data/cache
mkdir -p data/historical
mkdir -p backtest_results
echo "✓ Directories created"
echo ""

# Copy example configuration
echo "Setting up configuration..."
if [ ! -f "config/settings.yaml" ]; then
    cp config/settings.example.yaml config/settings.yaml
    echo "✓ Configuration file created (config/settings.yaml)"
    echo "  IMPORTANT: Edit config/settings.yaml with your settings"
else
    echo "✓ Configuration file already exists"
fi
echo ""

# Make scripts executable
echo "Making scripts executable..."
chmod +x scripts/*.sh
chmod +x scripts/*.py
echo "✓ Scripts are executable"
echo ""

# Run tests
echo "Running tests..."
if pytest tests/ -v --tb=short 2>/dev/null; then
    echo "✓ All tests passed"
else
    echo "⚠ Some tests failed (this is normal if you haven't configured data feeds yet)"
fi
echo ""

echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit config/settings.yaml with your configuration"
echo "2. Add your API keys for data feeds"
echo "3. Run pre-market check: python scripts/premarket_check.py"
echo "4. Start paper trading: python src/main.py --mode paper"
echo ""
echo "For more information, see README.md"
echo ""

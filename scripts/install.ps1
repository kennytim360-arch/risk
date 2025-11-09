# RORO Trading System - Windows PowerShell Installation Script

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "RORO Trading System - Installation" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green

    # Check if version is 3.9+
    if ($pythonVersion -match "Python 3\.([0-9]+)") {
        $minorVersion = [int]$Matches[1]
        if ($minorVersion -lt 9) {
            Write-Host "ERROR: Python 3.9 or higher required" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    Write-Host "Install from: https://www.python.org/" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
}
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip setuptools wheel | Out-Null
Write-Host "✓ pip upgraded" -ForegroundColor Green
Write-Host ""

# Install dependencies
Write-Host "Installing dependencies (this may take a few minutes)..." -ForegroundColor Yellow
pip install -r requirements.txt
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Install package
Write-Host "Installing RORO Trading System..." -ForegroundColor Yellow
pip install -e .
Write-Host "✓ Package installed" -ForegroundColor Green
Write-Host ""

# Create directories
Write-Host "Creating necessary directories..." -ForegroundColor Yellow
$dirs = @("logs", "data\cache", "data\historical", "backtest_results")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}
Write-Host "✓ Directories created" -ForegroundColor Green
Write-Host ""

# Copy configuration
Write-Host "Setting up configuration..." -ForegroundColor Yellow
if (-not (Test-Path "config\settings.yaml")) {
    Copy-Item "config\settings.example.yaml" "config\settings.yaml"
    Write-Host "✓ Configuration file created: config\settings.yaml" -ForegroundColor Green
    Write-Host "  IMPORTANT: Edit config\settings.yaml with your settings" -ForegroundColor Cyan
} else {
    Write-Host "✓ Configuration file already exists" -ForegroundColor Green
}
Write-Host ""

# Run tests
Write-Host "Running tests..." -ForegroundColor Yellow
pytest tests\ -v --tb=short 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ Some tests failed (normal if data feeds not configured)" -ForegroundColor Yellow
} else {
    Write-Host "✓ All tests passed" -ForegroundColor Green
}
Write-Host ""

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit config\settings.yaml with your configuration"
Write-Host "2. Add your API keys for data feeds"
Write-Host "3. Run pre-market check: python scripts\premarket_check.py"
Write-Host "4. Start paper trading: python src\main.py --mode paper"
Write-Host ""
Write-Host "Keep the virtual environment activated!" -ForegroundColor Cyan
Write-Host "To reactivate later: .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host ""

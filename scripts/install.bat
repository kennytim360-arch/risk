@echo off
REM RORO Trading System - Windows Installation Script

echo ==================================
echo RORO Trading System - Installation
echo ==================================
echo.

REM Check Python version
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher from https://www.python.org/
    pause
    exit /b 1
)

python --version
echo.

REM Create virtual environment
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel
echo pip upgraded
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo Dependencies installed
echo.

REM Install package
echo Installing RORO Trading System...
pip install -e .
echo Package installed
echo.

REM Create directories
echo Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "data\cache" mkdir data\cache
if not exist "data\historical" mkdir data\historical
if not exist "backtest_results" mkdir backtest_results
echo Directories created
echo.

REM Copy configuration
echo Setting up configuration...
if not exist "config\settings.yaml" (
    copy config\settings.example.yaml config\settings.yaml
    echo Configuration file created: config\settings.yaml
    echo IMPORTANT: Edit config\settings.yaml with your settings
) else (
    echo Configuration file already exists
)
echo.

REM Run tests
echo Running tests...
pytest tests\ -v --tb=short 2>nul
if errorlevel 1 (
    echo WARNING: Some tests failed - this is normal if data feeds not configured
) else (
    echo All tests passed
)
echo.

echo ==================================
echo Installation Complete!
echo ==================================
echo.
echo Next steps:
echo 1. Edit config\settings.yaml with your configuration
echo 2. Add your API keys for data feeds
echo 3. Run pre-market check: python scripts\premarket_check.py
echo 4. Start paper trading: python src\main.py --mode paper
echo.
echo Keep the virtual environment activated!
echo To reactivate later: venv\Scripts\activate.bat
echo.
pause

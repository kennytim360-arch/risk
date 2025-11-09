# Windows Installation Guide

## Quick Start for Windows

### Option 1: Using Batch Script (Easiest)

1. **Open Command Prompt** (cmd)
   - Press `Win + R`
   - Type `cmd` and press Enter

2. **Navigate to project directory**
   ```cmd
   cd path\to\risk
   ```

3. **Run installation script**
   ```cmd
   scripts\install.bat
   ```

### Option 2: Using PowerShell (Recommended)

1. **Open PowerShell**
   - Press `Win + X`
   - Select "Windows PowerShell" or "Terminal"

2. **Navigate to project directory**
   ```powershell
   cd path\to\risk
   ```

3. **Allow script execution** (first time only)
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **Run installation script**
   ```powershell
   .\scripts\install.ps1
   ```

### Option 3: Manual Installation

1. **Check Python**
   ```cmd
   python --version
   ```
   Should show Python 3.9 or higher. If not, install from [python.org](https://www.python.org/)

2. **Create virtual environment**
   ```cmd
   python -m venv venv
   ```

3. **Activate virtual environment**

   **Command Prompt:**
   ```cmd
   venv\Scripts\activate.bat
   ```

   **PowerShell:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

4. **Install dependencies**
   ```cmd
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   pip install -e .
   ```

5. **Create directories**
   ```cmd
   mkdir logs
   mkdir data\cache
   mkdir data\historical
   mkdir backtest_results
   ```

6. **Copy configuration**
   ```cmd
   copy config\settings.example.yaml config\settings.yaml
   ```

## Running the System on Windows

### Activate Virtual Environment

Every time you open a new terminal:

**Command Prompt:**
```cmd
cd path\to\risk
venv\Scripts\activate.bat
```

**PowerShell:**
```powershell
cd path\to\risk
.\venv\Scripts\Activate.ps1
```

You'll see `(venv)` at the start of your prompt when activated.

### Run Pre-Market Check

```cmd
python scripts\premarket_check.py
```

### Display Playbook

```cmd
python scripts\playbook.py
```

### Start Paper Trading

```cmd
python src\main.py --mode paper
```

### Run Tests

```cmd
pytest tests\ -v
```

## Common Windows Issues

### "python is not recognized"

**Problem:** Python not in PATH

**Solution:**
1. Reinstall Python from [python.org](https://www.python.org/)
2. During installation, check "Add Python to PATH"

Or manually add to PATH:
1. Search for "Environment Variables" in Start menu
2. Edit "Path" variable
3. Add: `C:\Users\YourName\AppData\Local\Programs\Python\Python311`

### "cannot be loaded because running scripts is disabled"

**Problem:** PowerShell execution policy

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### TA-Lib Installation Issues

**Problem:** TA-Lib requires compiled binary

**Solution:**
1. Download pre-built wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)
2. Install with pip:
   ```cmd
   pip install TA_Lib-0.4.XX-cpXX-cpXX-win_amd64.whl
   ```

### Virtual Environment Not Activating

**PowerShell:**
```powershell
# If Activate.ps1 doesn't work:
& ".\venv\Scripts\Activate.ps1"
```

**Command Prompt:**
```cmd
# Should always work:
venv\Scripts\activate.bat
```

## Configuration for Windows

Edit `config\settings.yaml`:

```yaml
# Windows path example
logging:
  file: logs/roro_system.log  # Use forward slashes even on Windows

# Data paths
data_directory: data/cache
```

Python handles forward slashes correctly on Windows, so use `/` not `\` in config.

## File Paths in Windows

When working with the system:

**In Python code:** Use forward slashes
```python
file_path = "data/cache/prices.csv"  # This works on Windows
```

**In terminal:** Use backslashes
```cmd
type data\cache\prices.csv
```

**In config files:** Use forward slashes
```yaml
log_file: logs/roro_system.log
```

## Quick Reference Commands

| Task | Command |
|------|---------|
| Activate venv (cmd) | `venv\Scripts\activate.bat` |
| Activate venv (PS) | `.\venv\Scripts\Activate.ps1` |
| Deactivate venv | `deactivate` |
| Install deps | `pip install -r requirements.txt` |
| Run tests | `pytest tests\ -v` |
| Pre-market check | `python scripts\premarket_check.py` |
| Paper trading | `python src\main.py --mode paper` |
| View playbook | `python scripts\playbook.py` |

## Recommended Windows Setup

### 1. Use Windows Terminal (Best Experience)

Install from Microsoft Store: [Windows Terminal](https://aka.ms/terminal)

Benefits:
- Tabs
- Better colors
- Copy/paste support
- Split panes

### 2. Use VS Code (Optional)

1. Install [VS Code](https://code.visualstudio.com/)
2. Open project: `File > Open Folder > risk`
3. Install Python extension
4. Select interpreter: `Ctrl+Shift+P` > "Python: Select Interpreter" > `.\venv\Scripts\python.exe`
5. Run scripts from integrated terminal

### 3. Git Bash (Alternative Terminal)

If you have Git for Windows, you can use Git Bash for Unix-like commands:

```bash
# Then you can use Linux-style commands
chmod +x scripts/*.sh
./scripts/install.sh
```

## Troubleshooting Checklist

- [ ] Python 3.9+ installed and in PATH
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip list` shows packages)
- [ ] Configuration file exists (`config\settings.yaml`)
- [ ] Directories created (`logs\`, `data\`)
- [ ] Tests pass (or fail only due to API keys)

## Getting Help

If you encounter issues:

1. **Check logs:**
   ```cmd
   type logs\roro_system.log
   ```

2. **Verify installation:**
   ```cmd
   python -c "import src; print('OK')"
   ```

3. **Check virtual environment:**
   ```cmd
   where python
   ```
   Should show path to `venv\Scripts\python.exe`

4. **Run with verbose output:**
   ```cmd
   python src\main.py --mode paper --verbose
   ```

## Next Steps

After successful installation:

1. ✅ Edit `config\settings.yaml`
2. ✅ Run `python scripts\premarket_check.py`
3. ✅ Review `python scripts\playbook.py`
4. ✅ Start paper trading
5. ✅ Monitor logs in `logs\roro_system.log`

Good luck with your trading! 🚀

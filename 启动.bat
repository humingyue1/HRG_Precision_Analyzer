@echo off
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ============================================
echo   HRG Precision Analyzer v4.0
echo ============================================
echo Starting...
python run_gui_v4.py

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start. Please install dependencies:
    echo   pip install -r requirements.txt
    echo.
    echo If VTK is not installed, 3D comparison will use matplotlib instead.
    pause
)

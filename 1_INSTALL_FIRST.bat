@echo off
title Factory Monitor Pro - Installing...
color 0A

echo ============================================================
echo   FACTORY 5 - PRODUCTION MONITOR
echo   Installing required libraries...
echo ============================================================
echo.

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Python is not installed or not in PATH.
    echo Please download from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during install
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing all required libraries...
python -m pip install streamlit pandas plotly openpyxl Pillow ezdxf numpy reportlab twilio

IF %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Installation failed. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   [SUCCESS] Installation complete!
echo   Now double-click:  2_RUN_DASHBOARD.bat
echo ============================================================
echo.
pause

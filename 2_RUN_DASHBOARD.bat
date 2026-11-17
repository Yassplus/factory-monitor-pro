@echo off
title Factory 5 Dashboard - Running...
color 0A

echo ============================================================
echo   FACTORY 5 - PRODUCTION MONITOR
echo   Starting Streamlit Dashboard...
echo ============================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Python not found. Please run 1_INSTALL_FIRST.bat first.
    pause
    exit /b 1
)

:: Check if streamlit is installed
python -c "import streamlit" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Streamlit is not installed.
    echo Please run 1_INSTALL_FIRST.bat first.
    echo.
    pause
    exit /b 1
)

echo [OK] All libraries found.
echo.
echo Opening dashboard in your browser...
echo (Press Ctrl+C in this window to stop the app)
echo.

:: Change directory to the folder where this bat file lives
cd /d "%~dp0"

:: Open browser after short delay
start /min "" cmd /c "timeout /t 4 >nul && start http://localhost:8501"

:: Run the app using python -m streamlit (fixes PATH issues)
python -m streamlit run app.py --server.port 8501 --server.headless false

IF %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo [ERROR] Failed to start the dashboard.
    echo Make sure 1_INSTALL_FIRST.bat was run successfully.
    pause
)

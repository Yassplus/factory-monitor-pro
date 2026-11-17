@echo off
title Factory Monitor Pro - Mobile View
color 0A

echo ============================================================
echo   FACTORY 5 - PRODUCTION MONITOR (MOBILE VIEW)
echo   Opening on port 8502 - scan QR code on your phone
echo ============================================================
echo.
echo After starting, open your phone browser and go to:
echo   http://[YOUR-PC-IP]:8502
echo.
echo To find your PC IP: open CMD and type "ipconfig"
echo.

cd /d "%~dp0"

python -m streamlit run mobile.py --server.port 8502 --server.address 0.0.0.0 --server.headless true

IF %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo [ERROR] Failed to start the mobile view.
    echo Make sure 1_INSTALL_FIRST.bat was run successfully.
    pause
)

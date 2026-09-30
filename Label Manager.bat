@echo off
title Gmail Label Manager
REM Gmail Label Manager - Windows launcher. Double-click this file.

cd /d "%~dp0"

echo ========================================
echo Gmail Label Manager
echo ========================================
echo.
echo Project directory: %cd%
echo.

uv --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: uv is not installed.
    echo.
    echo Install it by running this in PowerShell:
    echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo.
    echo Then reopen this script.
    echo.
    pause
    exit /b 1
)

if not exist "credentials_gmail.json" if not exist "credentials.json" (
    echo ERROR: No OAuth client file found.
    echo Place credentials_gmail.json or credentials.json in this folder.
    echo.
    pause
    exit /b 1
)

echo Starting Label Manager on http://127.0.0.1:8504
echo.
echo Sign-in uses the same tokens as Gmail Cleaner when an account is already active.
echo Do not sign in to both apps at the same time. They share OAuth port 8767.
echo.
echo Press Ctrl+C here to stop the server.
echo.

uv run --with streamlit python -m streamlit run label_manager_ui.py --server.port 8504 --browser.gatherUsageStats false

echo.
echo Server stopped.
pause

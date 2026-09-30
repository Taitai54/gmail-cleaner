@echo off
title Gmail Cleaner
REM Gmail Cleaner - Windows launcher. Double-click this file.

cd /d "%~dp0"

echo ========================================
echo Gmail Cleaner
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

echo uv detected:
uv --version
echo.

if exist "credentials.json" (
    echo credentials.json found.
) else (
    if exist "global.env" (
        echo Using credentials from global.env
    ) else (
        echo No credentials.json or global.env - the app will show setup steps if needed.
    )
)
echo.

REM Desktop mode. Do not inherit WEB_AUTH=true from Docker Desktop or other tools.
set WEB_AUTH=false

echo ========================================
echo Starting Gmail Cleaner on http://127.0.0.1:8766
echo ========================================
echo.
echo Your browser should open automatically.
echo Press Ctrl+C here to stop the server.
echo.
echo Label Manager is a separate app. Use "Label Manager.bat" for that.
echo.

uv run python main.py

echo.
echo Server stopped.
pause

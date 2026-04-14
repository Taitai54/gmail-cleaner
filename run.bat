@echo off
REM Gmail Cleaner - Windows Run Script

REM Always run from the folder this script is in
cd /d "%~dp0"

echo ========================================
echo Gmail Cleaner - Startup Script
echo ========================================
echo.
echo Project directory: %cd%
echo.

REM 1. Check for uv (the package manager this project uses)
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

REM 2. Credentials: app will load from credentials.json or global.env (GOOGLE_CREDENTIALS)
if exist "credentials.json" (
    echo credentials.json found.
) else (
    if exist "global.env" (
        echo Using credentials from global.env
    ) else (
        echo No credentials.json or global.env - app will show setup steps if needed.
    )
)
echo.

REM 3. Force desktop mode (never inherit WEB_AUTH=true from Docker Desktop or other tools)
set WEB_AUTH=false

REM 4. Launch the app via uv (handles dependencies automatically)
echo ========================================
echo Starting Gmail Cleaner...
echo ========================================
echo.
echo Your browser will open automatically.
echo If it doesn't, go to: http://127.0.0.1:8766
echo.
echo Press Ctrl+C here to stop the server.
echo.

uv run python main.py

REM Server stopped
echo.
echo Server stopped.
pause

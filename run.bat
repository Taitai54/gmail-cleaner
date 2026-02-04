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

REM 2. Check for credentials.json
if not exist "credentials.json" (
    echo ========================================
    echo SETUP REQUIRED - credentials.json missing
    echo ========================================
    echo.
    echo The app needs a Google OAuth credentials file.
    echo See README.md for the full guide. Quick steps:
    echo.
    echo  1. Go to https://console.cloud.google.com/
    echo  2. Create a project and enable the Gmail API
    echo  3. Go to Credentials -> Create -> OAuth client ID
    echo     (choose Desktop app type)
    echo  4. Download the JSON and save it as:
    echo     %cd%\credentials.json
    echo.
    pause
    exit /b 1
)

echo credentials.json found.
echo.

REM 3. Launch the app via uv (handles dependencies automatically)
echo ========================================
echo Starting Gmail Cleaner...
echo ========================================
echo.
echo Your browser will open automatically.
echo If it doesn't, go to: http://localhost:8766
echo.
echo Press Ctrl+C here to stop the server.
echo.

uv run python main.py

REM Server stopped
echo.
echo Server stopped.
pause

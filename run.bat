@echo off
REM Gmail Cleaner - Windows Run Script
REM This script sets up and runs the Gmail Cleaner application

echo ========================================
echo Gmail Cleaner - Startup Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Python detected:
python --version
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Check if dependencies are installed
if not exist "venv\Lib\site-packages\fastapi" (
    echo Installing dependencies...
    echo This may take a few minutes...
    pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo Dependencies installed successfully
    echo.
)

REM Check if credentials.json exists
if not exist "credentials.json" (
    echo.
    echo ========================================
    echo SETUP REQUIRED
    echo ========================================
    echo credentials.json not found!
    echo.
    echo Please follow these steps:
    echo 1. Copy credentials.template.json to credentials.json
    echo 2. Fill in your Google OAuth credentials
    echo 3. See README.md for detailed setup instructions
    echo.
    pause
    exit /b 1
)

REM Start the application
echo.
echo ========================================
echo Starting Gmail Cleaner...
echo ========================================
echo.
echo The application will be available at:
echo http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py

REM If we get here, the server has stopped
echo.
echo Server stopped.
pause

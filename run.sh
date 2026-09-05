#!/bin/bash
# Gmail Cleaner - Mac/Linux Run Script

# Always cd into the folder this script lives in, no matter where you run it from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "Gmail Cleaner - Startup Script"
echo "========================================"
echo ""
echo "Project directory: $SCRIPT_DIR"
echo ""

export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# 1. Determine runner (uv, .venv python, or system python3)
RUN_CMD=""
if command -v uv &> /dev/null; then
    RUN_CMD="uv run python main.py"
    echo "uv detected: $(uv --version)"
elif [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    RUN_CMD="$SCRIPT_DIR/.venv/bin/python main.py"
    echo "Using local virtual environment: $SCRIPT_DIR/.venv"
elif command -v python3 &> /dev/null; then
    RUN_CMD="python3 main.py"
    echo "Using system python3: $(which python3)"
else
    echo "ERROR: Python is not installed or not in PATH."
    echo ""
    echo "Install uv (recommended) by running:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "Press Enter to close..."
    read
    exit 1
fi
echo ""

# 2. Check for credentials (required before the app can start)
if [ ! -f "credentials.json" ] && [ ! -f "credentials_gmail.json" ] && [ ! -f "credentials_unidays.json" ]; then
    echo "========================================"
    echo "SETUP REQUIRED - OAuth credentials missing"
    echo "========================================"
    echo ""
    echo "The app needs a Google OAuth credentials file."
    echo "See README.md for the full guide. Quick steps:"
    echo ""
    echo "  1. Go to https://console.cloud.google.com/"
    echo "  2. Create a project and enable the Gmail API"
    echo "  3. Go to Credentials -> Create -> OAuth client ID"
    echo "     (choose Desktop app type)"
    echo "  4. Download the JSON and save it as:"
    echo "     $SCRIPT_DIR/credentials.json"
    echo ""
    echo "Press Enter to close..."
    read
    exit 1
fi

echo "credentials.json found."
echo ""

# 3. Launch the app via uv (handles dependencies automatically)
echo "========================================"
echo "Starting Gmail Cleaner..."
echo "========================================"
echo ""
echo "Your browser will open automatically."
echo "If it doesn't, go to: http://localhost:8766"
echo ""
echo "Press Ctrl+C here to stop the server."
echo ""

$RUN_CMD

# Server stopped (user hit Ctrl+C or it crashed)
echo ""
echo "Server stopped."
echo "Press Enter to close..."
read

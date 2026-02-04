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

# 1. Check for uv (the package manager this project uses)
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv is not installed."
    echo ""
    echo "Install it by running this in your terminal:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "Then reopen Terminal and run ./run.sh again."
    echo ""
    echo "Press Enter to close..."
    read
    exit 1
fi

echo "uv detected: $(uv --version)"
echo ""

# 2. Check for credentials.json (required before the app can start)
if [ ! -f "credentials.json" ]; then
    echo "========================================"
    echo "SETUP REQUIRED - credentials.json missing"
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

uv run python main.py

# Server stopped (user hit Ctrl+C or it crashed)
echo ""
echo "Server stopped."
echo "Press Enter to close..."
read

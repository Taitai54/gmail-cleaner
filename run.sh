#!/bin/bash
# Gmail Cleaner - Mac/Linux Run Script
# This script sets up and runs the Gmail Cleaner application

echo "========================================"
echo "Gmail Cleaner - Startup Script"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    echo ""
    echo "On macOS: brew install python3"
    echo "On Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

echo "Python detected:"
python3 --version
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        exit 1
    fi
    echo "Virtual environment created successfully"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

# Check if dependencies are installed
if [ ! -f "venv/lib/python*/site-packages/fastapi/__init__.py" ]; then
    echo "Installing dependencies..."
    echo "This may take a few minutes..."
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        exit 1
    fi
    echo "Dependencies installed successfully"
    echo ""
fi

# Check if credentials.json exists
if [ ! -f "credentials.json" ]; then
    echo ""
    echo "========================================"
    echo "SETUP REQUIRED"
    echo "========================================"
    echo "credentials.json not found!"
    echo ""
    echo "Please follow these steps:"
    echo "1. Copy credentials.template.json to credentials.json"
    echo "   cp credentials.template.json credentials.json"
    echo "2. Fill in your Google OAuth credentials"
    echo "3. See README.md for detailed setup instructions"
    echo ""
    exit 1
fi

# Start the application
echo ""
echo "========================================"
echo "Starting Gmail Cleaner..."
echo "========================================"
echo ""
echo "The application will be available at:"
echo "http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 main.py

# If we get here, the server has stopped
echo ""
echo "Server stopped."

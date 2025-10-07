#!/bin/bash
# ReolinkANPR Setup Script
# Automates the initial setup process

set -e

echo "============================================================"
echo "ReolinkANPR - Setup Script"
echo "============================================================"
echo ""

# Check Python version (3.11+ required for TCP push events)
echo "Checking Python version..."

# Try different Python versions
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3; do
    if command -v $cmd &> /dev/null; then
        VERSION=$($cmd --version 2>&1 | cut -d' ' -f2)
        MAJOR=$(echo $VERSION | cut -d'.' -f1)
        MINOR=$(echo $VERSION | cut -d'.' -f2)

        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
            PYTHON_CMD=$cmd
            echo "✓ Found $cmd (Python $VERSION) - Compatible!"
            break
        else
            echo "  $cmd (Python $VERSION) - Too old (need 3.11+)"
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo ""
    echo "ERROR: Python 3.11 or higher is required!"
    echo "TCP push events require reolink-aio 0.10+ which needs Python 3.11+"
    echo ""
    echo "Install Python 3.11+ using:"
    echo "  macOS:   brew install python@3.11"
    echo "  Ubuntu:  sudo apt install python3.11 python3.11-venv"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment with $PYTHON_CMD..."
$PYTHON_CMD -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt

# Create directories
echo ""
echo "Creating data directories..."
mkdir -p data/images
mkdir -p logs

echo ""
echo "============================================================"
echo "Setup Complete!"
echo "============================================================"
echo ""
echo "To start ReolinkANPR:"
echo "  source venv/bin/activate"
echo "  python3 run.py"
echo ""
echo "Then:"
echo "  1. Open browser: http://localhost:5001/config"
echo "  2. Configure your camera settings via web interface"
echo "  3. Save and restart"
echo ""
echo "Note: config.yaml will be auto-created on first run"
echo ""
echo "For detailed instructions, see INSTALL.md"
echo ""
echo "============================================================"

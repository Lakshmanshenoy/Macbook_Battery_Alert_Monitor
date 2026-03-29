#!/bin/bash
# Setup and installation script for Battery Alert App

set -e  # Exit on error

echo "═══════════════════════════════════════════════════"
echo "  🔋 Battery Alert Monitor - Setup & Build"
echo "═══════════════════════════════════════════════════"
echo ""

# Check Python version
echo "🔍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    echo "💡 Please install Python 3 from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=
$(python3 --version | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION found"
echo ""

# Create virtual environment (optional but recommended)
echo "📦 Setting up dependencies..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt
echo ""
echo "✅ Dependencies installed successfully!"
echo ""

# Make scripts executable
chmod +x build.sh
chmod +x create_dmg.sh

echo "═══════════════════════════════════════════════════"
echo "  📝 Quick Start Guide"
echo "═══════════════════════════════════════════════════"
echo ""
echo "1️⃣  Test the app first (optional):"
echo "    python3 battery_alert_gui.py"
echo ""
echo "2️⃣  Build the macOS app:"
echo "    ./build.sh"
echo ""
echo "3️⃣  Create DMG installer (optional, for distribution):"
echo "    ./create_dmg.sh"
echo ""
echo "4️⃣  Deactivate virtual environment (when done):"
echo "    deactivate"
echo ""
echo "═══════════════════════════════════════════════════"
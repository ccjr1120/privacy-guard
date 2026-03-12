#!/bin/bash
# Installation script

echo "🚀 Privacy Guard Installer"
echo ""

# Check Python
echo "📋 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not installed, please install Python 3.8+ first"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  source venv/bin/activate"
echo "  python privacy_guard.py"
echo ""
echo "Debug mode:"
echo "  python privacy_guard.py --debug"
echo ""
echo "💡 Tip: First run requires allowing terminal camera access in System Settings > Privacy & Security > Camera"

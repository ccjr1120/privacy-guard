#!/bin/bash
# Build script for Privacy Guard Mac app

echo "🚀 Privacy Guard Build Script"
echo ""

# Check if we're in the right directory
if [ ! -f "privacy_guard.py" ]; then
    echo "❌ Error: privacy_guard.py not found"
    echo "Please run this script from the project root"
    exit 1
fi

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Build app bundle
echo ""
echo "🔨 Building app bundle..."
rm -rf build dist
python setup.py py2app

if [ -d "dist/Privacy Guard.app" ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "App location: dist/Privacy Guard.app"
    echo ""
    echo "To install:"
    echo "  cp -r 'dist/Privacy Guard.app' /Applications/"
    echo ""
    echo "⚠️  Important: Grant permissions on first run:"
    echo "   - Camera access"
    echo "   - Screen recording (for blur effect)"
    echo "   - Accessibility (for global click detection)"
else
    echo ""
    echo "❌ Build failed"
    exit 1
fi

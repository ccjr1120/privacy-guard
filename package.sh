#!/bin/bash
# Build and package Privacy Guard as DMG for release

set -e

APP_NAME="Privacy Guard"
APP_BUNDLE="Privacy Guard.app"
DMG_NAME="PrivacyGuard-1.0.0.dmg"
VOLUME_NAME="Privacy Guard Installer"

echo "🚀 Privacy Guard DMG Builder"
echo ""

# Check if we're in the right directory
if [ ! -f "privacy_guard.py" ]; then
    echo "❌ Error: privacy_guard.py not found"
    echo "Please run this script from the project root"
    exit 1
fi

# Check dependencies
echo "📋 Checking dependencies..."
if ! command -v create-dmg &> /dev/null; then
    echo "📦 Installing create-dmg..."
    brew install create-dmg
fi

echo "✅ create-dmg installed"

# Clean previous builds
echo ""
echo "🧹 Cleaning previous builds..."
rm -rf build dist *.dmg

# Create virtual environment
echo ""
echo "📦 Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip

# Install dlib-bin first (precompiled, avoids build issues)
echo "📦 Installing dlib-bin..."
pip install dlib-bin

# Install other dependencies (excluding dlib to avoid compilation)
echo "📦 Installing other dependencies..."
pip install rumps PyQt6 pyyaml opencv-python numpy pillow py2app

# Install face-recognition without deps since we have dlib-bin
pip install face-recognition --no-deps
pip install Click face-recognition-models

# Build app bundle
echo ""
echo "🔨 Building app bundle..."
python setup.py py2app

if [ ! -d "dist/${APP_BUNDLE}" ]; then
    echo ""
    echo "❌ Build failed - app bundle not found"
    exit 1
fi

echo "✅ App bundle created"

# Sign the app (optional, ad-hoc signing)
echo ""
echo "📝 Signing app bundle..."
codesign --force --deep --sign - "dist/${APP_BUNDLE}"

# Create DMG
echo ""
echo "📀 Creating DMG..."

# Create a temporary directory for DMG contents
DMG_TEMP="dist/dmg_temp"
mkdir -p "${DMG_TEMP}"

# Copy app bundle
cp -R "dist/${APP_BUNDLE}" "${DMG_TEMP}/"

# Create Applications shortcut
ln -s /Applications "${DMG_TEMP}/Applications"

# Create README for DMG
cat > "${DMG_TEMP}/README.txt" << 'EOF'
Privacy Guard - Smart Screen Privacy Shield
===========================================

Installation:
1. Drag "Privacy Guard.app" to the Applications folder
2. Launch from Applications
3. On first run, grant permissions:
   - Camera (for face recognition)
   - Screen Recording (for blur effect)
   - Accessibility (for click detection)

First Time Setup:
1. Click the 🔒 icon in the menu bar
2. Select "Register Owner Face"
3. Look at the camera for 2-3 seconds
4. Done! The app will now only recognize you

Usage:
- The app runs in the menu bar
- Screen blurs when you leave or a stranger appears
- Click anywhere on the blurred screen to unlock
- View logs and settings from the menu bar icon

For more info: https://github.com/ccjr1120/privacy-guard
EOF

# Build DMG using create-dmg
create-dmg \
    --volname "${VOLUME_NAME}" \
    --volicon "dist/${APP_BUNDLE}/Contents/Resources/icon.icns" 2>/dev/null || echo "" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "${APP_BUNDLE}" 150 200 \
    --icon "Applications" 450 200 \
    --hide-extension "${APP_BUNDLE}" \
    --app-drop-link 450 200 \
    --no-internet-enable \
    "${DMG_NAME}" \
    "${DMG_TEMP}"

# Alternative: use hdiutil if create-dmg fails
if [ ! -f "${DMG_NAME}" ]; then
    echo "⚠️ create-dmg failed, trying hdiutil..."
    
    # Create temporary DMG
    TEMP_DMG="temp.dmg"
    hdiutil create -srcfolder "${DMG_TEMP}" -volname "${VOLUME_NAME}" -fs HFS+ \
        -format UDRW -size 100m "${TEMP_DMG}"
    
    # Mount it
    MOUNT_POINT=$(hdiutil attach "${TEMP_DMG}" -noverify -nobrowse | grep "/Volumes/" | awk '{print $3}')
    
    # Set background and icon positions (optional, requires AppleScript)
    # This is simplified - for production you'd want proper DMG styling
    
    # Unmount and convert to compressed DMG
    hdiutil detach "${MOUNT_POINT}"
    hdiutil convert "${TEMP_DMG}" -format UDZO -o "${DMG_NAME}"
    rm -f "${TEMP_DMG}"
fi

# Clean up
rm -rf "${DMG_TEMP}"

echo ""
echo "✅ DMG created successfully!"
echo ""
echo "📦 ${DMG_NAME}"
echo ""
echo "File size: $(du -h "${DMG_NAME}" | cut -f1)"
echo ""
echo "Next steps:"
echo "1. Test the DMG: open \"${DMG_NAME}\""
echo "2. Create a new release on GitHub"
echo "3. Upload ${DMG_NAME} to the release"
echo ""
echo "To create a release:"
echo "  gh release create v1.0.0 \"${DMG_NAME}\" --title \"Privacy Guard v1.0.0\" --notes \"Initial release\""

#!/bin/bash
# Quick release script - build and upload to GitHub

VERSION="${1:-1.0.0}"
DMG_FILE="PrivacyGuard-${VERSION}.dmg"

echo "🚀 Creating Privacy Guard Release v${VERSION}"
echo ""

# Build DMG
./package.sh

if [ ! -f "${DMG_FILE}" ]; then
    echo "❌ DMG not found"
    exit 1
fi

# Get release notes
echo ""
echo "📝 Release Notes:"
echo "- Smart screen blur when you leave"
echo "- Owner face recognition (only you can unlock)"
echo "- Stranger detection with immediate blur"
echo "- Menu bar app with system tray"
echo "- Activity log with snapshots"
echo ""

# Create GitHub release
echo "📤 Uploading to GitHub..."
gh release create "v${VERSION}" \
    "${DMG_FILE}" \
    --title "Privacy Guard v${VERSION}" \
    --notes "## Privacy Guard v${VERSION}

### Features
- 🔐 **Owner Recognition** - Only recognizes your face
- 🔒 **Smart Blur** - Blurs screen when you leave or stranger appears  
- 👆 **Click to Unlock** - Simple click to restore screen
- 📊 **System Tray** - Runs in menu bar
- 📝 **Activity Log** - Tracks presence with snapshots
- 🎭 **Stranger Alert** - Auto-blur when someone else sits at your desk

### Installation
1. Download the DMG
2. Drag app to Applications
3. Launch and grant permissions
4. Register your face via menu

### Requirements
- macOS 10.14+
- Camera access
- Screen recording permission

See README.md for full documentation." \
    --target ""

echo ""
echo "✅ Release v${VERSION} created!"
echo "🔗 https://github.com/ccjr1120/privacy-guard/releases/tag/v${VERSION}"

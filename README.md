# Privacy Guard - Smart Screen Privacy Shield

A macOS app that protects your screen privacy by blurring it when you step away.

## Features

- 🤖 **Face Detection** - Uses webcam to detect if you're at your desk
- 🔒 **Smart Blur** - Blurs the entire screen when you leave
- 👆 **Click to Unlock** - Simply click anywhere to restore the screen
- 📊 **System Tray** - Runs in the menu bar with easy controls
- 📝 **Activity Log** - Records when you leave and return (with face snapshots)
- 🎯 **Privacy First** - All processing is local, no data leaves your machine

## How It Works

1. The app monitors your presence using the webcam
2. When no face is detected for a few seconds, the screen blurs
3. Click anywhere on the blurred screen to restore it
4. Or just come back - face detection will auto-restore

## Installation

### Option 1: Download Pre-built App
Download from [Releases](../../releases)

### Option 2: Build from Source

```bash
# 1. Clone repository
git clone https://github.com/ccjr1120/privacy-guard.git
cd privacy-guard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python privacy_guard.py

# Or build app bundle
python setup.py py2app
```

## Permissions Required

- **Camera** - For face detection
- **Screen Recording** - To capture and blur the screen
- **Accessibility** - To detect global mouse clicks

## Configuration

Edit `config.yaml`:

```yaml
# Detection interval (seconds)
check_interval: 0.5

# Seconds without face before blur
absence_threshold: 3

# Blur intensity (10-50)
blur_amount: 20

# Save face snapshots
save_snapshots: true
snapshots_dir: "~/Pictures/PrivacyGuard"

# Camera index
camera_index: 0
```

## License

MIT

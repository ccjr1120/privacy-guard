# Privacy Guard - Smart Screen Privacy Shield

A macOS app that protects your screen privacy by blurring it when you step away.
**Only recognizes the owner** - strangers trigger the blur!

## Features

- 👤 **Owner Recognition** - Uses advanced face recognition to identify only you
- 🔒 **Smart Blur** - Blurs the entire screen when you leave OR when a stranger appears
- 👆 **Click to Unlock** - Simply click anywhere to restore the screen
- 📊 **System Tray** - Runs in the menu bar with easy controls
- 📝 **Activity Log** - Records when you leave, return, or strangers appear
- 🎭 **Stranger Detection** - Automatically blurs if someone else sits at your desk
- 🎯 **Privacy First** - All processing is local, no data leaves your machine

## How It Works

1. **Register your face** (one-time setup)
2. The app monitors your presence using the webcam
3. **Three scenarios:**
   - You leave → Screen blurs
   - You return → Screen restores automatically
   - Stranger appears → Screen blurs immediately
4. Click anywhere on the blurred screen to unlock

## Installation

### Option 1: Download Pre-built App
Download from [Releases](../../releases)

### Option 2: Build from Source

```bash
# 1. Clone repository
git clone https://github.com/ccjr1120/privacy-guard.git
cd privacy-guard

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python privacy_guard.py

# Or build app bundle
./package.sh
```

## First Time Setup

1. **Launch the app** - You'll see ⚠️ in the menu bar
2. **Click menu → "Register Owner Face"**
3. **Look at the camera** for 2-3 seconds
4. **Done!** The 🔒 icon means it's active and will only recognize you

## Permissions Required

- **Camera** - For face detection and recognition
- **Screen Recording** - To capture and blur the screen
- **Accessibility** - To detect global mouse clicks

## Configuration

Edit `config.yaml`:

```yaml
# Seconds without face before blur
absence_threshold: 3

# Blur intensity (10-50)
blur_amount: 20

# Blur when stranger detected
blur_on_stranger: true

# Face recognition strictness (0.4-0.6)
recognition_tolerance: 0.6

# Save face snapshots
save_snapshots: true
snapshots_dir: "~/Pictures/PrivacyGuard"
```

### Recognition Tolerance

- **0.4** - Very strict, might not recognize you with glasses/hat
- **0.6** (default) - Balanced
- **0.5** - More lenient, might accept similar-looking people

## Privacy Notes

- ✅ **Owner face data** is stored locally in `~/.privacyguard/`
- ✅ **Snapshots** saved to `~/Pictures/PrivacyGuard/` (can be disabled)
- ✅ **No network** - Everything processes locally
- ✅ **Delete anytime** - Clear the folders to remove all data

## Troubleshooting

**"No face detected" during registration**
- Ensure good lighting
- Face the camera directly
- Remove glasses/hat if needed

**Not recognizing me**
- Try re-registering with different lighting
- Lower the `recognition_tolerance` in config

**Stranger not being detected**
- Increase `recognition_tolerance` slightly
- Ensure stranger is facing the camera

## License

MIT

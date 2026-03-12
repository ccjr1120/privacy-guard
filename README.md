# Privacy Guard - Face Detection Screen Lock for Mac

A face detection screen lock tool for Mac that automatically locks your screen when you step away.

## Features

- Real-time face detection using webcam
- Automatic screen lock when you leave
- Optional auto-unlock when you return
- Runs locally, no internet required
- Lightweight model with low resource usage

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/ccjr1120/privacy-guard.git
cd privacy-guard

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Run
python privacy_guard.py

# Or with config file
python privacy_guard.py --config config.yaml

# Debug mode (shows camera feed)
python privacy_guard.py --debug
```

## Configuration

Edit `config.yaml`:

```yaml
# Detection interval (seconds)
check_interval: 0.5

# Consecutive absence threshold before locking
absence_threshold: 3

# Enable auto-unlock
auto_unlock: false

# Camera index
camera_index: 0

# Mac lock command
lock_command: "osascript -e 'tell application \"System Events\" to keystroke \"q\" using {control down, command down}'"
```

## How It Works

Uses OpenCV's Haar Cascade Classifier for face detection - lightweight and no GPU required.

## Requirements

- macOS 10.14+
- Python 3.8+
- Camera permission

## License

MIT

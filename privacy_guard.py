#!/usr/bin/env python3
"""
Privacy Guard - Smart Screen Privacy Shield
Blurs screen when you step away, click to restore
"""

import cv2
import yaml
import time
import argparse
import rumps
import os
import subprocess
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QGraphicsBlurEffect, QGraphicsScene, QGraphicsView,
    QGraphicsPixmapItem, QMainWindow
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QScreen, QImage, QKeyEvent
from PIL import Image, ImageFilter
import numpy as np
import io


class FaceDetectorThread(QThread):
    """Background thread for face detection"""
    face_detected = pyqtSignal(bool, int)  # (detected, count)
    snapshot_saved = pyqtSignal(str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True
        self.camera = None
        self.face_cascade = None
        
    def init_camera(self):
        """Initialize camera"""
        self.camera = cv2.VideoCapture(self.config['camera_index'])
        if not self.camera.isOpened():
            raise RuntimeError("Cannot open camera")
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
    def init_face_detector(self):
        """Initialize face detector"""
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
    def save_snapshot(self, frame, faces):
        """Save face snapshot"""
        if not self.config.get('save_snapshots', True):
            return
            
        snapshots_dir = Path(self.config.get('snapshots_dir', '~/Pictures/PrivacyGuard')).expanduser()
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = snapshots_dir / f"snapshot_{timestamp}.jpg"
        
        # Draw rectangle around faces
        frame_copy = frame.copy()
        for (x, y, w, h) in faces:
            cv2.rectangle(frame_copy, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame_copy, f"Face {faces.index((x,y,w,h))+1}", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        cv2.imwrite(str(filename), frame_copy)
        self.snapshot_saved.emit(str(filename))
        
    def detect_faces(self, frame) -> list:
        """Detect faces in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fd_config = self.config.get('face_detection', {})
        min_size = tuple(fd_config.get('min_size', [100, 100]))
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=fd_config.get('scale_factor', 1.1),
            minNeighbors=fd_config.get('min_neighbors', 5),
            minSize=min_size
        )
        return faces
        
    def run(self):
        """Main detection loop"""
        try:
            self.init_camera()
            self.init_face_detector()
        except Exception as e:
            print(f"Camera init failed: {e}")
            return
            
        while self.running:
            ret, frame = self.camera.read()
            if not ret:
                continue
                
            faces = self.detect_faces(frame)
            face_count = len(faces)
            
            # Save snapshot if faces detected
            if face_count > 0:
                self.save_snapshot(frame, faces)
                
            self.face_detected.emit(face_count > 0, face_count)
            time.sleep(self.config.get('check_interval', 0.5))
            
        self.cleanup()
        
    def cleanup(self):
        if self.camera:
            self.camera.release()


class BlurOverlay(QMainWindow):
    """Full screen blur overlay window"""
    
    def __init__(self, blur_amount=20):
        super().__init__()
        self.blur_amount = blur_amount
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the blur overlay UI"""
        self.setWindowTitle("Privacy Guard")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        
        # Get all screens
        screens = QApplication.screens()
        if screens:
            # Use primary screen geometry
            geometry = screens[0].geometry()
            self.setGeometry(geometry)
            
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Blur label
        self.blur_label = QLabel("Click anywhere to restore")
        self.blur_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.blur_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 48px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.blur_label)
        
        # Capture and blur screen
        self.update_blur()
        
    def update_blur(self):
        """Capture and blur the screen"""
        try:
            # Capture screen using screencapture
            timestamp = int(time.time() * 1000)
            temp_path = f"/tmp/privacy_guard_{timestamp}.png"
            
            subprocess.run(
                ["screencapture", "-x", temp_path],
                check=True,
                capture_output=True
            )
            
            # Open and blur image
            img = Image.open(temp_path)
            blurred = img.filter(ImageFilter.GaussianBlur(radius=self.blur_amount))
            
            # Convert to QPixmap
            buffer = io.BytesIO()
            blurred.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            
            # Scale to fit screen
            screen = QApplication.primaryScreen().geometry()
            scaled = pixmap.scaled(
                screen.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Create blurred background
            palette = self.palette()
            # We'll use a simple approach - semi-transparent overlay
            
            # Clean up temp file
            os.remove(temp_path)
            
        except Exception as e:
            print(f"Blur capture failed: {e}")
            
    def mousePressEvent(self, event):
        """Handle mouse click - restore screen"""
        self.hide()
        
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press - restore on any key"""
        self.hide()


class PrivacyGuardApp(rumps.App):
    """Menu bar application"""
    
    def __init__(self, config):
        super().__init__(
            name="PrivacyGuard",
            title="🔒",
            icon=None,
            quit_button="Quit"
        )
        
        self.config = config
        self.qt_app = None
        self.blur_window = None
        self.face_thread = None
        self.absence_count = 0
        self.is_blurred = False
        self.presence_log = []
        
        # Setup menu
        self.setup_menu()
        
        # Start Qt app
        self.init_qt()
        
        # Start face detection
        self.start_detection()
        
    def setup_menu(self):
        """Setup menu bar items"""
        self.menu = [
            rumps.MenuItem("Status: Active", callback=None),
            None,
            rumps.MenuItem("Manual Blur", callback=self.manual_blur),
            rumps.MenuItem("Show Log", callback=self.show_log),
            None,
            rumps.MenuItem("Preferences", callback=self.show_preferences),
        ]
        
    def init_qt(self):
        """Initialize Qt application"""
        self.qt_app = QApplication.instance() or QApplication([])
        self.blur_window = BlurOverlay(
            blur_amount=self.config.get('blur_amount', 20)
        )
        
    def start_detection(self):
        """Start face detection thread"""
        self.face_thread = FaceDetectorThread(self.config)
        self.face_thread.face_detected.connect(self.on_face_detected)
        self.face_thread.snapshot_saved.connect(self.on_snapshot_saved)
        self.face_thread.start()
        
    def on_face_detected(self, detected: bool, count: int):
        """Handle face detection result"""
        if detected:
            if self.absence_count > 0:
                # Face returned
                self.log_event("return", f"Detected {count} face(s)")
                if self.is_blurred and self.config.get('auto_restore', True):
                    self.restore_screen()
            self.absence_count = 0
        else:
            self.absence_count += 1
            threshold = self.config.get('absence_threshold', 3)
            
            if self.absence_count >= threshold and not self.is_blurred:
                # User left
                self.log_event("leave", "No face detected")
                self.blur_screen()
                
    def on_snapshot_saved(self, path: str):
        """Handle snapshot saved"""
        print(f"Snapshot saved: {path}")
        
    def log_event(self, event_type: str, details: str):
        """Log presence event"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.presence_log.append({
            'time': timestamp,
            'type': event_type,
            'details': details
        })
        
    def blur_screen(self):
        """Show blur overlay"""
        if self.blur_window:
            self.blur_window.showFullScreen()
            self.is_blurred = True
            self.title = "🔓"
            
    def restore_screen(self):
        """Hide blur overlay"""
        if self.blur_window:
            self.blur_window.hide()
            self.is_blurred = False
            self.title = "🔒"
            
    def manual_blur(self, _):
        """Manual blur trigger"""
        self.blur_screen()
        
    def show_log(self, _):
        """Show presence log"""
        if not self.presence_log:
            rumps.alert("No events recorded yet")
            return
            
        log_text = "Recent Events:\n\n"
        for event in self.presence_log[-10:]:  # Show last 10
            icon = "🚶" if event['type'] == 'leave' else "👋"
            log_text += f"{icon} {event['time']}: {event['details']}\n"
            
        rumps.alert(log_text)
        
    def show_preferences(self, _):
        """Show preferences"""
        rumps.alert(
            "Preferences",
            f"Check Interval: {self.config.get('check_interval', 0.5)}s\n"
            f"Absence Threshold: {self.config.get('absence_threshold', 3)}s\n"
            f"Blur Amount: {self.config.get('blur_amount', 20)}\n"
            f"Auto Restore: {self.config.get('auto_restore', True)}\n"
            f"Save Snapshots: {self.config.get('save_snapshots', True)}"
        )
        
    def run(self):
        """Run the app"""
        super().run()
        
    def cleanup(self):
        """Cleanup resources"""
        if self.face_thread:
            self.face_thread.running = False
            self.face_thread.wait()


def load_config(path: str = "config.yaml") -> dict:
    """Load configuration file"""
    default_config = {
        'check_interval': 0.5,
        'absence_threshold': 3,
        'blur_amount': 20,
        'auto_restore': True,
        'save_snapshots': True,
        'snapshots_dir': '~/Pictures/PrivacyGuard',
        'camera_index': 0,
        'face_detection': {
            'scale_factor': 1.1,
            'min_neighbors': 5,
            'min_size': [100, 100]
        }
    }
    
    if Path(path).exists():
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            default_config.update(config)
    
    return default_config


def main():
    parser = argparse.ArgumentParser(description='Privacy Guard - Smart Screen Privacy Shield')
    parser.add_argument('--config', '-c', default='config.yaml', help='Configuration file path')
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    app = PrivacyGuardApp(config)
    
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.cleanup()


if __name__ == '__main__':
    main()

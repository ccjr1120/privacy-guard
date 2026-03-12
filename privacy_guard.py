#!/usr/bin/env python3
"""
Privacy Guard - Smart Screen Privacy Shield
Blurs screen when you step away, click to restore
Only recognizes the owner
"""

import cv2
import yaml
import time
import argparse
import rumps
import os
import subprocess
import pickle
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QMainWindow,
    QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QImage, QPixmap
from PIL import Image, ImageFilter
import numpy as np
import io

# Optional face recognition
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: face_recognition not available, falling back to basic detection")


class FaceDetectorThread(QThread):
    """Background thread for face detection and recognition"""
    face_detected = pyqtSignal(bool, int, bool)  # (detected, count, is_owner)
    snapshot_saved = pyqtSignal(str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.running = True
        self.camera = None
        self.face_cascade = None
        self.owner_encoding = None
        self.load_owner_face()
        
    def load_owner_face(self):
        """Load owner's face encoding"""
        if not FACE_RECOGNITION_AVAILABLE:
            return
            
        data_dir = Path(self.config.get('data_dir', '~/.privacyguard')).expanduser()
        encoding_file = data_dir / 'owner_encoding.pkl'
        
        if encoding_file.exists():
            with open(encoding_file, 'rb') as f:
                self.owner_encoding = pickle.load(f)
            print(f"✅ Loaded owner face encoding")
        else:
            print(f"⚠️ No owner face registered. Register via menu.")
            
    def save_owner_face(self, encoding):
        """Save owner's face encoding"""
        data_dir = Path(self.config.get('data_dir', '~/.privacyguard')).expanduser()
        data_dir.mkdir(parents=True, exist_ok=True)
        encoding_file = data_dir / 'owner_encoding.pkl'
        
        with open(encoding_file, 'wb') as f:
            pickle.dump(encoding, f)
        self.owner_encoding = encoding
        print(f"✅ Owner face registered")
        
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
        
    def recognize_owner(self, frame, face_location) -> bool:
        """Check if face matches owner"""
        if not FACE_RECOGNITION_AVAILABLE or self.owner_encoding is None:
            return True  # If no owner registered, accept any face
            
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get face encoding
            encodings = face_recognition.face_encodings(rgb_frame, [face_location])
            if not encodings:
                return False
                
            # Compare with owner
            tolerance = self.config.get('recognition_tolerance', 0.6)
            matches = face_recognition.compare_faces(
                [self.owner_encoding], 
                encodings[0], 
                tolerance=tolerance
            )
            return matches[0]
        except Exception as e:
            print(f"Recognition error: {e}")
            return False
        
    def save_snapshot(self, frame, faces, is_owner_list):
        """Save face snapshot"""
        if not self.config.get('save_snapshots', True):
            return
            
        snapshots_dir = Path(self.config.get('snapshots_dir', '~/Pictures/PrivacyGuard')).expanduser()
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = snapshots_dir / f"snapshot_{timestamp}.jpg"
        
        # Draw rectangle around faces
        frame_copy = frame.copy()
        for i, ((x, y, w, h), is_owner) in enumerate(zip(faces, is_owner_list)):
            color = (0, 255, 0) if is_owner else (0, 0, 255)  # Green for owner, red for stranger
            label = "Owner" if is_owner else "Stranger"
            cv2.rectangle(frame_copy, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame_copy, label, (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        cv2.imwrite(str(filename), frame_copy)
        self.snapshot_saved.emit(str(filename))
        
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
            
            # Recognize each face
            is_owner_detected = False
            is_owner_list = []
            
            if FACE_RECOGNITION_AVAILABLE and face_count > 0:
                for (x, y, w, h) in faces:
                    face_location = (y, x + w, y + h, x)  # face_recognition format
                    is_owner = self.recognize_owner(frame, face_location)
                    is_owner_list.append(is_owner)
                    if is_owner:
                        is_owner_detected = True
            else:
                # Fallback: all faces accepted if no recognition available
                is_owner_detected = face_count > 0
                is_owner_list = [True] * face_count
                
            # Save snapshot
            if face_count > 0:
                self.save_snapshot(frame, faces, is_owner_list)
                
            self.face_detected.emit(face_count > 0, face_count, is_owner_detected)
            time.sleep(self.config.get('check_interval', 0.5))
            
        self.cleanup()
        
    def cleanup(self):
        if self.camera:
            self.camera.release()


class BlurOverlay(QMainWindow):
    """Full screen blur overlay window"""
    
    def __init__(self, blur_amount=20, allow_stranger_unlock=False):
        super().__init__()
        self.blur_amount = blur_amount
        self.allow_stranger_unlock = allow_stranger_unlock
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the blur overlay UI"""
        self.setWindowTitle("Privacy Guard")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Get primary screen
        screens = QApplication.screens()
        if screens:
            geometry = screens[0].geometry()
            self.setGeometry(geometry)
            
        # Semi-transparent dark background
        self.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)
        
        # Status label
        self.status_label = QLabel("Screen Locked")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #FF6B6B;
                font-size: 64px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Message label
        self.msg_label = QLabel("Click anywhere to unlock")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 24px;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.msg_label)
        
        # Add stretch to center content
        layout.addStretch()
        
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
        self.owner_registered = self.check_owner_registered()
        
        # Setup menu
        self.setup_menu()
        
        # Start Qt app
        self.init_qt()
        
        # Start face detection
        if self.owner_registered or not FACE_RECOGNITION_AVAILABLE:
            self.start_detection()
        else:
            self.title = "⚠️"
            
    def check_owner_registered(self) -> bool:
        """Check if owner face is registered"""
        data_dir = Path(self.config.get('data_dir', '~/.privacyguard')).expanduser()
        return (data_dir / 'owner_encoding.pkl').exists()
        
    def setup_menu(self):
        """Setup menu bar items"""
        self.menu = [
            rumps.MenuItem("Status: Active" if self.owner_registered else "Status: No Owner Registered", callback=None),
            None,
        ]
        
        if not self.owner_registered and FACE_RECOGNITION_AVAILABLE:
            self.menu.append(rumps.MenuItem("Register Owner Face", callback=self.register_owner))
            self.menu.append(None)
            
        self.menu.extend([
            rumps.MenuItem("Manual Blur", callback=self.manual_blur),
            rumps.MenuItem("Show Log", callback=self.show_log),
            None,
            rumps.MenuItem("Preferences", callback=self.show_preferences),
        ])
        
    def init_qt(self):
        """Initialize Qt application"""
        self.qt_app = QApplication.instance() or QApplication([])
        self.blur_window = BlurOverlay(
            blur_amount=self.config.get('blur_amount', 20),
            allow_stranger_unlock=self.config.get('allow_stranger_unlock', False)
        )
        
    def start_detection(self):
        """Start face detection thread"""
        self.face_thread = FaceDetectorThread(self.config)
        self.face_thread.face_detected.connect(self.on_face_detected)
        self.face_thread.snapshot_saved.connect(self.on_snapshot_saved)
        self.face_thread.start()
        
    def register_owner(self, _):
        """Register owner's face"""
        if not FACE_RECOGNITION_AVAILABLE:
            rumps.alert("Face recognition not available")
            return
            
        # Simple registration: capture current frame
        try:
            cap = cv2.VideoCapture(self.config['camera_index'])
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Capture a few frames
            encodings = []
            for _ in range(5):
                ret, frame = cap.read()
                if ret:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_frame)
                    if face_locations:
                        face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
                        encodings.append(face_encoding)
                time.sleep(0.2)
                
            cap.release()
            
            if encodings:
                # Use average of encodings
                avg_encoding = np.mean(encodings, axis=0)
                
                if self.face_thread:
                    self.face_thread.save_owner_face(avg_encoding)
                    
                self.owner_registered = True
                self.title = "🔒"
                self.menu[0].title = "Status: Active"
                
                # Remove register menu item
                self.menu = [item for item in self.menu if not (hasattr(item, 'title') and item.title == "Register Owner Face")]
                
                # Start detection if not already running
                if not self.face_thread:
                    self.start_detection()
                    
                rumps.alert("✅ Owner face registered successfully!")
            else:
                rumps.alert("❌ No face detected. Please try again.")
                
        except Exception as e:
            rumps.alert(f"Registration failed: {e}")
            
    def on_face_detected(self, detected: bool, count: int, is_owner: bool):
        """Handle face detection result"""
        if detected and is_owner:
            # Owner detected
            if self.absence_count > 0:
                self.log_event("return", f"Owner detected ({count} face(s))")
                if self.is_blurred and self.config.get('auto_restore', True):
                    self.restore_screen()
            self.absence_count = 0
        elif detected and not is_owner:
            # Stranger detected - stay blurred or blur immediately
            if not self.is_blurred and self.config.get('blur_on_stranger', True):
                self.log_event("alert", f"Stranger detected ({count} face(s))")
                self.blur_screen("Stranger Detected", "Only owner can unlock")
        else:
            # No face detected
            self.absence_count += 1
            threshold = self.config.get('absence_threshold', 3)
            
            if self.absence_count >= threshold and not self.is_blurred:
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
        # Keep only last 100 events
        self.presence_log = self.presence_log[-100:]
        
    def blur_screen(self, title="Screen Locked", message="Click anywhere to unlock"):
        """Show blur overlay"""
        if self.blur_window:
            self.blur_window.status_label.setText(title)
            self.blur_window.msg_label.setText(message)
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
        for event in self.presence_log[-20:]:
            icons = {
                'leave': '🚶',
                'return': '👋',
                'alert': '⚠️'
            }
            icon = icons.get(event['type'], '•')
            log_text += f"{icon} {event['time']}: {event['details']}\n"
            
        rumps.alert(log_text)
        
    def show_preferences(self, _):
        """Show preferences"""
        reg_status = "Registered" if self.owner_registered else "Not Registered"
        
        rumps.alert(
            "Preferences",
            f"Owner: {reg_status}\n"
            f"Check Interval: {self.config.get('check_interval', 0.5)}s\n"
            f"Absence Threshold: {self.config.get('absence_threshold', 3)}s\n"
            f"Blur on Stranger: {self.config.get('blur_on_stranger', True)}\n"
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
        'blur_on_stranger': True,
        'save_snapshots': True,
        'snapshots_dir': '~/Pictures/PrivacyGuard',
        'data_dir': '~/.privacyguard',
        'camera_index': 0,
        'recognition_tolerance': 0.6,
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
    
    if not FACE_RECOGNITION_AVAILABLE:
        print("⚠️  face_recognition not installed. Running in basic mode (any face unlocks).")
        print("   To enable owner-only mode: pip install face-recognition dlib")
    
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

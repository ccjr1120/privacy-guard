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
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QMainWindow,
    QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QImage, QPixmap, QPainter, QColor, QFont

# UI components
from ui.settings_window import SettingsWindow
from ui.face_registration_dialog import FaceRegistrationDialog
from ui.dashboard_window import DashboardWindow
from PIL import Image, ImageFilter, ImageGrab
import numpy as np
import io

# Face recognition
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: face_recognition not available")


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


class _BlurCanvas(QWidget):
    """Widget that paints the frosted glass overlay"""
    
    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()
        
        if self.overlay.blurred_pixmap and not self.overlay.blurred_pixmap.isNull():
            painter.drawPixmap(rect, self.overlay.blurred_pixmap)
            painter.fillRect(rect, QColor(255, 255, 255, 35))
        else:
            painter.fillRect(rect, QColor(240, 245, 255, 230))
        
        painter.setPen(QColor(60, 60, 80))
        font = QFont()
        font.setPointSize(48)
        font.setBold(True)
        painter.setFont(font)
        text_rect = rect.adjusted(50, rect.height() // 3, -50, -50)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.overlay.status_text)
        
        font.setPointSize(18)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(100, 100, 120))
        msg_rect = text_rect.adjusted(0, 80, 0, 0)
        painter.drawText(msg_rect, Qt.AlignmentFlag.AlignCenter, self.overlay.msg_text)


class BlurOverlay(QMainWindow):
    """Full screen frosted glass overlay - captures and blurs screen content"""
    
    def __init__(self, blur_amount=20, allow_stranger_unlock=False):
        super().__init__()
        self.blur_amount = blur_amount
        self.allow_stranger_unlock = allow_stranger_unlock
        self.blurred_pixmap = None
        self.status_text = "Screen Locked"
        self.msg_text = "Click anywhere to unlock"
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the overlay window"""
        self.setWindowTitle("Privacy Guard")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Get primary screen geometry
        screens = QApplication.screens()
        if screens:
            geometry = screens[0].geometry()
            self.setGeometry(geometry)
        
        self.central = _BlurCanvas(self)
        self.setCentralWidget(self.central)
        
    def capture_and_blur_screen(self) -> Optional[QPixmap]:
        """Capture screen and apply blur for frosted glass effect"""
        try:
            # Capture screen (requires Screen Recording permission on macOS)
            screenshot = ImageGrab.grab()
            if screenshot is None or screenshot.size[0] == 0:
                return None
                
            # Resize for performance if needed, then blur
            w, h = screenshot.size
            scale = min(1.0, 800 / max(w, h)) if max(w, h) > 800 else 1.0
            if scale < 1.0:
                screenshot = screenshot.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            
            # Gaussian blur for frosted glass effect
            blurred = screenshot.filter(ImageFilter.GaussianBlur(radius=self.blur_amount))
            
            # Restore to original size if we scaled down
            if scale < 1.0:
                blurred = blurred.resize((w, h), Image.Resampling.LANCZOS)
            
            # Convert PIL to QPixmap
            if blurred.mode != 'RGB':
                blurred = blurred.convert('RGB')
            data = blurred.tobytes('raw', 'RGB')
            qimg = QImage(data, blurred.width, blurred.height, blurred.width * 3, QImage.Format.Format_RGB888)
            return QPixmap.fromImage(qimg)
        except Exception as e:
            print(f"Screen capture failed: {e}, using fallback")
            return None
            
    def showEvent(self, event):
        """Refresh display when showing (capture done in blur_screen before show)"""
        super().showEvent(event)
        if self.blurred_pixmap is None:
            self.blurred_pixmap = self.capture_and_blur_screen()
        self.central.update()
        
    def set_status(self, title: str, message: str):
        """Update status text (called before show)"""
        self.status_text = title
        self.msg_text = message
        self.central.update()
        
    def _make_label_proxy(self, attr: str):
        """Create proxy for status_label/msg_label compatibility"""
        class _LabelProxy:
            def __init__(self, overlay, attr_name):
                self._overlay = overlay
                self._attr = attr_name
            def setText(self, text):
                setattr(self._overlay, self._attr, text)
                self._overlay.central.update()
        return _LabelProxy(self, attr)
    
    @property
    def status_label(self):
        return self._make_label_proxy('status_text')
    
    @property 
    def msg_label(self):
        return self._make_label_proxy('msg_text')
        
    def mousePressEvent(self, event):
        self.hide()
        
    def keyPressEvent(self, event: QKeyEvent):
        self.hide()


class PrivacyGuardApp(rumps.App):
    """Menu bar application"""
    
    def __init__(self, config, config_path: str = "config.yaml"):
        super().__init__(
            name="PrivacyGuard",
            title="🔒",
            icon=None,
            quit_button="Quit"
        )
        
        self.config = config
        self.config_path = config_path
        self.qt_app = None
        self.blur_window = None
        self.face_thread = None
        self.dashboard_window = None
        self.absence_count = 0
        self.is_blurred = False
        self.presence_log = []
        self.presence_state = "present"  # present | away | returned
        self._returned_timer = None
        self.owner_registered = self.check_owner_registered()
        
        # Setup menu
        self.setup_menu()
        
        # Start Qt app
        self.init_qt()
        
        # Process Qt events periodically (rumps uses Cocoa loop, Qt signals need processEvents)
        self._qt_timer = rumps.Timer(self._process_qt_events, 0.2)
        self._qt_timer.start()
        
        # Start face detection
        if self.owner_registered or not FACE_RECOGNITION_AVAILABLE:
            self.start_detection()
        else:
            self.title = "⚠️"
            
    def _process_qt_events(self, _=None):
        """Process pending Qt events so signals from face thread get handled"""
        qt_app = QApplication.instance()
        if qt_app:
            qt_app.processEvents()
            
    def check_owner_registered(self) -> bool:
        """Check if owner face is registered"""
        data_dir = Path(self.config.get('data_dir', '~/.privacyguard')).expanduser()
        return (data_dir / 'owner_encoding.pkl').exists()
        
    def setup_menu(self):
        """Setup menu bar items"""
        menu_items = [
            rumps.MenuItem("Status: Active" if self.owner_registered else "Status: No Owner Registered", callback=None),
            None,
            rumps.MenuItem("打开控制面板", callback=self.open_dashboard),
            None,
        ]
        
        if FACE_RECOGNITION_AVAILABLE:
            label = "更新人脸" if self.owner_registered else "注册人脸"
            menu_items.append(rumps.MenuItem(label, callback=self.register_owner))
            menu_items.append(None)
            
        menu_items.extend([
            rumps.MenuItem("Manual Blur", callback=self.manual_blur),
            rumps.MenuItem("Show Log", callback=self.show_log),
            None,
            rumps.MenuItem("设置", callback=self.open_settings),
        ])
        
        self.menu = menu_items
        
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
        """Register owner's face - opens UI dialog"""
        self.open_face_registration()
            
    def on_face_detected(self, detected: bool, count: int, is_owner: bool):
        """Handle face detection result"""
        if detected and is_owner:
            # Owner detected - 人回来
            was_away = self.presence_state == "away"
            if self.absence_count > 0:
                self.log_event("return", f"Owner detected ({count} face(s))")
                if self.is_blurred and self.config.get('auto_restore', True):
                    self.restore_screen()
            self.absence_count = 0
            self.presence_state = "returned" if was_away else "present"
            self._update_dashboard_presence()
            if was_away:
                self._schedule_returned_reset()
        elif detected and not is_owner:
            # Stranger detected - stay blurred or blur immediately
            if not self.is_blurred and self.config.get('blur_on_stranger', True):
                self.log_event("alert", f"Stranger detected ({count} face(s))")
                self.blur_screen("Stranger Detected", "Only owner can unlock")
        else:
            # No face detected - 人离开
            self.absence_count += 1
            threshold = self.config.get('absence_threshold', 3)
            
            if self.absence_count >= threshold:
                if self.presence_state != "away":
                    self.log_event("leave", "No face detected")
                self.presence_state = "away"
                self._update_dashboard_presence()
                # 不显示全屏遮罩，仅在面板显示状态
                if self.is_blurred:
                    pass  # 保持原有模糊状态
                # 不再自动 blur_screen()
                
    def on_snapshot_saved(self, path: str):
        """Handle snapshot saved"""
        print(f"Snapshot saved: {path}")
        
    def _update_dashboard_presence(self):
        """Update dashboard presence indicator if open"""
        if self.dashboard_window and self.dashboard_window.isVisible():
            self.dashboard_window.update_presence_indicator()
    
    def _schedule_returned_reset(self):
        """Reset 'returned' to 'present' after a few seconds"""
        if self._returned_timer:
            self._returned_timer.stop()
        self._returned_timer = rumps.Timer(lambda _: self._reset_returned_state(), 3)
        self._returned_timer.start()
    
    def _reset_returned_state(self):
        if self.presence_state == "returned":
            self.presence_state = "present"
            self._update_dashboard_presence()
        if self._returned_timer:
            self._returned_timer.stop()
            self._returned_timer = None
    
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
            # Capture screen BEFORE showing overlay (so we get clean content)
            self.blur_window.blurred_pixmap = self.blur_window.capture_and_blur_screen()
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
        
    def open_settings(self, _=None):
        """Open settings window"""
        config_path = Path(self.config_path)
        if not config_path.is_absolute():
            config_path = Path.cwd() / config_path
        win = SettingsWindow(self.config, str(config_path), parent=None)
        win.exec()
        
    def open_dashboard(self, _=None):
        """Open dashboard/control panel"""
        if self.dashboard_window is None or not self.dashboard_window.isVisible():
            self.dashboard_window = DashboardWindow(self, parent=None)
        self.dashboard_window.show()
        self.dashboard_window.raise_()
        self.dashboard_window.activateWindow()
        
    def open_face_registration(self):
        """Open face registration dialog (stops detection during registration)"""
        if not FACE_RECOGNITION_AVAILABLE:
            rumps.alert("人脸识别库未安装")
            return
            
        # Stop face detection to free camera
        was_running = self.face_thread and self.face_thread.isRunning()
        if was_running:
            self.face_thread.running = False
            self.face_thread.wait(3000)
            
        def on_success(_encoding):
            self.owner_registered = True
            self.title = "🔒"
            if hasattr(self, 'menu') and self.menu:
                for item in self.menu:
                    if hasattr(item, 'title') and item.title == "Status: No Owner Registered":
                        item.title = "Status: Active"
                        break
                        
        dialog = FaceRegistrationDialog(self.config, on_success_callback=on_success)
        dialog.exec()
        
        # Restart face detection
        if was_running or self.owner_registered:
            self.start_detection()
        
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


def get_config_path(specified: str) -> str:
    """Resolve config file path (handles packaged app)"""
    import sys
    if getattr(sys, 'frozen', False):
        # Running as packaged app - use user dir (Resources may be read-only)
        data_dir = Path.home() / '.privacyguard'
        data_dir.mkdir(parents=True, exist_ok=True)
        user_config = data_dir / 'config.yaml'
        # Copy from bundle if user config doesn't exist
        bundle_config = Path(sys.executable).parent / 'Resources' / Path(specified).name
        if not user_config.exists() and bundle_config.exists():
            import shutil
            shutil.copy(bundle_config, user_config)
        return str(user_config)
    return specified


def main():
    parser = argparse.ArgumentParser(description='Privacy Guard - Smart Screen Privacy Shield')
    parser.add_argument('--config', '-c', default='config.yaml', help='Configuration file path')
    args = parser.parse_args()
    
    config_path = get_config_path(args.config)
    
    if not FACE_RECOGNITION_AVAILABLE:
        print("⚠️  face_recognition not installed. Running in basic mode (any face unlocks).")
        print("   To enable owner-only mode: pip install face-recognition dlib")
    
    config = load_config(config_path)
    
    app = PrivacyGuardApp(config, config_path=config_path)
    
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.cleanup()


if __name__ == '__main__':
    main()

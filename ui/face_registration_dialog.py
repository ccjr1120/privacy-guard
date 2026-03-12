"""
Face Registration Dialog - Register owner face with live camera preview
"""

import cv2
import pickle
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap


class FaceRegistrationDialog(QDialog):
    """Dialog for registering owner's face with live preview"""
    
    def __init__(self, config: dict, on_success_callback=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.on_success_callback = on_success_callback
        self.camera = None
        self.encodings = []
        self.capture_count = 0
        self.required_captures = 5
        self.is_registering = False
        self.face_recognition = None
        
        try:
            import face_recognition
            self.face_recognition = face_recognition
        except ImportError:
            pass
            
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("注册主人人脸")
        self.setMinimumSize(640, 520)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        self.instruction_label = QLabel(
            "请正对摄像头，保持面部在画面中央\n"
            "点击「开始注册」后，请保持姿势 2-3 秒"
        )
        self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instruction_label.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(self.instruction_label)
        
        # Camera preview
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(640, 480)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a2e;
                border: 2px solid #4a4a6a;
                border-radius: 8px;
            }
        """)
        self.preview_label.setText("摄像头未启动")
        layout.addWidget(self.preview_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 13px; color: #888; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.required_captures)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m 已采集")
        layout.addWidget(self.progress_bar)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.start_btn = QPushButton("开始注册")
        self.start_btn.clicked.connect(self.start_registration)
        btn_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Timer for camera updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        
    def showEvent(self, event):
        super().showEvent(event)
        self.init_camera()
        
    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)
        
    def init_camera(self):
        """Initialize camera"""
        if self.camera is not None:
            return
            
        try:
            self.camera = cv2.VideoCapture(self.config.get('camera_index', 0))
            if not self.camera.isOpened():
                self.status_label.setText("❌ 无法打开摄像头")
                return
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.timer.start(30)  # ~33 fps
        except Exception as e:
            self.status_label.setText(f"❌ 摄像头错误: {e}")
            
    def stop_camera(self):
        """Release camera"""
        self.timer.stop()
        if self.camera:
            self.camera.release()
            self.camera = None
            
    def update_frame(self):
        """Update camera preview"""
        if not self.camera or not self.camera.isOpened():
            return
            
        ret, frame = self.camera.read()
        if not ret:
            return
            
        # Draw face detection overlay if registering
        if self.is_registering and self.face_recognition:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = self.face_recognition.face_locations(rgb_frame)
            
            if face_locations:
                # Draw green rectangle around face
                for (top, right, bottom, left) in face_locations:
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, "Face Detected", (left, top - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                if self.capture_count > 0:
                    self.status_label.setText(f"✅ 检测到人脸 - 正在采集 ({self.capture_count}/{self.required_captures})")
                    self.status_label.setStyleSheet("font-size: 13px; color: #4ade80; padding: 5px;")
            else:
                if self.capture_count > 0:
                    self.status_label.setText("⚠️ 请保持面部在画面中")
                    self.status_label.setStyleSheet("font-size: 13px; color: #fbbf24; padding: 5px;")
                else:
                    self.status_label.setText("请将面部对准摄像头")
                    self.status_label.setStyleSheet("font-size: 13px; color: #888; padding: 5px;")
                    
        # Convert to QPixmap
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(qt_image)
        scaled = pixmap.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.preview_label.setPixmap(scaled)
        
    def start_registration(self):
        """Start the registration process"""
        if not self.face_recognition:
            self.status_label.setText("❌ 人脸识别库未安装")
            self.status_label.setStyleSheet("font-size: 13px; color: #ef4444; padding: 5px;")
            return
            
        self.encodings = []
        self.capture_count = 0
        self.is_registering = True
        self.start_btn.setEnabled(False)
        self.instruction_label.setText("请保持姿势，正在采集人脸数据...")
        self.status_label.setText("准备采集...")
        self.progress_bar.setValue(0)
        
        # Use timer to capture frames
        QTimer.singleShot(500, self.capture_frame)
        
    def capture_frame(self):
        """Capture one frame for encoding"""
        if self.capture_count >= self.required_captures:
            self.finish_registration()
            return
            
        if not self.camera or not self.camera.isOpened():
            self.status_label.setText("❌ 摄像头不可用")
            self.start_btn.setEnabled(True)
            return
            
        ret, frame = self.camera.read()
        if not ret:
            QTimer.singleShot(200, self.capture_frame)
            return
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = self.face_recognition.face_locations(rgb_frame)
        
        if face_locations:
            try:
                encoding = self.face_recognition.face_encodings(rgb_frame, face_locations)[0]
                self.encodings.append(encoding)
                self.capture_count += 1
                self.progress_bar.setValue(self.capture_count)
            except Exception as e:
                print(f"Encoding error: {e}")
                
        # Continue capturing
        if self.capture_count < self.required_captures:
            QTimer.singleShot(300, self.capture_frame)
        else:
            self.finish_registration()
            
    def finish_registration(self):
        """Save encoding and finish"""
        self.start_btn.setEnabled(True)
        
        if len(self.encodings) < 2:
            self.status_label.setText("❌ 采集样本不足，请重试")
            self.status_label.setStyleSheet("font-size: 13px; color: #ef4444; padding: 5px;")
            self.instruction_label.setText("请正对摄像头，点击「开始注册」重试")
            self.progress_bar.setValue(0)
            self.encodings = []
            self.capture_count = 0
            self.is_registering = False
            self.start_btn.setEnabled(True)
            return
            
        # Average encodings
        avg_encoding = np.mean(self.encodings, axis=0)
        
        # Save to file
        data_dir = Path(self.config.get('data_dir', '~/.privacyguard')).expanduser()
        data_dir.mkdir(parents=True, exist_ok=True)
        encoding_file = data_dir / 'owner_encoding.pkl'
        
        with open(encoding_file, 'wb') as f:
            pickle.dump(avg_encoding, f)
            
        self.status_label.setText("✅ 注册成功！")
        self.status_label.setStyleSheet("font-size: 13px; color: #4ade80; font-weight: bold; padding: 5px;")
        self.instruction_label.setText("主人人脸已成功注册，现在只有您能解锁屏幕")
        
        self.is_registering = False
        self.start_btn.setEnabled(True)
        if self.on_success_callback:
            self.on_success_callback(avg_encoding)
            
        QTimer.singleShot(1500, self.accept)

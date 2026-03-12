"""
Settings Window - Full UI for adjusting Privacy Guard configuration
"""

import yaml
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QSpinBox, QDoubleSpinBox, QSlider, QCheckBox, QLineEdit,
    QPushButton, QLabel, QFileDialog, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt


class SettingsWindow(QDialog):
    """Settings dialog with all config options"""
    
    def __init__(self, config: dict, config_path: str, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.config_path = config_path
        self.setup_ui()
        self.load_values()
        
    def setup_ui(self):
        self.setWindowTitle("Privacy Guard - 设置")
        self.setMinimumWidth(450)
        self.setMinimumHeight(500)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Detection group
        detection_group = QGroupBox("检测设置")
        detection_layout = QFormLayout()
        
        self.check_interval = QDoubleSpinBox()
        self.check_interval.setRange(0.1, 5.0)
        self.check_interval.setSingleStep(0.1)
        self.check_interval.setSuffix(" 秒")
        detection_layout.addRow("检测间隔:", self.check_interval)
        
        self.absence_threshold = QSpinBox()
        self.absence_threshold.setRange(1, 30)
        self.absence_threshold.setSuffix(" 次")
        detection_layout.addRow("离开阈值:", self.absence_threshold)
        
        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 10)
        detection_layout.addRow("摄像头索引:", self.camera_index)
        
        detection_group.setLayout(detection_layout)
        layout.addWidget(detection_group)
        
        # Blur group
        blur_group = QGroupBox("模糊设置")
        blur_layout = QFormLayout()
        
        self.blur_amount = QSlider(Qt.Orientation.Horizontal)
        self.blur_amount.setRange(10, 50)
        self.blur_amount_value = QLabel("20")
        self.blur_amount.valueChanged.connect(lambda v: self.blur_amount_value.setText(str(v)))
        blur_row = QHBoxLayout()
        blur_row.addWidget(self.blur_amount)
        blur_row.addWidget(self.blur_amount_value, 0, Qt.AlignmentFlag.AlignRight)
        blur_layout.addRow("模糊强度:", blur_row)
        
        blur_group.setLayout(blur_layout)
        layout.addWidget(blur_group)
        
        # Behavior group
        behavior_group = QGroupBox("行为设置")
        behavior_layout = QFormLayout()
        
        self.auto_restore = QCheckBox("检测到主人时自动恢复")
        behavior_layout.addRow(self.auto_restore)
        
        self.blur_on_stranger = QCheckBox("检测到陌生人时立即模糊")
        behavior_layout.addRow(self.blur_on_stranger)
        
        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)
        
        # Face recognition group
        face_group = QGroupBox("人脸识别")
        face_layout = QFormLayout()
        
        self.recognition_tolerance = QDoubleSpinBox()
        self.recognition_tolerance.setRange(0.3, 0.8)
        self.recognition_tolerance.setSingleStep(0.05)
        self.recognition_tolerance.setDecimals(2)
        face_layout.addRow("识别容差 (越小越严格):", self.recognition_tolerance)
        
        face_group.setLayout(face_layout)
        layout.addWidget(face_group)
        
        # Snapshots group
        snapshot_group = QGroupBox("快照")
        snapshot_layout = QFormLayout()
        
        self.save_snapshots = QCheckBox("保存检测到的人脸快照")
        snapshot_layout.addRow(self.save_snapshots)
        
        snapshots_row = QHBoxLayout()
        self.snapshots_dir = QLineEdit()
        self.snapshots_dir.setPlaceholderText("~/Pictures/PrivacyGuard")
        snapshots_row.addWidget(self.snapshots_dir)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_snapshots_dir)
        snapshots_row.addWidget(browse_btn)
        snapshot_layout.addRow("快照目录:", snapshots_row)
        
        snapshot_group.setLayout(snapshot_layout)
        layout.addWidget(snapshot_group)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("保存")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_and_close)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)
        
    def browse_snapshots_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择快照保存目录")
        if path:
            self.snapshots_dir.setText(path)
            
    def load_values(self):
        """Load config values into UI"""
        self.check_interval.setValue(self.config.get('check_interval', 0.5))
        self.absence_threshold.setValue(self.config.get('absence_threshold', 3))
        self.camera_index.setValue(self.config.get('camera_index', 0))
        self.blur_amount.setValue(self.config.get('blur_amount', 20))
        self.auto_restore.setChecked(self.config.get('auto_restore', True))
        self.blur_on_stranger.setChecked(self.config.get('blur_on_stranger', True))
        self.recognition_tolerance.setValue(self.config.get('recognition_tolerance', 0.6))
        self.save_snapshots.setChecked(self.config.get('save_snapshots', True))
        self.snapshots_dir.setText(self.config.get('snapshots_dir', '~/Pictures/PrivacyGuard'))
        
    def get_values(self) -> dict:
        """Get values from UI"""
        return {
            'check_interval': self.check_interval.value(),
            'absence_threshold': self.absence_threshold.value(),
            'camera_index': self.camera_index.value(),
            'blur_amount': self.blur_amount.value(),
            'auto_restore': self.auto_restore.isChecked(),
            'blur_on_stranger': self.blur_on_stranger.isChecked(),
            'recognition_tolerance': self.recognition_tolerance.value(),
            'save_snapshots': self.save_snapshots.isChecked(),
            'snapshots_dir': self.snapshots_dir.text().strip() or '~/Pictures/PrivacyGuard',
        }
        
    def save_and_close(self):
        """Save config to file and update"""
        values = self.get_values()
        
        # Preserve face_detection and data_dir
        values['data_dir'] = self.config.get('data_dir', '~/.privacyguard')
        values['face_detection'] = self.config.get('face_detection', {
            'scale_factor': 1.1,
            'min_neighbors': 5,
            'min_size': [100, 100]
        })
        
        # Save to YAML
        config_path = Path(self.config_path)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(values, f, allow_unicode=True, default_flow_style=False)
            
        self.config.update(values)
        self.accept()

"""
Dashboard Window - Main control panel for Privacy Guard
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QScrollArea, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class DashboardWindow(QMainWindow):
    """Main dashboard with status, controls, and event log"""
    
    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Privacy Guard - 控制面板")
        self.setMinimumSize(480, 600)
        self.setMaximumWidth(520)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Status section
        status_group = QGroupBox("状态")
        status_layout = QVBoxLayout()
        
        self.status_indicator = QLabel("🔒 运行中")
        self.status_indicator.setFont(QFont("", 18, QFont.Weight.Bold))
        self.status_indicator.setStyleSheet("color: #4ade80; padding: 5px;")
        status_layout.addWidget(self.status_indicator)
        
        # 人在/人离开/人回来 标识
        self.presence_indicator = QLabel("人在")
        self.presence_indicator.setFont(QFont("", 14, QFont.Weight.Bold))
        self.presence_indicator.setStyleSheet(
            "color: #4ade80; padding: 8px; "
            "background-color: #14532d33; border-radius: 6px;"
        )
        status_layout.addWidget(self.presence_indicator)
        
        self.owner_status = QLabel("主人: 已注册")
        self.owner_status.setStyleSheet("color: #94a3b8; padding: 2px;")
        status_layout.addWidget(self.owner_status)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Quick actions
        actions_group = QGroupBox("快捷操作")
        actions_layout = QGridLayout()
        
        self.register_btn = QPushButton("👤 注册/更新人脸")
        self.register_btn.clicked.connect(self.on_register_face)
        actions_layout.addWidget(self.register_btn, 0, 0)
        
        self.settings_btn = QPushButton("⚙️ 设置")
        self.settings_btn.clicked.connect(self.on_settings)
        actions_layout.addWidget(self.settings_btn, 0, 1)
        
        self.blur_btn = QPushButton("🔒 手动模糊")
        self.blur_btn.clicked.connect(self.on_manual_blur)
        actions_layout.addWidget(self.blur_btn, 1, 0)
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.refresh_status)
        actions_layout.addWidget(self.refresh_btn, 1, 1)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # Event log
        log_group = QGroupBox("最近事件")
        log_layout = QVBoxLayout()
        
        self.log_area = QScrollArea()
        self.log_area.setWidgetResizable(True)
        self.log_area.setFrameShape(QFrame.Shape.NoFrame)
        self.log_area.setMinimumHeight(200)
        
        self.log_content = QLabel()
        self.log_content.setWordWrap(True)
        self.log_content.setStyleSheet("color: #94a3b8; font-size: 12px; padding: 8px;")
        self.log_content.setText("暂无事件记录")
        self.log_area.setWidget(self.log_content)
        
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        
    def update_presence_indicator(self):
        """Update 人离开/人回来 indicator based on presence_state"""
        state = getattr(self.app_controller, 'presence_state', 'present')
        if state == "present":
            self.presence_indicator.setText("人在")
            self.presence_indicator.setStyleSheet(
                "color: #4ade80; padding: 8px; "
                "background-color: #14532d33; border-radius: 6px;"
            )
        elif state == "away":
            self.presence_indicator.setText("人离开")
            self.presence_indicator.setStyleSheet(
                "color: #fbbf24; padding: 8px; "
                "background-color: #78350f33; border-radius: 6px;"
            )
        else:  # returned
            self.presence_indicator.setText("人已回来")
            self.presence_indicator.setStyleSheet(
                "color: #38bdf8; padding: 8px; "
                "background-color: #0c4a6e33; border-radius: 6px;"
            )
    
    def refresh_status(self):
        """Refresh status display"""
        self.update_presence_indicator()
        owner_registered = self.app_controller.check_owner_registered()
        
        if owner_registered:
            self.owner_status.setText("主人: ✅ 已注册")
            self.owner_status.setStyleSheet("color: #4ade80; padding: 2px;")
            self.register_btn.setText("👤 更新人脸")
        else:
            self.owner_status.setText("主人: ⚠️ 未注册")
            self.owner_status.setStyleSheet("color: #fbbf24; padding: 2px;")
            self.register_btn.setText("👤 注册人脸")
            
        if self.app_controller.is_blurred:
            self.status_indicator.setText("🔓 屏幕已锁定")
            self.status_indicator.setStyleSheet("color: #fbbf24; padding: 5px;")
        else:
            self.status_indicator.setText("🔒 运行中")
            self.status_indicator.setStyleSheet("color: #4ade80; padding: 5px;")
            
        # Update log
        self.update_log()
        
    def update_log(self):
        """Update event log display"""
        log = self.app_controller.presence_log
        if not log:
            self.log_content.setText("暂无事件记录")
            return
            
        icons = {'leave': '🚶 离开', 'return': '👋 返回', 'alert': '⚠️ 陌生人'}
        lines = []
        for event in reversed(log[-15:]):
            icon = icons.get(event['type'], '•')
            lines.append(f"{icon} {event['time']}\n   {event['details']}")
        self.log_content.setText("\n\n".join(lines))
        
    def on_register_face(self):
        self.app_controller.open_face_registration()
        self.refresh_status()
        
    def on_settings(self):
        self.app_controller.open_settings()
        
    def on_manual_blur(self):
        self.app_controller.manual_blur()
        self.refresh_status()
        
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_status()

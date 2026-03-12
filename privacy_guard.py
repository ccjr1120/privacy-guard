#!/usr/bin/env python3
"""
Privacy Guard - Face Detection Screen Lock for Mac
Automatically locks screen when you step away
"""

import cv2
import yaml
import time
import subprocess
import argparse
from pathlib import Path


class PrivacyGuard:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self.load_config(config_path)
        self.camera = None
        self.face_cascade = None
        self.absence_count = 0
        self.is_locked = False
        
    def load_config(self, path: str) -> dict:
        """Load configuration file"""
        default_config = {
            'check_interval': 0.5,
            'absence_threshold': 3,
            'auto_unlock': False,
            'unlock_confidence': 0.8,
            'camera_index': 0,
            'debug': False,
            'lock_command': "osascript -e 'tell application \"System Events\" to keystroke \"q\" using {control down, command down}'",
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
    
    def init_camera(self):
        """Initialize camera"""
        self.camera = cv2.VideoCapture(self.config['camera_index'])
        if not self.camera.isOpened():
            raise RuntimeError("Cannot open camera, please check permission settings")
        
        # Lower resolution for better performance
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
    def init_face_detector(self):
        """Initialize face detector"""
        # Use OpenCV's built-in Haar Cascade Classifier
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
    def detect_faces(self, frame) -> list:
        """Detect faces in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        fd_config = self.config['face_detection']
        min_size = tuple(fd_config['min_size'])
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=fd_config['scale_factor'],
            minNeighbors=fd_config['min_neighbors'],
            minSize=min_size
        )
        
        return faces
    
    def lock_screen(self):
        """Lock the screen"""
        if not self.is_locked:
            print("🔒 Face not detected, locking screen...")
            try:
                subprocess.run(
                    self.config['lock_command'],
                    shell=True,
                    check=True,
                    capture_output=True
                )
                self.is_locked = True
                print("✅ Screen locked")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to lock screen: {e}")
    
    def unlock_screen(self):
        """Unlock screen (optional feature)"""
        if self.is_locked and self.config['auto_unlock']:
            print("🔓 Face detected, preparing to unlock...")
            # Auto-unlock on Mac is complex, can be extended here
            self.is_locked = False
    
    def run(self):
        """Main loop"""
        print("🚀 Privacy Guard starting...")
        print("Press Ctrl+C to stop")
        
        try:
            self.init_camera()
            self.init_face_detector()
        except RuntimeError as e:
            print(f"❌ Initialization failed: {e}")
            print("💡 Tip: Allow terminal camera access in System Settings > Privacy & Security > Camera")
            return
        
        print("✅ Camera started, detecting...")
        
        try:
            while True:
                ret, frame = self.camera.read()
                if not ret:
                    print("⚠️ Cannot read camera frame")
                    continue
                
                # Detect faces
                faces = self.detect_faces(frame)
                face_count = len(faces)
                
                # Debug mode: show camera feed
                if self.config['debug']:
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.imshow('Privacy Guard', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Logic
                if face_count == 0:
                    # No face detected
                    self.absence_count += 1
                    if self.absence_count >= self.config['absence_threshold']:
                        self.lock_screen()
                else:
                    # Face detected
                    if self.absence_count > 0:
                        print(f"😊 Detected {face_count} face(s)")
                        self.unlock_screen()
                    self.absence_count = 0
                
                time.sleep(self.config['check_interval'])
                
        except KeyboardInterrupt:
            print("\n👋 Program stopped")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()
        print("🧹 Resources cleaned up")


def main():
    parser = argparse.ArgumentParser(description='Privacy Guard - Face Detection Screen Lock for Mac')
    parser.add_argument('--config', '-c', default='config.yaml', help='Configuration file path')
    parser.add_argument('--debug', '-d', action='store_true', help='Debug mode (shows camera feed)')
    
    args = parser.parse_args()
    
    guard = PrivacyGuard(args.config)
    if args.debug:
        guard.config['debug'] = True
    
    guard.run()


if __name__ == '__main__':
    main()

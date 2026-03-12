#!/usr/bin/env python3
"""
Setup script for Privacy Guard Mac app bundle
"""

from setuptools import setup

APP = ['privacy_guard.py']
DATA_FILES = [
    'config.yaml',
    'README.md',
]
OPTIONS = {
    'argv_emulation': True,
    'packages': ['rumps', 'cv2', 'yaml', 'PIL', 'PyQt6'],
    'includes': ['numpy', 'subprocess', 'datetime', 'pathlib', 'io'],
    'excludes': ['tkinter', 'matplotlib'],
    'iconfile': None,  # Can add .icns file here
    'plist': {
        'CFBundleName': 'Privacy Guard',
        'CFBundleDisplayName': 'Privacy Guard',
        'CFBundleIdentifier': 'com.ccjr1120.privacyguard',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,  # Run as agent (no dock icon)
        'NSCameraUsageDescription': 'Privacy Guard needs camera access to detect your presence and protect your screen privacy.',
        'NSAppleEventsUsageDescription': 'Privacy Guard needs to detect screen changes for blur effect.',
    },
    'frameworks': [],
}

setup(
    name='Privacy Guard',
    version='1.0.0',
    description='Smart Screen Privacy Shield for Mac',
    author='ccjr1120',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

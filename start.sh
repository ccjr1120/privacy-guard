#!/bin/bash
# 启动脚本

cd "$(dirname "$0")"
source venv/bin/activate
python privacy_guard.py "$@"

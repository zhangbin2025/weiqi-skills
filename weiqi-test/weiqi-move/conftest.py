"""
pytest 配置文件
"""
import sys
from pathlib import Path

# 添加 weiqi-move 脚本目录到路径
weiqi_move_scripts = Path(__file__).parent.parent.parent / 'weiqi-move' / 'scripts'
sys.path.insert(0, str(weiqi_move_scripts))

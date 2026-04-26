#!/usr/bin/env python3
"""
pytest 配置文件
正确处理 src 包的导入
"""
import sys
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent.parent / "weiqi-joseki"

# 添加项目根目录到 path，使 src 成为可识别的包
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

#!/usr/bin/env python3
"""
围棋定式数据库 - 兼容性入口

⚠️ 注意：此文件已重构为模块化结构，现仅作为兼容性入口使用。
新的模块化代码位于 scripts/ 目录下：
- scripts/sgf_parser.py - SGF解析器
- scripts/joseki_extractor.py - 定式提取
- scripts/katago_downloader.py - KataGo下载
- scripts/joseki_db.py - 定式库管理
- scripts/cli.py - 命令行入口

请使用新的入口：
    python3 -m weiqi_joseki.scripts.cli ...
或直接：
    python3 cli.py ...
"""

import sys
import warnings

# 发出弃用警告
warnings.warn(
    "db.py 已弃用，请使用 scripts/cli.py 或 python3 -m weiqi_joseki.scripts.cli",
    DeprecationWarning,
    stacklevel=2
)

# 从新的模块化结构导入所有内容以保持兼容性
from scripts.cli import main
from scripts.joseki_db import JosekiDB, MatchResult, ConflictCheck
from scripts.joseki_extractor import (
    extract_joseki_from_sgf, parse_multigogm,
    process_corner_sequence, format_multigogm,
    detect_corner, convert_to_top_right,
    CoordinateSystem, COORDINATE_SYSTEMS
)

# 为了保持完全的向后兼容，导出所有原有符号
__all__ = [
    # CLI
    'main',
    # 数据库
    'JosekiDB', 'MatchResult', 'ConflictCheck',
    # 定式提取
    'extract_joseki_from_sgf', 'parse_multigogm',
    'process_corner_sequence', 'format_multigogm',
    'detect_corner', 'convert_to_top_right',
    # 坐标系统
    'CoordinateSystem', 'COORDINATE_SYSTEMS',
]

if __name__ == "__main__":
    # 委托给新的CLI入口
    main()

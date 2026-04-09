"""
围棋定式数据库模块

此模块提供围棋定式的存储、匹配、提取和管理功能。
"""

# 从子模块导出主要类和函数
from .joseki_db import JosekiDB, MatchResult, ConflictCheck
from .joseki_extractor import (
    extract_joseki_from_sgf, parse_multigogm,
    detect_corner, convert_to_top_right,
    CoordinateSystem, COORDINATE_SYSTEMS
)
from .katago_downloader import (
    download_katago_games, iter_sgf_from_tar,
    DownloadManager, ProgressManager, MemoryMonitor
)

__all__ = [
    # 数据库
    'JosekiDB', 'MatchResult', 'ConflictCheck',
    # 定式提取
    'extract_joseki_from_sgf', 'parse_multigogm',
    'detect_corner', 'convert_to_top_right',
    # 坐标系统
    'CoordinateSystem', 'COORDINATE_SYSTEMS',
    # KataGo下载
    'download_katago_games', 'iter_sgf_from_tar',
    'DownloadManager', 'ProgressManager', 'MemoryMonitor',
]

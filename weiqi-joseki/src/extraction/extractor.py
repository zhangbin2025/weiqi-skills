#!/usr/bin/env python3
"""
定式提取器（新方案）
基于连通块检测的四角定式提取
"""

from typing import List, Tuple, Dict, Optional
from .sgf_parser import parse_sgf
from .component_detector import extract_corner_moves
from ..core.coords import CoordinateSystem, convert_to_top_right


# 四角配置
CORNERS = ['tl', 'tr', 'bl', 'br']
CORNER_NAMES = {
    'tl': '左上',
    'tr': '右上', 
    'bl': '左下',
    'br': '右下'
}


def extract_main_branch(sgf_data: str, first_n: int = 80) -> List[Tuple[str, str]]:
    """
    从SGF提取主分支着法
    
    Args:
        sgf_data: SGF棋谱内容
        first_n: 只取前N手
    
    Returns:
        [(color, coord), ...] 颜色和坐标
    """
    sgf = parse_sgf(sgf_data)
    moves = []
    node = sgf['tree']
    
    while len(node['children']) > 0:
        node = node['children'][0]
        coord = node['coord'] if node['coord'] else 'tt'
        moves.append((node['color'], coord))
        if len(moves) >= first_n:
            break
    
    return moves


def extract_joseki(
    sgf_data: str,
    corner: Optional[str] = None,
    first_n: int = 80,
    distance_threshold: int = 4
) -> Dict[str, List[Tuple[str, str]]]:
    """
    从SGF提取四角定式（新方案）
    
    流程：
    1. 解析SGF，提取主分支前N手
    2. 对每个13路角区：
       - 矩阵化，找连通块
       - 仅保留离角最近的连通块
       - 过滤着法，保留连通块内的着法
       - 检测脱先（连续同色插入tt）
    3. 返回四角定式序列
    
    Args:
        sgf_data: SGF棋谱内容
        corner: 指定提取哪个角 ('tl', 'tr', 'bl', 'br')，None表示全部四角
        first_n: 只取前N手（默认80）
        distance_threshold: 连通块合并距离阈值（默认4）
    
    Returns:
        {corner_key: [(color, coord), ...], ...}
        corner_key: 'tl', 'tr', 'bl', 'br'
        坐标为原始SGF坐标，未转换视角
    """
    # 步骤1: 提取主分支着法
    moves = extract_main_branch(sgf_data, first_n)
    if not moves:
        return {}
    
    # 确定要处理的角
    corners_to_process = [corner] if corner else CORNERS
    
    # 步骤2-5: 对每个角提取定式
    result = {}
    for corner_key in corners_to_process:
        corner_moves = extract_corner_moves(moves, corner_key, distance_threshold)
        if corner_moves and len(corner_moves) >= 2:
            result[corner_key] = corner_moves
    
    return result


def extract_joseki_all_corners(
    sgf_data: str,
    first_n: int = 80,
    distance_threshold: int = 4
) -> Dict[str, List[Tuple[str, str]]]:
    """
    提取四角定式（便捷函数）
    """
    return extract_joseki(sgf_data, corner=None, first_n=first_n, 
                          distance_threshold=distance_threshold)


def convert_to_multigogm(
    corner_moves: Dict[str, List[Tuple[str, str]]],
    convert_to_tr: bool = True
) -> str:
    """
    将四角定式转换为MULTIGOGM格式SGF
    
    Args:
        corner_moves: {corner_key: [(color, coord), ...], ...}
        convert_to_tr: 是否转换为右上角视角
    
    Returns:
        MULTIGOGM格式SGF字符串
    """
    parts = [f"(;CA[utf-8]FF[4]AP[JosekiExtract]SZ[19]GM[1]KM[0]MULTIGOGM[1]"]
    
    for corner_key in ['tl', 'tr', 'bl', 'br']:
        moves = corner_moves.get(corner_key)
        if not moves:
            continue
        
        # 转换视角
        if convert_to_tr and corner_key != 'tr':
            coords = [coord for _, coord in moves]
            converted_coords = convert_to_top_right(coords, corner_key)
            moves = [(color, converted_coords[i]) for i, (color, _) in enumerate(moves)]
        
        # 生成SGF分支
        comment = CORNER_NAMES.get(corner_key, corner_key)
        if moves[0][0] == 'W':
            comment += " 白先→黑先"
        else:
            comment += " 黑先"
        
        # 检查是否有脱先
        has_pass = any(coord == 'tt' for _, coord in moves)
        if has_pass:
            comment += " 含脱先"
        
        parts.append(f"(C[{comment}]")
        for color, coord in moves:
            sgf_coord = coord if coord else ''
            parts.append(f";{color}[{sgf_coord}]")
        parts.append(")")
    
    parts.append(")")
    return "".join(parts)


def get_move_sequence(moves: List[Tuple[str, str]]) -> List[str]:
    """
    从着法列表提取坐标序列（去除颜色）
    
    Args:
        moves: [(color, coord), ...]
    
    Returns:
        [coord, ...]
    """
    return [coord for _, coord in moves]

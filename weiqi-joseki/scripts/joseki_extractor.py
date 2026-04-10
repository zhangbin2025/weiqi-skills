#!/usr/bin/env python3
"""
围棋定式提取模块
从SGF中提取四角定式，处理坐标转换
"""

import re
from typing import List, Dict, Optional, Tuple

# 导入 SGF 解析模块
try:
    from .sgf_parser import parse_sgf
except ImportError:
    from sgf_parser import parse_sgf

# 8个坐标系定义
class CoordinateSystem:
    """坐标系定义"""
    
    def __init__(self, name: str, origin_corner: str, x_dir: str, y_dir: str):
        self.name = name
        self.origin_corner = origin_corner
        self.x_dir = x_dir
        self.y_dir = y_dir
        self._to_local_cache: Dict[str, Tuple[int, int]] = {}
        self._to_sgf_cache: Dict[Tuple[int, int], str] = {}
        self._build_maps()
    
    @staticmethod
    def sgf_to_nums(sgf: str) -> Tuple[int, int]:
        return (ord(sgf[0]) - ord('a'), ord(sgf[1]) - ord('a'))
    
    @staticmethod
    def nums_to_sgf(c: int, r: int) -> str:
        return chr(ord('a') + c) + chr(ord('a') + r)
    
    def _sgf_to_local(self, sgf: str) -> Tuple[int, int]:
        col, row = self.sgf_to_nums(sgf)
        if self.origin_corner == 'tl':
            if self.x_dir == 'right' and self.y_dir == 'down':
                return (col, row)
            elif self.x_dir == 'down' and self.y_dir == 'right':
                return (row, col)
        elif self.origin_corner == 'bl':
            if self.x_dir == 'right' and self.y_dir == 'up':
                return (col, 18 - row)
            elif self.x_dir == 'up' and self.y_dir == 'right':
                return (18 - row, col)
        elif self.origin_corner == 'tr':
            if self.x_dir == 'left' and self.y_dir == 'down':
                return (18 - col, row)
            elif self.x_dir == 'down' and self.y_dir == 'left':
                return (row, 18 - col)
        elif self.origin_corner == 'br':
            if self.x_dir == 'left' and self.y_dir == 'up':
                return (18 - col, 18 - row)
            elif self.x_dir == 'up' and self.y_dir == 'left':
                return (18 - row, 18 - col)
        raise ValueError(f"Invalid coordinate system: {self.name}")
    
    def _local_to_sgf(self, x: int, y: int) -> str:
        if self.origin_corner == 'tl':
            if self.x_dir == 'right' and self.y_dir == 'down':
                return self.nums_to_sgf(x, y)
            elif self.x_dir == 'down' and self.y_dir == 'right':
                return self.nums_to_sgf(y, x)
        elif self.origin_corner == 'bl':
            if self.x_dir == 'right' and self.y_dir == 'up':
                return self.nums_to_sgf(x, 18 - y)
            elif self.x_dir == 'up' and self.y_dir == 'right':
                return self.nums_to_sgf(y, 18 - x)
        elif self.origin_corner == 'tr':
            if self.x_dir == 'left' and self.y_dir == 'down':
                return self.nums_to_sgf(18 - x, y)
            elif self.x_dir == 'down' and self.y_dir == 'left':
                return self.nums_to_sgf(18 - y, x)
        elif self.origin_corner == 'br':
            if self.x_dir == 'left' and self.y_dir == 'up':
                return self.nums_to_sgf(18 - x, 18 - y)
            elif self.x_dir == 'up' and self.y_dir == 'left':
                return self.nums_to_sgf(18 - y, 18 - x)
        raise ValueError(f"Invalid coordinate system: {self.name}")
    
    def _build_maps(self):
        for col in range(19):
            for row in range(19):
                sgf = self.nums_to_sgf(col, row)
                local = self._sgf_to_local(sgf)
                self._to_local_cache[sgf] = local
                self._to_sgf_cache[local] = sgf


# 8个坐标系定义
COORDINATE_SYSTEMS = {
    'lurd': CoordinateSystem('lurd', 'tl', 'right', 'down'),
    'ludr': CoordinateSystem('ludr', 'tl', 'down', 'right'),
    'ldru': CoordinateSystem('ldru', 'bl', 'right', 'up'),
    'ldur': CoordinateSystem('ldur', 'bl', 'up', 'right'),
    'ruld': CoordinateSystem('ruld', 'tr', 'left', 'down'),
    'rudl': CoordinateSystem('rudl', 'tr', 'down', 'left'),
    'rdlu': CoordinateSystem('rdlu', 'br', 'left', 'up'),
    'rdul': CoordinateSystem('rdul', 'br', 'up', 'left'),
}


def detect_corner(moves: List[str]) -> Optional[str]:
    """
    检测定式属于哪个角
    
    根据坐标分布判断：
    - 如果所有坐标都在 col<=8 && row<=8 区域 → 左上 (tl)
    - 如果所有坐标都在 col>=10 && row<=8 区域 → 右上 (tr)
    - 如果所有坐标都在 col<=8 && row>=10 区域 → 左下 (bl)
    - 如果所有坐标都在 col>=10 && row>=10 区域 → 右下 (br)
    
    返回: 'tl', 'tr', 'bl', 'br' 或 None（无法判断）
    """
    valid_coords = [m for m in moves if m and m != 'pass' and len(m) == 2]
    if not valid_coords:
        return None
    
    corner_counts = {'tl': 0, 'tr': 0, 'bl': 0, 'br': 0}
    
    for coord in valid_coords:
        try:
            col, row = CoordinateSystem.sgf_to_nums(coord)
            if col <= 8 and row <= 8:
                corner_counts['tl'] += 1
            elif col >= 10 and row <= 8:
                corner_counts['tr'] += 1
            elif col <= 8 and row >= 10:
                corner_counts['bl'] += 1
            elif col >= 10 and row >= 10:
                corner_counts['br'] += 1
        except:
            continue
    
    # 找出数量最多的角
    max_corner = max(corner_counts, key=corner_counts.get)
    if corner_counts[max_corner] > 0:
        return max_corner
    return None


def convert_to_top_right(moves: List[str], source_corner: str) -> List[str]:
    """
    将定式坐标转换为右上角（视觉）的坐标
    
    Args:
        moves: 坐标序列
        source_corner: 源角位 ('tl', 'tr', 'bl', 'br')
    
    返回:
        转换后的坐标序列（右上角视角）
    """
    # 如果已经是右上角，无需转换
    if source_corner == 'tr':
        return moves
    
    # 源角对应的坐标系
    source_coord_sys = {
        'tl': COORDINATE_SYSTEMS['lurd'],  # 左上
        'bl': COORDINATE_SYSTEMS['ldru'],  # 左下
        'br': COORDINATE_SYSTEMS['rdlu'],  # 右下
    }.get(source_corner)
    
    if not source_coord_sys:
        return moves
    
    # 目标坐标系：右上角的 ruld（左→下）
    target_coord_sys = COORDINATE_SYSTEMS['ruld']
    
    converted = []
    for coord in moves:
        if not coord or coord == 'pass':
            converted.append(coord)
            continue
        try:
            # 先转为局部坐标
            local_x, local_y = source_coord_sys._to_local_cache.get(coord, (0, 0))
            # 再用目标坐标系转回SGF
            new_coord = target_coord_sys._to_sgf_cache.get((local_x, local_y), coord)
            converted.append(new_coord)
        except:
            converted.append(coord)
    
    return converted


def _extract_moves_from_sgf(sgf_data: str, first_n: int = 50) -> List[Tuple[str, str]]:
    """
    从SGF提取前N手着法（内部辅助函数）
    
    返回:
        [(color, coord), ...] 颜色(B/W), 坐标(sgf格式或'tt')
    """
    moves = []
    sgf = parse_sgf(sgf_data)
    move = sgf['tree']
    while len(move['children']) > 0:
        move = move['children'][0]
        if move['coord'] is None:
            move['coord'] = 'tt'
        moves.append((move['color'], move['coord']))
        if len(moves) >= first_n:
            break
    return moves


def _classify_to_corners(moves: List[Tuple[str, str]]) -> Dict[str, List[Tuple[str, str]]]:
    """
    将着法分类到四角（支持"角部-脱先-其他-回角部"完整序列）
    
    策略：为每个角维护独立序列，当回到该角时继续追加
    
    返回:
        {corner_key: [(color, coord), ...], ...}
        corner_key: 'tr', 'tl', 'bl', 'br'
    """
    corners = {'tr': [], 'tl': [], 'bl': [], 'br': []}
    last_corner = None
    
    for color, coord in moves:
        if coord == 'tt':
            if last_corner:
                corners[last_corner].append((color, coord))
            continue
        
        col, row = CoordinateSystem.sgf_to_nums(coord)
        current_corner = None
        
        if col <= 8 and row <= 8:
            current_corner = 'tl'
        elif col >= 10 and row <= 8:
            current_corner = 'tr'
        elif col <= 8 and row >= 10:
            current_corner = 'bl'
        elif col >= 10 and row >= 10:
            current_corner = 'br'
        
        if current_corner:
            corners[current_corner].append((color, coord))
            last_corner = current_corner
    
    return corners


def extract_joseki_from_sgf_raw(sgf_data: str, first_n: int = 50) -> Dict[str, List[Tuple[str, str]]]:
    """
    从SGF提取四角定式，直接返回解析后的数据结构（消除双重解析）
    
    Args:
        sgf_data: SGF棋谱内容
        first_n: 只取前N手（默认50）
    
    返回:
        {corner_key: [(color, coord), ...], ...}
        corner_key: 'tr', 'tl', 'bl', 'br'
        坐标已转换为右上角视角，颜色已标准化为黑先
    """
    moves = _extract_moves_from_sgf(sgf_data, first_n)
    
    if not moves:
        return {}
    
    corners = _classify_to_corners(moves)
    
    result = {}
    for corner_key, seq in corners.items():
        if len(seq) < 2:
            continue
        
        processed = process_corner_sequence_raw(seq, corner_key)
        if processed:
            result[corner_key] = processed
    
    return result


def process_corner_sequence_raw(
    moves: List[Tuple[str, str]],
    corner_key: str
) -> Optional[List[Tuple[str, str]]]:
    """
    处理单角序列，直接返回处理后的着法列表（消除SGF字符串生成）
    
    Args:
        moves: [(color, sgf_coord), ...]
        corner_key: 角的键名 ('tl', 'tr', 'bl', 'br')
    
    返回:
        [(color, coord), ...] - 颜色已标准化为黑先，坐标已转换到右上角视角
    """
    if len(moves) < 2:
        return None
    
    # 1. 检测脱先（连续同色）并插入tt标记
    processed = []
    last_color = None
    
    for color, coord in moves:
        if last_color == color:
            pass_color = 'W' if color == 'B' else 'B'
            processed.append((pass_color, 'tt'))
        processed.append((color, coord))
        last_color = color
    
    # 2. 分离颜色和坐标
    colors = [c for c, _ in processed]
    coords = [coord for _, coord in processed]
    
    # 3. 将坐标转换为视觉上的右上角区域
    source_coord_sys = {
        'tl': COORDINATE_SYSTEMS['lurd'],
        'bl': COORDINATE_SYSTEMS['ldru'],
        'tr': COORDINATE_SYSTEMS['ruld'],
        'br': COORDINATE_SYSTEMS['rdlu'],
    }[corner_key]
    
    target_coord_sys = COORDINATE_SYSTEMS['ruld']
    
    tr_coords = []
    for coord in coords:
        if coord == 'tt':
            tr_coords.append('tt')
            continue
        local_x, local_y = source_coord_sys._to_local_cache.get(coord, (0, 0))
        new_coord = target_coord_sys._to_sgf_cache.get((local_x, local_y), coord)
        tr_coords.append(new_coord)
    
    # 4. 颜色标准化为黑先
    if colors[0] == 'W':
        colors = ['B' if c == 'W' else 'W' for c in colors]
    
    return list(zip(colors, tr_coords))


def extract_joseki_from_sgf(sgf_data: str, first_n: int = 50, corner: str = None) -> str:
    """
    从SGF提取四角定式，输出MULTIGOGM格式（保持向后兼容）
    
    Args:
        sgf_data: SGF棋谱内容
        first_n: 只取前N手（默认50）
        corner: 指定提取哪个角 ('tl', 'tr', 'bl', 'br')，None表示全部
    
    返回:
        MULTIGOGM格式的SGF字符串
    """
    moves = _extract_moves_from_sgf(sgf_data, first_n)
    
    if not moves:
        return "(;CA[utf-8]FF[4]AP[JosekiExtract]SZ[19]GM[1]KM[0]MULTIGOGM[1])"
    
    corners = _classify_to_corners(moves)
    
    # 处理每角
    branches = []
    corner_names = {'tl': '左上', 'tr': '右上', 'bl': '左下', 'br': '右下'}
    
    corners_to_process = [corner] if corner else corners.keys()
    
    for corner_name in corners_to_process:
        seq = corners.get(corner_name, [])
        if len(seq) < 2:
            continue
        
        branch = process_corner_sequence(seq, corner_names[corner_name], corner_name)
        if branch:
            branches.append(branch)
    
    return format_multigogm(branches)


def process_corner_sequence(moves: List[Tuple[str, str]], corner_desc: str, corner_key: str) -> Optional[Tuple[str, List[Tuple[str, str]]]]:
    """
    处理单角序列，检测脱先，转换为右上角坐标，标准化为黑先
    
    Args:
        moves: [(color, sgf_coord), ...]
        corner_desc: 角的描述（如"左上")
        corner_key: 角的键名 ('tl', 'tr', 'bl', 'br')
    
    返回:
        (comment, [(color, coord), ...]) 或 None
    """
    if len(moves) < 2:
        return None
    
    # 1. 检测脱先（连续同色）并插入tt标记
    # 规则：在同一角，如果当前颜色与上一手相同，说明对方脱先了
    processed = []
    last_color = None
    has_pass = False
    
    for color, coord in moves:
        if last_color == color:
            # 检测到脱先：插入对方脱先标记（只插入一步）
            pass_color = 'W' if color == 'B' else 'B'
            processed.append((pass_color, 'tt'))
            has_pass = True
        processed.append((color, coord))
        last_color = color
    
    # 2. 分离颜色和坐标
    colors = [c for c, _ in processed]
    coords = [coord for _, coord in processed]
    
    # 3. 将坐标转换为视觉上的右上角区域
    # 方法：先将SGF坐标转为该角的局部坐标，再用右上角的坐标系转回SGF
    source_coord_sys = {
        'tl': COORDINATE_SYSTEMS['lurd'],  # 左上用 lurd
        'bl': COORDINATE_SYSTEMS['ldru'],  # 左下用 ldru
        'tr': COORDINATE_SYSTEMS['ruld'],  # 右上用 ruld
        'br': COORDINATE_SYSTEMS['rdlu'],  # 右下用 rdlu
    }[corner_key]
    
    target_coord_sys = COORDINATE_SYSTEMS['ruld']  # 输出到右上角的 ruld
    
    tr_coords = []
    for coord in coords:
        if coord == 'tt':
            tr_coords.append('tt')
            continue
        # 先得到局部坐标 (x, y)
        local_x, local_y = source_coord_sys._to_local_cache.get(coord, (0, 0))
        # 再用目标坐标系转回SGF
        new_coord = target_coord_sys._to_sgf_cache.get((local_x, local_y), coord)
        tr_coords.append(new_coord)
    
    # 5. 颜色标准化为黑先
    if colors[0] == 'W':  # 原变化白先，需要翻转
        colors = ['B' if c == 'W' else 'W' for c in colors]
        comment = f"{corner_desc} 白先→黑先"
    else:
        comment = f"{corner_desc} 黑先"
    
    if has_pass:
        comment += " 含脱先"
    
    return (comment, list(zip(colors, tr_coords)))


def format_multigogm(branches: List[Tuple[str, List[Tuple[str, str]]]]) -> str:
    """生成MULTIGOGM格式的SGF（空坐标转为tt表示脱先）"""
    parts = [f"(;CA[utf-8]FF[4]AP[JosekiExtract]SZ[19]GM[1]KM[0]MULTIGOGM[1]"]
    
    for comment, moves in branches:
        parts.append(f"(C[{comment}]")
        for color, coord in moves:
            sgf_coord = coord if coord else 'tt'
            parts.append(f";{color}[{sgf_coord}]")
        parts.append(")")
    
    parts.append(")")
    return "".join(parts)


def parse_multigogm(sgf_data: str) -> Dict[str, Tuple[str, List[Tuple[str, str]]]]:
    """
    解析MULTIGOGM格式的SGF，提取各角定式
    
    返回:
        {corner_key: (comment, [(color, coord), ...]), ...}
        corner_key: 'tl', 'tr', 'bl', 'br'
    """
    result = {}
    corner_map = {'左上': 'tl', '右上': 'tr', '左下': 'bl', '右下': 'br'}
    
    sgf = parse_sgf(sgf_data)
    for child in sgf['tree']['children']: 
        comment = child['properties']['C']
        
        # 着法
        moves = []
        while True: 
            if child['coord'] is None:
                child['coord'] = 'tt'
            moves.append((child['color'], child['coord']))
            if len(child['children']) == 0:
                break
            child = child['children'][0]
                        
        # 从comment中判断是哪个角
        corner_key = None
        for cn, key in corner_map.items():
            if cn in comment:
                corner_key = key
                break
        
        if corner_key:
            result[corner_key] = (comment, moves)

    return result

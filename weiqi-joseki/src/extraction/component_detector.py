#!/usr/bin/env python3
"""
连通块检测器
基于距离阈值的连通块查找和筛选
"""

from typing import List, Tuple, Set, Dict
from collections import deque


class ConnectedComponent:
    """连通块"""
    def __init__(self, positions: Set[Tuple[int, int]], corner_origin: Tuple[int, int]):
        self.positions = positions
        self.corner_origin = corner_origin  # 角的原点坐标
        self._nearest_pos = None
        self._min_distance = None
    
    @property
    def size(self) -> int:
        """连通块大小（棋子数）"""
        return len(self.positions)
    
    @property
    def nearest_to_corner(self) -> Tuple[int, int]:
        """找到连通块中离角最近的点"""
        if self._nearest_pos is None:
            min_dist = float('inf')
            nearest = None
            cx, cy = self.corner_origin
            for pos in self.positions:
                px, py = pos
                # 曼哈顿距离
                dist = abs(px - cx) + abs(py - cy)
                if dist < min_dist:
                    min_dist = dist
                    nearest = pos
            self._nearest_pos = nearest
            self._min_distance = min_dist
        return self._nearest_pos
    
    @property
    def distance_to_corner(self) -> int:
        """连通块离角的距离"""
        if self._min_distance is None:
            _ = self.nearest_to_corner
        return self._min_distance


def find_connected_components(
    positions: List[Tuple[int, int]], 
    corner_origin: Tuple[int, int],
    distance_threshold: int = 4
) -> List[ConnectedComponent]:
    """
    从位置列表中查找连通块
    
    算法：
    1. 八连通找基础连通块（上下左右 + 4个对角线方向相邻视为连通）
    2. 合并相近的块（块间最小距离 <= distance_threshold）
    3. 返回所有连通块
    
    说明：八连通是指一个棋子的8个邻接位置（上、下、左、右、左上、右上、左下、右下）
          如果相邻位置有棋子，则认为这两个棋子属于同一个连通块
    
    Args:
        positions: 棋子位置列表 [(col, row), ...]
        corner_origin: 角的原点坐标 (col, row)
        distance_threshold: 块间合并距离阈值（默认4）
    
    Returns:
        连通块列表
    """
    if not positions:
        return []
    
    # 步骤1: 八连通找基础连通块
    pos_set = set(positions)
    visited = set()
    components = []
    
    # 八邻域方向
    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    
    for start_pos in positions:
        if start_pos in visited:
            continue
        
        # BFS找连通块
        component_pos = set()
        queue = deque([start_pos])
        visited.add(start_pos)
        
        while queue:
            curr = queue.popleft()
            component_pos.add(curr)
            cx, cy = curr
            
            for dx, dy in directions:
                neighbor = (cx + dx, cy + dy)
                if neighbor in pos_set and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        components.append(ConnectedComponent(component_pos, corner_origin))
    
    # 步骤2: 合并相近的块
    if len(components) > 1:
        components = _merge_close_components(components, distance_threshold)
    
    return components


def _merge_close_components(
    components: List[ConnectedComponent], 
    threshold: int
) -> List[ConnectedComponent]:
    """
    合并距离相近的连通块
    
    如果两个连通块之间的最小距离 <= threshold，则合并
    """
    if not components:
        return components
    
    n = len(components)
    parent = list(range(n))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # 计算所有连通块间的距离，合并相近的
    for i in range(n):
        for j in range(i + 1, n):
            dist = _component_distance(components[i], components[j])
            if dist <= threshold:
                union(i, j)
    
    # 按合并结果分组
    groups: Dict[int, Set[Tuple[int, int]]] = {}
    for i, comp in enumerate(components):
        root = find(i)
        if root not in groups:
            groups[root] = set()
        groups[root].update(comp.positions)
    
    # 重新创建连通块对象
    corner_origin = components[0].corner_origin
    return [ConnectedComponent(positions, corner_origin) for positions in groups.values()]


def _component_distance(c1: ConnectedComponent, c2: ConnectedComponent) -> int:
    """计算两个连通块之间的最小曼哈顿距离"""
    min_dist = float('inf')
    for p1 in c1.positions:
        for p2 in c2.positions:
            dist = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
            min_dist = min(min_dist, dist)
    return min_dist


def filter_nearest_component(components: List[ConnectedComponent]) -> Set[Tuple[int, int]]:
    """
    仅保留离角最近的连通块
    
    Args:
        components: 连通块列表
    
    Returns:
        最近连通块的位置集合
    """
    if not components:
        return set()
    
    # 找到离角最近的连通块
    nearest_comp = min(components, key=lambda c: c.distance_to_corner)
    return nearest_comp.positions


def extract_corner_moves(
    moves: List[Tuple[str, str]], 
    corner_key: str,
    distance_threshold: int = 4
) -> List[Tuple[str, str]]:
    """
    提取指定角的着法（含脱先标记）
    
    Args:
        moves: [(color, coord), ...] 完整着法序列
        corner_key: 角标识 ('tl', 'tr', 'bl', 'br')
        distance_threshold: 连通块合并距离阈值
    
    Returns:
        处理后的着法序列（含tt脱先标记）
    """
    from ..core.coords import CoordinateSystem
    
    # 定义四角的13路范围（左上角原点）和角的原点
    corner_config = {
        'tl': {'col_range': (0, 12), 'row_range': (0, 12), 'origin': (0, 0)},
        'tr': {'col_range': (6, 18), 'row_range': (0, 12), 'origin': (18, 0)},
        'bl': {'col_range': (0, 12), 'row_range': (6, 18), 'origin': (0, 18)},
        'br': {'col_range': (6, 18), 'row_range': (6, 18), 'origin': (18, 18)},
    }
    
    config = corner_config.get(corner_key)
    if not config:
        return []
    
    col_min, col_max = config['col_range']
    row_min, row_max = config['row_range']
    origin = config['origin']
    
    # 收集13路范围内的所有棋子位置
    corner_positions = []
    for color, coord in moves:
        if coord == 'tt' or not coord or len(coord) != 2:
            continue
        try:
            col, row = CoordinateSystem.sgf_to_nums(coord)
            if col_min <= col <= col_max and row_min <= row <= row_max:
                corner_positions.append((col, row))
        except:
            continue
    
    if not corner_positions:
        return []
    
    # 找连通块并筛选最近的
    components = find_connected_components(corner_positions, origin, distance_threshold)
    valid_positions = filter_nearest_component(components)
    
    if not valid_positions:
        return []
    
    # 重新遍历着法，只保留在有效连通块内的着法
    # 同时检测脱先（连续同色）
    result = []
    last_color = None
    
    for color, coord in moves:
        if coord == 'tt' or not coord or len(coord) != 2:
            continue
        
        try:
            col, row = CoordinateSystem.sgf_to_nums(coord)
            if (col, row) in valid_positions:
                # 检测脱先
                if last_color == color:
                    # 插入对方脱先标记
                    pass_color = 'W' if color == 'B' else 'B'
                    result.append((pass_color, 'tt'))
                result.append((color, coord))
                last_color = color
        except:
            continue
    
    return result

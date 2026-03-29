#!/usr/bin/env python3
"""
围棋定式数据库 - 单文件版
数据存储于 ~/.weiqi-joseki/database.json
"""

import json
import re
import os
import sys
import argparse
import time
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# OGS 抓取相关
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ==================== 配置 ====================
DEFAULT_DB_DIR = Path.home() / ".weiqi-joseki"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "database.json"

# ==================== 坐标系定义 ====================
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


@dataclass
class Move:
    """围棋一手棋"""
    color: str
    sgf_coord: str


# ==================== 数据类 ====================
@dataclass
class MatchResult:
    id: str
    name: str
    similarity: float
    matched_direction: str
    common_moves: int


@dataclass
class ConflictCheck:
    has_conflict: bool
    similar_joseki: List[dict]


# ==================== 数据库类 ====================
class JosekiDB:
    """定式数据库"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._ensure_dir()
        self.data = self._load()
        self.joseki_list = self.data.get("joseki_list", [])
    
    def _ensure_dir(self):
        """确保目录存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load(self) -> dict:
        """加载数据库"""
        if self.db_path.exists():
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"version": "1.0.0", "joseki_list": []}
    
    def _save(self):
        """保存数据库"""
        self.data["joseki_list"] = self.joseki_list
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def _now(self) -> str:
        return datetime.now().isoformat()
    
    # ========== 坐标转换 ==========
    
    @staticmethod
    def normalize_moves(moves: List[str], ignore_pass: bool = True) -> List[str]:
        """标准化为纯坐标
        Args:
            moves: 着法列表
            ignore_pass: 是否忽略pass（匹配时用True，入库时用False）
        """
        result = []
        for m in moves:
            m = m.strip()
            if m.startswith(("B[", "W[")) and len(m) >= 4:
                coord = m[2:4]
                if coord == '' and not ignore_pass:
                    result.append('')  # 保留pass标记为空字符串
                elif coord != '':
                    result.append(coord)
            elif len(m) == 2 and m[0] in 'abcdefghijklmnopqrs' and m[1] in 'abcdefghijklmnopqrs':
                result.append(m)
            elif m == '' and not ignore_pass:
                result.append('')  # 保留空字符串作为pass标记
            elif m == 'pass' and not ignore_pass:
                result.append('pass')
        return result
    
    @staticmethod
    def generate_variations(moves: List[str]) -> List[dict]:
        """生成8向变化并去重（保留pass）"""
        variations = []
        seen = set()
        
        for name, coord_sys in COORDINATE_SYSTEMS.items():
            var_moves = []
            for move in moves:
                # pass保持为pass
                if move == '' or move == 'pass':
                    var_moves.append('')
                else:
                    c, r = CoordinateSystem.sgf_to_nums(move)
                    nc, nr = {
                        'lurd': lambda c, r: (c, r),
                        'ludr': lambda c, r: (r, c),
                        'ldru': lambda c, r: (c, 18 - r),
                        'ldur': lambda c, r: (18 - r, c),
                        'ruld': lambda c, r: (18 - c, r),
                        'rudl': lambda c, r: (r, 18 - c),
                        'rdlu': lambda c, r: (18 - c, 18 - r),
                        'rdul': lambda c, r: (18 - r, 18 - c),
                    }[name](c, r)
                    var_moves.append(CoordinateSystem.nums_to_sgf(nc, nr))
            
            key = ",".join(var_moves)
            if key not in seen:
                seen.add(key)
                variations.append({"direction": name, "moves": var_moves})
        
        return variations
    
    def generate_8way_sgf(self, joseki_id: str) -> Optional[str]:
        """生成包含8向变化的SGF"""
        joseki = self.get(joseki_id)
        if not joseki:
            return None
        
        name = joseki.get('name', joseki_id)
        sgf_parts = [f"(;CA[utf-8]FF[4]AP[JosekiDB]SZ[19]GM[1]KM[0]MULTIGOGM[1]C[{name}]"]
        
        for var in joseki.get("variations", []):
            dir_desc = {
                'lurd': '左上(右→下)', 'ludr': '左上(下→右)',
                'ldru': '左下(右→上)', 'ldur': '左下(上→右)',
                'ruld': '右上(左→下)', 'rudl': '右上(下→左)',
                'rdlu': '右下(左→上)', 'rdul': '右下(上→左)'
            }.get(var['direction'], var['direction'])
            
            sgf_parts.append(f"(C[{dir_desc} {var['direction']}]" if len(joseki['variations']) > 1 else "(")
            color = 'B'
            for coord in var['moves']:
                # pass输出为 B[] 或 W[]
                sgf_parts.append(f";{color}[{coord}]")
                color = 'W' if color == 'B' else 'B'
            sgf_parts.append(")")
        
        sgf_parts.append(")")
        return "".join(sgf_parts)
    
    @staticmethod
    def lcs_similarity(seq1: List[str], seq2: List[str]) -> float:
        """最长公共子序列相似度"""
        if not seq1 or not seq2:
            return 0.0
        
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        
        return dp[m][n] / max(m, n)
    
    # ========== CRUD ==========
    
    def check_conflict(self, moves: List[str]) -> ConflictCheck:
        """检查是否与已有定式冲突（完全相同才算冲突）"""
        # 标准化输入（保留pass）
        coord_seq = self.normalize_moves(moves, ignore_pass=False)
        similar = []
        
        for joseki in self.joseki_list:
            for var in joseki.get("variations", []):
                # 直接比较完整序列（包括pass）
                if coord_seq == var["moves"]:
                    similar.append({
                        "id": joseki["id"],
                        "direction": var["direction"]
                    })
                    break
        
        return ConflictCheck(has_conflict=len(similar) > 0, similar_joseki=similar)
    
    def add(self, name: str = "", category_path: str = "", moves: List[str] = None, 
            tags: List[str] = None, description: str = "", 
            force: bool = False) -> Tuple[Optional[str], Optional[ConflictCheck]]:
        """添加定式（保留pass，name和category_path可选）"""
        moves = moves or []
        # 入库时保留pass
        coord_moves = self.normalize_moves(moves, ignore_pass=False)
        if not coord_moves:
            return None, ConflictCheck(has_conflict=False, similar_joseki=[{"error": "无效的着法序列"}])
        
        conflict = self.check_conflict(moves)
        if conflict.has_conflict and not force:
            return None, conflict
        
        joseki_id = f"joseki_{len(self.joseki_list) + 1:03d}"
        variations = self.generate_variations(coord_moves)
        
        joseki = {
            "id": joseki_id,
            "tags": tags or [],
            "description": description,
            "variations": variations,
            "created_at": self._now()
        }
        
        # name 可选，如果有值才添加
        if name:
            joseki["name"] = name
        
        # category_path 可选，如果有值才添加
        if category_path:
            joseki["category_path"] = category_path
        
        self.joseki_list.append(joseki)
        self._save()
        return joseki_id, None
    
    def remove(self, joseki_id: str) -> bool:
        """删除定式"""
        for i, j in enumerate(self.joseki_list):
            if j["id"] == joseki_id:
                self.joseki_list.pop(i)
                self._save()
                return True
        return False
    
    def clear(self) -> int:
        """清空定式库"""
        count = len(self.joseki_list)
        self.joseki_list = []
        self._save()
        return count
    
    def get(self, joseki_id: str) -> Optional[dict]:
        """获取定式详情"""
        for j in self.joseki_list:
            if j["id"] == joseki_id:
                return j
        return None
    
    # ========== OGS 抓取 ==========
    
    @staticmethod
    def _go_to_sgf(go_coord: str) -> str:
        """围棋坐标转SGF坐标"""
        if go_coord == 'pass':
            return ''
        # 构建坐标映射表（不含I）
        col_map = {}
        letters = [chr(ord('A') + i) for i in range(19)]
        letters.remove('I')
        for i, letter in enumerate(letters):
            col_map[letter] = chr(ord('a') + i)
        
        col_char = go_coord[0].upper()
        row_num = int(go_coord[1:])
        sgf_col = col_map.get(col_char, '')
        sgf_row = chr(ord('a') + (19 - row_num))
        return sgf_col + sgf_row
    
    @staticmethod
    def _fetch_ogs_position(node_id: str, delay: float = 0.3) -> Optional[dict]:
        """从OGS抓取定式位置数据（使用positions复数API）"""
        if not HAS_REQUESTS:
            raise ImportError("需要安装 requests: pip install requests")
        
        # 使用positions复数API，返回数组，取第一个元素
        url = f"https://online-go.com/oje/positions?id={node_id}&mode=0"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(delay)
            data = response.json()
            # positions返回数组，取第一个元素
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return None
        except Exception as e:
            print(f"Error fetching {node_id}: {e}")
            return None
    
    def fetch_ogs_joseki(self, start_node_id: str = "15422", max_moves: int = 15) -> Optional[List[str]]:
        """从OGS抓取一条定式主线（包含从第一手开始的完整路径）
        
        Args:
            start_node_id: OGS节点ID（默认15422=Q16）
            max_moves: 最大抓取步数
            
        Returns:
            着法序列列表（SGF坐标），失败返回None
        """
        if not HAS_REQUESTS:
            raise ImportError("需要安装 requests: pip install requests")
        
        # 先回溯到第一手，获取完整路径
        full_path = self._trace_back_to_root(start_node_id)
        if not full_path:
            return None
        
        current_id = full_path[-1]  # 从start_node继续
        visited = set(full_path)
        node_ids = full_path.copy()
        
        # 继续抓取后续着法
        for step in range(len(full_path), max_moves):
            data = self._fetch_ogs_position(current_id)
            if not data:
                break
            
            next_moves = data.get('next_moves', [])
            if not next_moves:
                break
            
            # 按 IDEAL/GOOD 优先级选择
            next_move = None
            for priority in ['IDEAL', 'GOOD']:
                for m in next_moves:
                    if m['category'] == priority:
                        next_move = m
                        break
                if next_move:
                    break
            
            if not next_move:
                break
            
            current_id = next_move['node_id']
            if current_id in visited:
                break
            
            visited.add(current_id)
            node_ids.append(current_id)
        
        # 获取每个节点的placement并转换为SGF坐标
        path_coords = []
        seen_coords = set()
        for nid in node_ids:
            data = self._fetch_ogs_position(nid)
            if data:
                placement = data.get('placement', '')
                if placement == 'root':
                    placement = 'Q16'
                if placement and placement not in seen_coords:
                    path_coords.append(placement)
                    seen_coords.add(placement)
        
        # 转换为SGF坐标
        return [self._go_to_sgf(c) for c in path_coords]
    
    def _trace_back_to_root(self, node_id: str) -> List[str]:
        """从节点回溯到第一手，返回节点ID列表
        
        从空棋盘(15081) -> ... -> node_id 的完整路径
        """
        if not HAS_REQUESTS:
            raise ImportError("需要安装 requests: pip install requests")
        
        # 获取目标节点的父节点链
        path = [node_id]
        current = node_id
        visited = {node_id}
        
        # 最多回溯20步防止无限循环
        for _ in range(20):
            data = self._fetch_ogs_position(current)
            if not data:
                break
            
            parent = data.get('parent')
            if not parent:
                break
            
            parent_id = parent.get('node_id')
            if not parent_id or parent_id in visited:
                break
            
            path.insert(0, parent_id)
            visited.add(parent_id)
            current = parent_id
        
        return path
    
    def import_from_ogs(self, count: int = 5, start_nodes: List[str] = None, min_moves: int = 4) -> List[str]:
        """从OGS随机抓取定式入库
        
        Args:
            count: 抓取定式数量
            start_nodes: 起始节点列表（默认从空棋盘开始，选择第一手随机）
            min_moves: 至少多少步的定式才抓取（默认4）
            
        Returns:
            成功入库的定式ID列表
        """
        if not HAS_REQUESTS:
            raise ImportError("需要安装 requests: pip install requests")
        
        # 默认从空棋盘开始，第一手随机选择
        empty_board_id = "15081"
        
        imported_ids = []
        attempts = 0
        max_attempts = count * 3  # 最大尝试次数，避免无限循环
        
        while len(imported_ids) < count and attempts < max_attempts:
            attempts += 1
            print(f"[{len(imported_ids)+1}/{count}] 从空棋盘抓取... (尝试 {attempts})")
            
            # 抓取定式（从空棋盘开始，第一手随机）
            moves, description, last_node_id = self.fetch_ogs_joseki_from_empty(
                empty_board_id, 
                max_moves=random.randint(10, 20)
            )
            
            if not moves or len(moves) < min_moves:
                print(f"  抓取失败或步数不足({len(moves) if moves else 0}手 < {min_moves}手)，跳过")
                continue
            
            # 检查冲突
            conflict = self.check_conflict(moves)
            if conflict.has_conflict:
                print(f"  与已有定式冲突，跳过")
                continue
            
            # 使用最后一手节点ID作为描述
            joseki_desc = last_node_id if last_node_id else ""
            
            # 入库
            joseki_id, _ = self.add(
                moves=moves,
                description=joseki_desc
            )
            
            if joseki_id:
                print(f"  ✓ 入库成功: {joseki_id} ({len(moves)}手) 第一手: {moves[0]}")
                imported_ids.append(joseki_id)
            
            # 随机延迟，避免请求过快
            time.sleep(random.uniform(0.5, 1.5))
        
        print(f"\n共成功导入 {len(imported_ids)} 条定式")
        return imported_ids
    
    def fetch_ogs_joseki_from_empty(self, empty_board_id: str = "15081", max_moves: int = 15) -> Tuple[Optional[List[str]], str, str]:
        """从空棋盘开始抓取定式，第一手随机选择
        
        Args:
            empty_board_id: 空棋盘节点ID（默认15081）
            max_moves: 最大抓取步数
            
        Returns:
            (着法序列列表, 描述, 最后一手节点ID)
        """
        if not HAS_REQUESTS:
            raise ImportError("需要安装 requests: pip install requests")
        
        # 使用系统时间作为随机种子，避免冲突
        random.seed(time.time())
        
        # 获取空棋盘的可选着法
        data = self._fetch_ogs_position(empty_board_id)
        if not data:
            return None, "", ""
        
        next_moves = data.get('next_moves', [])
        if not next_moves:
            return None, "", ""
        
        # 随机选择一个第一手（IDEAL/GOOD优先）
        ideal_moves = [m for m in next_moves if m['category'] in ['IDEAL', 'GOOD']]
        if ideal_moves:
            first_move = random.choice(ideal_moves)
        else:
            first_move = random.choice(next_moves)
        
        first_node_id = first_move['node_id']
        first_placement = first_move.get('placement', '')
        
        # 使用 _fetch_joseki_line 抓取从第二手开始的序列
        # _fetch_joseki_line 返回的是从 start_node 的下一手开始的路径
        moves, description, last_node_id = self._fetch_joseki_line(first_node_id, max_moves - 1)
        
        # 组合完整序列：第一手 + 后续着法
        # pass 保留为空字符串，后续生成SGF时会处理为 B[]/W[]
        full_moves = []
        if first_placement and first_placement != 'root':
            full_moves.append(self._go_to_sgf(first_placement))
        
        if moves:
            full_moves.extend(moves)
        
        return full_moves, description, last_node_id
    
    def _fetch_joseki_line(self, start_node_id: str, max_moves: int) -> Tuple[Optional[List[str]], str, str]:
        """从指定节点的下一步开始抓取定式（不包含起始节点本身）
        
        Returns:
            (着法序列列表, 描述, 最后一手节点ID)
        """
        path_coords = []
        description = ""
        last_node_data = None
        last_node_id = ""
        
        # 获取起始节点的信息，但不将其加入路径
        start_data = self._fetch_ogs_position(start_node_id)
        if not start_data:
            return None, "", ""
        
        # 获取下一步
        next_moves = start_data.get('next_moves', [])
        if not next_moves:
            return [], description, ""
        
        # 选择下一步
        next_move = None
        for priority in ['IDEAL', 'GOOD']:
            for m in next_moves:
                if m['category'] == priority:
                    next_move = m
                    break
            if next_move:
                break
        
        if not next_move:
            return [], description, ""
        
        current_id = next_move['node_id']
        visited = {start_node_id, current_id}
        
        # 从第二步开始抓取，直到没有后续着法或达到max_moves上限
        step = 0
        while step < max_moves:
            data = self._fetch_ogs_position(current_id)
            if not data:
                break
            
            # 保存最后一个节点的数据和ID
            last_node_data = data
            last_node_id = str(current_id)
            
            placement = data.get('placement', '')
            # 跳过 root，但保留 pass（pass会转成空字符串表示脱先）
            if placement and placement != 'root':
                path_coords.append(placement)
            
            # 获取后续着法
            next_moves = data.get('next_moves', [])
            if not next_moves:
                # 没有后续着法，定式结束
                break
            
            # 按 IDEAL/GOOD 优先级选择
            next_move = None
            for priority in ['IDEAL', 'GOOD']:
                for m in next_moves:
                    if m['category'] == priority:
                        next_move = m
                        break
                if next_move:
                    break
            
            if not next_move:
                # 没有找到合适的下一步，定式结束
                break
            
            current_id = next_move['node_id']
            if current_id in visited:
                # 循环 detected，定式结束
                break
            visited.add(current_id)
            step += 1
        
        # 转换为SGF坐标
        sgf_moves = [self._go_to_sgf(c) for c in path_coords]
        return sgf_moves, description, last_node_id
    
    def list_all(self, category: str = None) -> List[dict]:
        """列出定式"""
        result = self.joseki_list
        if category:
            result = [j for j in result if j.get("category_path", "").startswith(category)]
        
        return [{
            "id": j["id"],
            "name": j["name"],
            "category_path": j.get("category_path", ""),
            "variation_count": len(j.get("variations", [])),
            "tags": j.get("tags", [])
        } for j in result]
    
    # ========== 匹配 ==========
    
    def match(self, moves: List[str], top_k: int = 5, min_similarity: float = 0.5) -> List[MatchResult]:
        """匹配定式（忽略pass和颜色，只看坐标顺序）"""
        # 过滤掉pass，只保留有效坐标
        coord_seq = [m for m in self.normalize_moves(moves, ignore_pass=True) if m and m != 'pass']
        if not coord_seq:
            return []
        
        results = []
        seen_ids = set()
        
        for joseki in self.joseki_list:
            if joseki["id"] in seen_ids:
                continue
            
            best_sim = 0.0
            best_dir = ""
            
            for var in joseki.get("variations", []):
                # 定式变化中也过滤pass
                var_moves = [m for m in var["moves"] if m and m != 'pass']
                sim = self.lcs_similarity(coord_seq, var_moves)
                if sim > best_sim:
                    best_sim = sim
                    best_dir = var["direction"]
            
            if best_sim >= min_similarity:
                # 计算共同着法数（过滤pass后）
                first_var = joseki['variations'][0]["moves"] if joseki['variations'] else []
                first_var_filtered = [m for m in first_var if m and m != 'pass']
                common = sum(1 for i in range(min(len(coord_seq), len(first_var_filtered))) 
                            if coord_seq[i] == first_var_filtered[i])
                
                results.append(MatchResult(
                    id=joseki["id"],
                    name=joseki["name"],
                    similarity=round(best_sim, 3),
                    matched_direction=best_dir,
                    common_moves=common
                ))
                seen_ids.add(joseki["id"])
        
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]
    
    def identify_corners(self, sgf_data: str, top_k: int = 3) -> Dict[str, List[MatchResult]]:
        """从SGF识别四角定式"""
        corners = {"tl": [], "tr": [], "bl": [], "br": []}
        
        for match in re.finditer(r';[BW]\[([a-z]{2})\]', sgf_data):
            coord = match.group(1)
            col = ord(coord[0]) - ord('a')
            row = ord(coord[1]) - ord('a')
            key = "tl" if col < 9 and row < 9 else "tr" if col >= 9 and row < 9 else "bl" if col < 9 and row >= 9 else "br"
            corners[key].append(coord)
        
        return {
            corner: self.match(moves, top_k)
            for corner, moves in corners.items()
            if moves
        }
    
    def stats(self) -> dict:
        """统计信息"""
        from collections import Counter
        cat_list = []
        for j in self.joseki_list:
            path = j.get("category_path", "")
            parts = [p for p in path.split("/") if p]
            cat_list.append(parts[0] if parts else "未分类")
        
        return {
            "total": len(self.joseki_list),
            "by_category": dict(Counter(cat_list)),
            "db_path": str(self.db_path)
        }


# ==================== CLI ====================

def cmd_init(args):
    db = JosekiDB(args.db)
    db._save()
    print(f"✅ 已创建数据库: {db.db_path}")

def cmd_add(args):
    db = JosekiDB(args.db)
    
    moves = []
    if args.sgf:
        moves = [f"{m.group(1)}[{m.group(2)}]" for m in re.finditer(r';([BW])\[([a-z]{2})\]', args.sgf)]
    elif args.moves:
        moves = args.moves.split(",")
    
    if not moves:
        print("❌ 错误: 未提供有效的着法序列", file=sys.stderr)
        sys.exit(1)
    
    if not args.force:
        conflict = db.check_conflict(moves)
        if conflict.has_conflict:
            print("⚠️  检测到相似定式:")
            for s in conflict.similar_joseki:
                print(f"    {s['id']}: {s['name']} (相似度: {s['similarity']:.2f})")
            print("使用 --force 强制添加")
            sys.exit(1)
    
    joseki_id, _ = db.add(
        name=args.name, category_path=args.category,
        moves=moves, tags=args.tag or [], description=args.description or "", force=args.force
    )
    
    if joseki_id:
        print(f"✅ 已添加定式: {joseki_id}")
    else:
        print("❌ 添加失败")
        sys.exit(1)

def cmd_remove(args):
    db = JosekiDB(args.db)
    joseki = db.get(args.id)
    if not joseki:
        print(f"❌ 未找到定式: {args.id}")
        sys.exit(1)
    if db.remove(args.id):
        print(f"✅ 已删除定式: {args.id}")

def cmd_clear(args):
    db = JosekiDB(args.db)
    count = len(db.joseki_list)
    if count == 0:
        print("数据库已经是空的")
        return
    if not args.force:
        confirm = input(f"确定要删除全部 {count} 个定式吗? [y/N]: ")
        if confirm.lower() != 'y':
            print("已取消")
            return
    deleted = db.clear()
    print(f"✅ 已清空数据库，删除 {deleted} 个定式")

def cmd_list(args):
    db = JosekiDB(args.db)
    joseki_list = db.list_all(category=args.category)
    if not joseki_list:
        print("数据库为空")
        return
    if args.limit:
        joseki_list = joseki_list[:args.limit]
    
    print(f"{'ID':<12} {'名称':<30} {'分类':<25} {'变化数':<8}")
    print("-" * 80)
    for j in joseki_list:
        print(f"{j['id']:<12} {j['name']:<30} {j['category_path']:<25} {j['variation_count']:<8}")

def cmd_8way(args):
    """查看定式8向变化SGF"""
    db = JosekiDB(args.db)
    joseki = db.get(args.id)
    if not joseki:
        print(f"❌ 未找到定式: {args.id}")
        sys.exit(1)
    
    sgf = db.generate_8way_sgf(args.id)
    if sgf:
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(sgf)
            print(f"✅ 已保存到: {args.output}")
        else:
            print(sgf)
    else:
        print("❌ 生成SGF失败")

def cmd_match(args):
    db = JosekiDB(args.db)
    sgf_data = ""
    if args.sgf_file:
        with open(args.sgf_file, 'r', encoding='utf-8') as f:
            sgf_data = f.read()
    elif args.sgf:
        sgf_data = args.sgf
    else:
        sgf_data = sys.stdin.read()
    
    if not sgf_data:
        print("❌ 错误: 未提供SGF数据", file=sys.stderr)
        sys.exit(1)
    
    if args.corner:
        corners = {"tl": [], "tr": [], "bl": [], "br": []}
        for m in re.finditer(r';[BW]\[([a-z]{2})\]', sgf_data):
            coord = m.group(1)
            col = ord(coord[0]) - ord('a')
            row = ord(coord[1]) - ord('a')
            key = "tl" if col < 9 and row < 9 else "tr" if col >= 9 and row < 9 else "bl" if col < 9 and row >= 9 else "br"
            corners[key].append(coord)
        moves = corners.get(args.corner, [])
        if not moves:
            print(f"⚠️  {args.corner} 角没有着法")
            return
        results = db.match(moves, top_k=args.top_k)
        print(f"\n『{args.corner.upper()}』角匹配结果:")
        _print_match_results(results)
    else:
        results = db.identify_corners(sgf_data, top_k=args.top_k)
        for corner, matches in results.items():
            if matches:
                print(f"\n『{corner.upper()}』角:")
                _print_match_results(matches)

def _print_match_results(results):
    if not results:
        print("  无匹配")
        return
    print(f"  {'排名':<6} {'ID':<12} {'名称':<25} {'相似度':<10} {'方向':<8}")
    print("  " + "-" * 70)
    for i, r in enumerate(results, 1):
        marker = " ✓" if r.similarity > 0.9 else ""
        print(f"  {i:<6} {r.id:<12} {r.name:<25} {r.similarity:<10.2f} {r.matched_direction:<8}{marker}")

def cmd_identify(args):
    db = JosekiDB(args.db)
    sgf_data = ""
    if args.sgf_file:
        with open(args.sgf_file, 'r', encoding='utf-8') as f:
            sgf_data = f.read()
    elif args.sgf:
        sgf_data = args.sgf
    else:
        sgf_data = sys.stdin.read()
    
    if not sgf_data:
        print("❌ 错误: 未提供SGF数据", file=sys.stderr)
        sys.exit(1)
    
    results = db.identify_corners(sgf_data, top_k=args.top_k)
    
    if args.output == "json":
        output = {}
        for corner, matches in results.items():
            output[corner] = [{"id": m.id, "name": m.name, "similarity": m.similarity} for m in matches]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 70)
        print("「定式识别结果」")
        print("=" * 70)
        corner_names = {"tl": "左上", "tr": "右上", "bl": "左下", "br": "右下"}
        for corner in ["tl", "tr", "bl", "br"]:
            matches = results.get(corner, [])
            cn = corner_names.get(corner, corner)
            if matches:
                best = matches[0]
                match_str = f"{best.name} (相似度: {best.similarity:.2f})"
                if best.similarity > 0.9:
                    match_str += " ✓ 高置信度"
            else:
                match_str = "(无匹配)"
            print(f"  {cn}: {match_str}")
        print("=" * 70)

def cmd_stats(args):
    db = JosekiDB(args.db)
    stats = db.stats()
    print(f"\n『定式库统计』")
    print(f"  数据库路径: {stats['db_path']}")
    print(f"  定式总数: {stats['total']}")
    if stats['by_category']:
        print(f"\n『按分类统计』")
        for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count} 个")

def cmd_fetch_ogs(args):
    db = JosekiDB(args.db)
    start_nodes = args.start_node if args.start_node else None
    try:
        imported = db.import_from_ogs(count=args.count, start_nodes=start_nodes, min_moves=args.min_moves)
        if imported:
            print(f"\n✓ 成功导入 {len(imported)} 条定式:")
            for jid in imported:
                print(f"  - {jid}")
        else:
            print("\n⚠ 未导入任何定式")
    except ImportError as e:
        print(f"❌ 错误: {e}")
        print("请安装依赖: pip install requests")

def main():
    parser = argparse.ArgumentParser(description="围棋定式数据库管理工具")
    parser.add_argument("--db", default=None, help="数据库路径 (默认: ~/.weiqi-joseki/database.json)")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    p_init = subparsers.add_parser("init", help="初始化数据库")
    
    p_add = subparsers.add_parser("add", help="添加定式")
    p_add.add_argument("--name", help="定式名称（可选）")
    p_add.add_argument("--category", help="分类路径（可选）")
    p_add.add_argument("--sgf")
    p_add.add_argument("--moves")
    p_add.add_argument("--tag", action="append")
    p_add.add_argument("--description")
    p_add.add_argument("--force", action="store_true")
    
    p_remove = subparsers.add_parser("remove", help="删除定式")
    p_remove.add_argument("id")
    
    p_clear = subparsers.add_parser("clear", help="清空定式库")
    p_clear.add_argument("--force", action="store_true")
    
    p_list = subparsers.add_parser("list", help="列出现式")
    p_list.add_argument("--category")
    p_list.add_argument("--limit", type=int)
    
    p_8way = subparsers.add_parser("8way", help="生成定式8向变化SGF")
    p_8way.add_argument("id", help="定式ID")
    p_8way.add_argument("--output", "-o", help="输出文件路径")
    
    p_match = subparsers.add_parser("match", help="匹配定式")
    p_match.add_argument("--sgf")
    p_match.add_argument("--sgf-file")
    p_match.add_argument("--corner", choices=["tl", "tr", "bl", "br"])
    p_match.add_argument("--top-k", type=int, default=5)
    
    p_identify = subparsers.add_parser("identify", help="识别整盘棋")
    p_identify.add_argument("--sgf")
    p_identify.add_argument("--sgf-file")
    p_identify.add_argument("--top-k", type=int, default=1)
    p_identify.add_argument("--output", choices=["table", "json"], default="table")
    
    p_stats = subparsers.add_parser("stats", help="统计信息")
    
    p_fetch_ogs = subparsers.add_parser("fetch-ogs", help="从OGS抓取定式")
    p_fetch_ogs.add_argument("--count", "-n", type=int, default=5, help="抓取数量 (默认5)")
    p_fetch_ogs.add_argument("--start-node", action="append", help="指定起始节点ID (可多次指定)")
    p_fetch_ogs.add_argument("--min-moves", "-m", type=int, default=4, help="至少多少步的定式才抓取 (默认4)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        "init": cmd_init, "add": cmd_add, "remove": cmd_remove,
        "clear": cmd_clear, "list": cmd_list, "8way": cmd_8way,
        "match": cmd_match, "identify": cmd_identify, "stats": cmd_stats,
        "fetch-ogs": cmd_fetch_ogs,
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()

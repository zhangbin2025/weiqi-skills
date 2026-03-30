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
        """从单一方向生成包含8向变化的SGF"""
        joseki = self.get(joseki_id)
        if not joseki:
            return None
        
        name = joseki.get('name', joseki_id)
        sgf_parts = [f"(;CA[utf-8]FF[4]AP[JosekiDB]SZ[19]GM[1]KM[0]MULTIGOGM[1]C[{name}]"]
        
        # 获取存储的单一方向变化
        stored_moves = joseki.get("moves", [])
        if not stored_moves:
            # 兼容旧数据
            variations = joseki.get("variations", [])
            if variations:
                stored_moves = variations[0]["moves"]
            else:
                return None
        
        # 动态生成8个方向的变化
        variations = self.generate_variations(stored_moves)
        
        for var in variations:
            dir_desc = {
                'lurd': '左上(右→下)', 'ludr': '左上(下→右)',
                'ldru': '左下(右→上)', 'ldur': '左下(上→右)',
                'ruld': '右上(左→下)', 'rudl': '右上(下→左)',
                'rdlu': '右下(左→上)', 'rdul': '右下(上→左)'
            }.get(var['direction'], var['direction'])
            
            sgf_parts.append(f"(C[{dir_desc} {var['direction']}]" if len(variations) > 1 else "(")
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
        """检查是否与已有定式冲突（比较右上角两个方向）
        
        规则：输入定式转换到右上角后，生成 ruld 和 rudl 两个方向，
        与库里定式（已统一为 ruld 方向）比较。
        
        关键：使用 CoordinateSystem 进行正确的坐标转换，而不是错误的公式。
        """
        # 标准化输入（保留pass）
        coord_seq = self.normalize_moves(moves, ignore_pass=False)
        
        # 检测角位并转换到右上角（ruld 视角）
        detected_corner = self.detect_corner(coord_seq)
        if detected_corner and detected_corner != 'tr':
            coord_seq = self.convert_to_top_right(coord_seq, detected_corner)
        
        # 获取右上角两个坐标系
        ruld = COORDINATE_SYSTEMS['ruld']  # 左→下
        rudl = COORDINATE_SYSTEMS['rudl']  # 下→左
        
        # ruld_seq: 直接就是转换后的坐标
        ruld_seq = coord_seq
        
        # rudl_seq: 需要把 ruld 坐标先转局部，再用 rudl 转回SGF
        rudl_seq = []
        for m in coord_seq:
            if not m or m == 'pass':
                rudl_seq.append(m)
            else:
                # 1. ruld SGF → 局部坐标
                local = ruld._to_local_cache.get(m)
                # 2. 局部坐标 → rudl SGF
                new_sgf = rudl._to_sgf_cache.get(local, m)
                rudl_seq.append(new_sgf)
        
        similar = []
        
        for joseki in self.joseki_list:
            # 获取库存储的单一方向变化（已统一为右上角 ruld 方向）
            stored_moves = joseki.get("moves", [])
            if not stored_moves:
                # 兼容旧数据
                variations = joseki.get("variations", [])
                if variations:
                    stored_moves = variations[0]["moves"]
            
            # 检查两个方向是否任一匹配
            if stored_moves == ruld_seq or stored_moves == rudl_seq:
                similar.append({
                    "id": joseki["id"],
                    "name": joseki.get("name", joseki["id"])
                })
        
        return ConflictCheck(has_conflict=len(similar) > 0, similar_joseki=similar)
    
    @staticmethod
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
    
    @staticmethod
    def convert_to_top_right(moves: List[str], source_corner: str) -> List[str]:
        """
        将定式坐标转换为右上角（视觉）的坐标
        
        Args:
            moves: 坐标序列
            source_corner: 源角位 ('tl', 'tr', 'bl', 'br')
        
        Returns:
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

    def add(self, name: str = "", category_path: str = "", moves: List[str] = None, 
            tags: List[str] = None, description: str = "", 
            force: bool = False) -> Tuple[Optional[str], Optional[ConflictCheck]]:
        """添加定式（保留pass，name和category_path可选，自动识别角位并转为右上角存储）"""
        moves = moves or []
        # 入库时保留pass
        coord_moves = self.normalize_moves(moves, ignore_pass=False)
        if not coord_moves:
            return None, ConflictCheck(has_conflict=False, similar_joseki=[{"error": "无效的着法序列"}])
        
        # 检测角位并转换为右上角
        detected_corner = self.detect_corner(coord_moves)
        if detected_corner and detected_corner != 'tr':
            coord_moves = self.convert_to_top_right(coord_moves, detected_corner)
        
        conflict = self.check_conflict(coord_moves)
        if conflict.has_conflict and not force:
            return None, conflict
        
        joseki_id = f"joseki_{len(self.joseki_list) + 1:03d}"
        
        joseki = {
            "id": joseki_id,
            "tags": tags or [],
            "description": description,
            "moves": coord_moves,  # 存储转换后的右上角视角变化
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
    
    def list_all(self, category: str = None) -> List[dict]:
        """列出现式（精简字段）"""
        result = self.joseki_list
        if category:
            result = [j for j in result if j.get("category_path", "").startswith(category)]
        
        return [{
            "id": j["id"],
            "name": j.get("name", j["id"]),
            "category_path": j.get("category_path", ""),
            "move_count": len(j.get("moves", [])),
            "tags": j.get("tags", [])
        } for j in result]
    
    # ========== 匹配 ==========
    
    def match(self, moves: List[str], top_k: int = 5, min_similarity: float = 0.5) -> List[MatchResult]:
        """匹配定式（忽略pass和颜色，只看坐标顺序，库存储为ruld，只需比较ruld和rudl两个方向）"""
        # 过滤掉pass，只保留有效坐标
        coord_seq = [m for m in self.normalize_moves(moves, ignore_pass=True) if m and m != 'pass']
        if not coord_seq:
            return []
        
        results = []
        seen_ids = set()
        
        # 获取右上角坐标系
        ruld = COORDINATE_SYSTEMS['ruld']
        rudl = COORDINATE_SYSTEMS['rudl']
        
        for joseki in self.joseki_list:
            if joseki["id"] in seen_ids:
                continue
            
            # 获取库存储的单一方向变化（ruld视角）
            stored_moves = joseki.get("moves", [])
            if not stored_moves:
                # 兼容旧数据
                variations = joseki.get("variations", [])
                if variations:
                    stored_moves = variations[0]["moves"]
                else:
                    continue
            
            # 过滤库存储的pass
            stored_filtered = [m for m in stored_moves if m and m != 'pass']
            if not stored_filtered:
                continue
            
            best_sim = 0.0
            best_dir = ""
            
            # 方向1: 直接比较（ruld vs ruld）
            sim1 = self.lcs_similarity(coord_seq, stored_filtered)
            if sim1 > best_sim:
                best_sim = sim1
                best_dir = "ruld"
            
            # 方向2: 库存的转 rudl（下→左）再比较
            rudl_moves = []
            for m in stored_filtered:
                local = ruld._to_local_cache.get(m)
                new_sgf = rudl._to_sgf_cache.get(local, m)
                rudl_moves.append(new_sgf)
            
            sim2 = self.lcs_similarity(coord_seq, rudl_moves)
            if sim2 > best_sim:
                best_sim = sim2
                best_dir = "rudl"
            
            if best_sim >= min_similarity:
                # 计算共同着法数（与原始存储序列比对）
                common = sum(1 for i in range(min(len(coord_seq), len(stored_filtered))) 
                            if coord_seq[i] == stored_filtered[i])
                
                results.append(MatchResult(
                    id=joseki["id"],
                    name=joseki.get("name", joseki["id"]),
                    similarity=round(best_sim, 3),
                    matched_direction=best_dir,
                    common_moves=common
                ))
                seen_ids.add(joseki["id"])
        
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]
    
    def identify_corners(self, sgf_data: str, top_k: int = 3, first_n: int = 80) -> Dict[str, List[MatchResult]]:
        """
        从SGF识别四角定式
        
        流程：
        1. 先用 extract_joseki_from_sgf 提取四角定式（统一到右上角）
        2. 对每个角的定式进行匹配（只需匹配2个方向）
        """
        from db import extract_joseki_from_sgf, parse_multigogm
        
        # 提取四角定式（已经统一到右上角）
        multigogm_sgf = extract_joseki_from_sgf(sgf_data, first_n=first_n)
        corner_sequences = parse_multigogm(multigogm_sgf)
        
        results = {}
        for corner_key, (comment, moves) in corner_sequences.items():
            if len(moves) >= 2:  # 至少2手才算定式
                # 提取纯坐标序列（忽略颜色）
                coord_seq = [coord for _, coord in moves if coord and coord != 'tt']
                if coord_seq:
                    results[corner_key] = self.match_top_right(coord_seq, top_k)
        
        return results
    
    def match_top_right(self, moves: List[str], top_k: int = 5, min_similarity: float = 0.5) -> List[MatchResult]:
        """
        匹配右上角的定式（只需匹配2个方向：ruld和rudl）
        
        注意：库存储的定式默认是 ruld 方向（右上，左→下），提取的定式也统一到 ruld 方向
        所以只需比较：
        1. 直接比较（ruld vs ruld）
        2. 把库存的转 rudl 再比较
        
        Args:
            moves: 坐标序列（如 ['pd', 'qf', 'nc']），已经是 ruld 方向
            top_k: 返回前K个结果
            min_similarity: 最小相似度阈值
        """
        if not moves:
            return []
        
        # 过滤pass
        coord_seq = [m for m in moves if m and m != 'pass' and m != 'tt']
        if not coord_seq:
            return []
        
        results = []
        seen_ids = set()
        
        for joseki in self.joseki_list:
            if joseki["id"] in seen_ids:
                continue
            
            # 获取库存储的单一方向变化（默认是 ruld 方向）
            stored_moves = joseki.get("moves", [])
            if not stored_moves:
                variations = joseki.get("variations", [])
                if variations:
                    stored_moves = variations[0]["moves"]
                else:
                    continue
            
            # 过滤库存储的pass
            stored_filtered = [m for m in stored_moves if m and m != 'pass' and m != 'tt']
            if not stored_filtered:
                continue
            
            best_sim = 0.0
            best_dir = ""
            
            # 方向1: 直接比较（ruld vs ruld，都是左→下）
            sim1 = self.lcs_similarity(coord_seq, stored_filtered)
            if sim1 > best_sim:
                best_sim = sim1
                best_dir = "ruld"
            
            # 方向2: 库存的转 rudl（下→左）再比较
            ruld = COORDINATE_SYSTEMS['ruld']
            rudl = COORDINATE_SYSTEMS['rudl']
            rudl_moves = []
            for m in stored_filtered:
                # ruld SGF → 局部坐标 → rudl SGF
                local = ruld._to_local_cache.get(m)
                new_sgf = rudl._to_sgf_cache.get(local, m)
                rudl_moves.append(new_sgf)
            
            sim2 = self.lcs_similarity(coord_seq, rudl_moves)
            if sim2 > best_sim:
                best_sim = sim2
                best_dir = "rudl"
            
            if best_sim >= min_similarity:
                # 计算共同着法数（与原始存储序列比对）
                common = sum(1 for i in range(min(len(coord_seq), len(stored_filtered))) 
                            if coord_seq[i] == stored_filtered[i])
                
                results.append(MatchResult(
                    id=joseki["id"],
                    name=joseki.get("name", joseki["id"]),
                    similarity=round(best_sim, 3),
                    matched_direction=best_dir,
                    common_moves=common
                ))
                seen_ids.add(joseki["id"])
        
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]
    
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
    
    # 先标准化着法以检测角位
    coord_moves = db.normalize_moves(moves, ignore_pass=False)
    detected_corner = db.detect_corner(coord_moves)
    corner_names = {'tl': '左上', 'tr': '右上', 'bl': '左下', 'br': '右下'}
    
    if detected_corner:
        corner_desc = corner_names.get(detected_corner, detected_corner)
        if detected_corner == 'tr':
            print(f"📍 检测到角位: {corner_desc}（已是右上角视角，无需转换）")
        else:
            print(f"📍 检测到角位: {corner_desc} → 已自动转换为右上角视角")
    else:
        print(f"⚠️  无法自动识别角位，按原坐标入库")
    
    if not args.force:
        conflict = db.check_conflict(moves)
        if conflict.has_conflict:
            print("⚠️  检测到相同定式已存在:")
            for s in conflict.similar_joseki:
                print(f"    {s['id']}: {s.get('name', s['id'])}")
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
    
    print(f"{'ID':<12} {'名称':<30} {'分类':<25} {'手数':<8}")
    print("-" * 80)
    for j in joseki_list:
        print(f"{j['id']:<12} {j['name']:<30} {j['category_path']:<25} {j['move_count']:<8}")

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
        # 使用提取+匹配流程（统一到右上角）
        from db import extract_joseki_from_sgf, parse_multigogm
        multigogm = extract_joseki_from_sgf(sgf_data, first_n=50)
        parsed = parse_multigogm(multigogm)
        
        if args.corner not in parsed:
            print(f"⚠️  {args.corner} 角没有着法")
            return
        
        comment, moves = parsed[args.corner]
        coord_seq = [c for _, c in moves if c and c != 'tt']
        
        if not coord_seq:
            print(f"⚠️  {args.corner} 角没有有效着法")
            return
        
        results = db.match_top_right(coord_seq, top_k=args.top_k)
        print(f"\n『{args.corner.upper()}』角 ({comment}):")
        _print_match_results(results)
    else:
        results = db.identify_corners(sgf_data, top_k=args.top_k)
        for corner in ['tl', 'tr', 'bl', 'br']:
            matches = results.get(corner, [])
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


def cmd_extract(args):
    """从SGF提取四角定式，输出MULTIGOGM格式SGF"""
    sgf_data = ""
    if args.sgf_file:
        with open(args.sgf_file, 'r', encoding='utf-8') as f:
            sgf_data = f.read()
    else:
        sgf_data = sys.stdin.read()
    
    if not sgf_data:
        print("❌ 错误: 未提供SGF数据", file=sys.stderr)
        sys.exit(1)
    
    result = extract_joseki_from_sgf(sgf_data, first_n=args.first_n, corner=args.corner)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"✅ 已保存到: {args.output}")
    else:
        print(result)


def extract_joseki_from_sgf(sgf_data: str, first_n: int = 50, corner: str = None) -> str:
    """
    从SGF提取四角定式，输出MULTIGOGM格式
    
    Args:
        sgf_data: SGF棋谱内容
        first_n: 只取前N手（默认50）
        corner: 指定提取哪个角 ('tl', 'tr', 'bl', 'br')，None表示全部
    
    Returns:
        MULTIGOGM格式的SGF字符串
    """
    # 解析前N手
    moves = []
    for m in re.finditer(r';([BW])\[([a-z]{0,2})\]', sgf_data):
        color = m.group(1)
        coord = m.group(2)
        if coord == '':  # pass
            coord = 'tt'
        moves.append((color, coord))
        if len(moves) >= first_n:
            break
    
    if not moves:
        return "(;CA[utf-8]FF[4]AP[JosekiExtract]SZ[19]GM[1]KM[0]MULTIGOGM[1])"
    
    # 分类到四角（单次遍历）
    corners = {'tr': [], 'tl': [], 'bl': [], 'br': []}
    for color, coord in moves:
        if coord == 'tt':
            continue  # pass 不参与角部分类
        col, row = CoordinateSystem.sgf_to_nums(coord)
        # 判断属于哪个角 (0-8 或 10-18，9为边界)
        if col <= 8 and row <= 8:
            corners['tl'].append((color, coord))
        elif col >= 10 and row <= 8:
            corners['tr'].append((color, coord))
        elif col <= 8 and row >= 10:
            corners['bl'].append((color, coord))
        elif col >= 10 and row >= 10:
            corners['br'].append((color, coord))
        # col==9 或 row==9 为中央边界，不处理
    
    # 处理每角
    branches = []
    corner_names = {'tl': '左上', 'tr': '右上', 'bl': '左下', 'br': '右下'}
    
    # 如果指定了角，只处理该角
    corners_to_process = [corner] if corner else corners.keys()
    
    for corner_name in corners_to_process:
        seq = corners.get(corner_name, [])
        if len(seq) < 2:  # 至少2手才算定式
            continue
        
        branch = process_corner_sequence(seq, corner_names[corner_name], corner_name)
        if branch:
            branches.append(branch)
    
    # 生成MULTIGOGM SGF
    return format_multigogm(branches)


def process_corner_sequence(moves: List[Tuple[str, str]], corner_desc: str, corner_key: str) -> Optional[Tuple[str, List[Tuple[str, str]]]]:
    """
    处理单角序列，转换为右上角坐标，标准化为黑先
    
    Args:
        moves: [(color, sgf_coord), ...]
        corner_desc: 角的描述（如"左上")
        corner_key: 角的键名 ('tl', 'tr', 'bl', 'br')
    
    Returns:
        (comment, [(color, coord), ...]) 或 None
    """
    # 1. 检测脱先并截断
    filtered = []
    last_color = None
    has_pass = False
    
    for color, coord in moves:
        if last_color == color:  # 脱先 detected：对方没应，当前方继续
            # 脱先是对方（与当前color相反的那方）
            pass_color = 'W' if color == 'B' else 'B'
            filtered.append((pass_color, 'tt'))  # 标记脱先
            has_pass = True
            break
        filtered.append((color, coord))
        last_color = color
    
    if len(filtered) < 2:
        return None
    
    # 2. 分离颜色和坐标
    colors = [c for c, _ in filtered]
    coords = [coord for _, coord in filtered]
    
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
    
    Returns:
        {corner_key: (comment, [(color, coord), ...]), ...}
        corner_key: 'tl', 'tr', 'bl', 'br'
    """
    result = {}
    corner_map = {'左上': 'tl', '右上': 'tr', '左下': 'bl', '右下': 'br'}
    
    # 找到每个分支 (C[comment];B[xx];W[yy]...)
    for branch_match in re.finditer(r'\(C\[([^\]]+)\]([^)]*)\)', sgf_data):
        comment = branch_match.group(1)
        moves_str = branch_match.group(2)
        
        # 解析着法
        moves = []
        for m in re.finditer(r';([BW])\[([a-z]{0,2})\]', moves_str):
            color = m.group(1)
            coord = m.group(2) if m.group(2) else 'tt'
            moves.append((color, coord))
        
        # 从comment中判断是哪个角
        corner_key = None
        for cn, key in corner_map.items():
            if cn in comment:
                corner_key = key
                break
        
        if corner_key:
            result[corner_key] = (comment, moves)
    
    return result

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
    
    p_extract = subparsers.add_parser("extract", help="从SGF提取四角定式")
    p_extract.add_argument("--sgf-file", help="SGF文件路径")
    p_extract.add_argument("--first-n", type=int, default=50, help="只取前N手（默认50）")
    p_extract.add_argument("--output", "-o", help="输出文件路径")
    p_extract.add_argument("--corner", choices=["tl", "tr", "bl", "br"], help="只提取指定角 (tl=左上, tr=右上, bl=左下, br=右下)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        "init": cmd_init, "add": cmd_add, "remove": cmd_remove,
        "clear": cmd_clear, "list": cmd_list, "8way": cmd_8way,
        "match": cmd_match, "identify": cmd_identify, "stats": cmd_stats,
        "extract": cmd_extract,
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()

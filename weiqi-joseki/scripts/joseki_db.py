#!/usr/bin/env python3
"""
围棋定式数据库核心模块
管理定式库的CRUD、匹配、8向生成、导出
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime
from collections import Counter

# 导入依赖模块
try:
    from .joseki_extractor import (
        CoordinateSystem, COORDINATE_SYSTEMS,
        extract_joseki_from_sgf, parse_multigogm,
        detect_corner, convert_to_top_right
    )
except ImportError:
    from joseki_extractor import (
        CoordinateSystem, COORDINATE_SYSTEMS,
        extract_joseki_from_sgf, parse_multigogm,
        detect_corner, convert_to_top_right
    )


# 配置
DEFAULT_DB_DIR = Path.home() / ".weiqi-joseki"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "database.json"


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
            if m.startswith(("B[", "W[")) and len(m) >= 3:
                coord = m[2:4] if len(m) >= 4 else ''
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
    def generate_variations(moves: List[str], directions: Optional[List[str]] = None) -> List[dict]:
        """
        生成8向变化并去重（保留pass）
        
        Args:
            moves: 着法序列
            directions: 方向列表，None表示全部8个方向
        """
        variations = []
        seen = set()
        
        target_directions = directions if directions else COORDINATE_SYSTEMS.keys()
        
        for name in target_directions:
            if name not in COORDINATE_SYSTEMS:
                continue
            
            coord_sys = COORDINATE_SYSTEMS[name]
            var_moves = []
            for move in moves:
                # pass保持为pass
                if move == '' or move == 'pass':
                    var_moves.append('')
                else:
                    c, r = CoordinateSystem.sgf_to_nums(move)
                    nc, nr = {
                        'ruld': lambda c, r: (c, r),
                        'rudl': lambda c, r: (18 - r, 18 - c),
                        'rdlu': lambda c, r: (c, 18 - r),
                        'rdul': lambda c, r: (18 - r, c),
                        'lurd': lambda c, r: (18 - c, r),
                        'ludr': lambda c, r: (r, 18 - c),
                        'ldru': lambda c, r: (18 - c, 18 - r),
                        'ldur': lambda c, r: (r, c),
                    }[name](c, r)
                    var_moves.append(CoordinateSystem.nums_to_sgf(nc, nr))
            
            key = ",".join(var_moves)
            if key not in seen:
                seen.add(key)
                variations.append({"direction": name, "moves": var_moves})
        
        return variations
    
    def generate_8way_sgf(self, joseki_id: str, directions: Optional[List[str]] = None) -> Optional[str]:
        """
        从单一方向生成包含8向变化的SGF
        
        Args:
            joseki_id: 定式ID
            directions: 指定方向列表，如 ['ruld', 'rudl']，None表示全部8个方向
        
        返回:
            MULTIGOGM格式的SGF字符串
        """
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
        variations = self.generate_variations(stored_moves, directions)
        
        for var in variations:
            dir_desc = {
                'lurd': '左上(右→下)', 'ludr': '左上(下→右)',
                'ldru': '左下(右→上)', 'ldur': '左下(上→右)',
                'ruld': '右上(左→下)', 'rudl': '右上(下→左)',
                'rdlu': '右下(左→上)', 'rdul': '右下(上→左)'
            }.get(var['direction'], var['direction'])
            
            # 总是包含方向描述，便于识别
            sgf_parts.append(f"(C[{dir_desc} {var['direction']}]")
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
        """
        # 标准化输入（保留pass）
        coord_seq = self.normalize_moves(moves, ignore_pass=False)
        
        # 检测角位并转换到右上角（ruld 视角）
        detected_corner = detect_corner(coord_seq)
        if detected_corner and detected_corner != 'tr':
            coord_seq = convert_to_top_right(coord_seq, detected_corner)
        
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
        detected_corner = detect_corner(coord_moves)
        if detected_corner and detected_corner != 'tr':
            coord_moves = convert_to_top_right(coord_moves, detected_corner)
        
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
    
    def match_top_right(self, moves: List[str], top_k: int = 5, min_similarity: float = 0.5) -> List[MatchResult]:
        """
        匹配右上角的定式（只需匹配2个方向：ruld和rudl）
        
        注意：库存储的定式默认是 ruld 方向（右上，左→下），提取的定式也统一到 ruld 方向
        所以只需比较：
        1. 直接比较（ruld vs ruld）
        2. 把库存的转 rudl 再比较
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
    
    def identify_corners(self, sgf_data: str, top_k: int = 3, first_n: int = 80) -> Dict[str, List[MatchResult]]:
        """
        从SGF识别四角定式
        
        流程：
        1. 先用 extract_joseki_from_sgf 提取四角定式（统一到右上角）
        2. 对每个角的定式进行匹配（只需匹配2个方向）
        """
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
    
    # ========== 导入功能 ==========
    
    def import_from_sgfs(self,
                        sgf_sources: List,
                        min_count: int = 10,
                        min_moves: int = 4,
                        min_rate: float = 0.0,
                        first_n: int = 50,
                        dry_run: bool = False,
                        progress_callback: Optional[Callable] = None) -> Tuple[int, int, List[str]]:
        """
        从SGF文件列表批量导入定式
        
        Args:
            sgf_sources: SGF文件路径列表，或包含SGF内容的字符串列表（自动识别）
            min_count: 最少出现次数才入库
            min_moves: 定式至少多少手
            min_rate: 最小出现概率%
            first_n: 每谱提取前N手内的定式
            dry_run: 试运行，只统计不真入库
            progress_callback: 进度回调函数(current, total)
        
        返回:
            (added_count, skipped_count, candidates_list)
        """
        count_map = {}  # {joseki_str: count}
        total_sources = len(sgf_sources)
        
        # 1. 提取所有定式
        for i, source in enumerate(sgf_sources):
            if progress_callback:
                progress_callback(i + 1, total_sources)
            
            try:
                if isinstance(source, Path):
                    sgf_data = source.read_text(encoding='utf-8', errors='ignore')
                else:
                    sgf_data = source
                
                # 使用 joseki_extractor 提取四角定式
                multigogm = extract_joseki_from_sgf(sgf_data, first_n=first_n)
                parsed = parse_multigogm(multigogm)
                
                for corner_key, (comment, moves) in parsed.items():
                    coords = [coord for color, coord in moves if coord]
                    if len(coords) >= 2:
                        joseki_str = " ".join(coords)
                        count_map[joseki_str] = count_map.get(joseki_str, 0) + 1
            except Exception:
                continue
        
        # 2. 前缀累加
        sorted_joseki = sorted(count_map.keys())
        for i in range(len(sorted_joseki)):
            current = sorted_joseki[i]
            for j in range(i+1, len(sorted_joseki)):
                later = sorted_joseki[j]
                if later.startswith(current + " "):
                    count_map[current] += count_map[later]
                else:
                    break
        
        # 3. 筛选候选
        candidates = []
        for prefix, count in count_map.items():
            if len(prefix.split()) < min_moves:
                continue
            if count < min_count:
                continue
            if min_rate > 0 and (count/total_sources)*100 < min_rate:
                continue
            candidates.append((prefix, count))
        
        # 按频率排序
        candidates.sort(key=lambda x: -x[1])
        
        if dry_run:
            return 0, 0, [f"{prefix} ({count}次)" for prefix, count in candidates]
        
        # 4. 入库
        added, skipped = 0, 0
        
        for prefix, count in candidates:
            coords = prefix.split()
            
            # 构造SGF格式
            sgf_moves = []
            color = 'B'
            for c in coords:
                sgf_moves.append(f"{color}[{c}]")
                color = 'W' if color == 'B' else 'B'
            
            # 检查冲突
            conflict = self.check_conflict(sgf_moves)
            if conflict.has_conflict:
                skipped += 1
                continue
            
            # 自动命名和分类
            name = f"自动提取-{len(coords)}手"
            category = "/自动"
            
            joseki_id, _ = self.add(
                name=name,
                category_path=category,
                moves=sgf_moves,
                force=False
            )
            
            if joseki_id:
                added += 1
            else:
                skipped += 1
        
        return added, skipped, [f"{prefix} ({count}次)" for prefix, count in candidates]
    
    def import_from_katago_cache(self,
                                  cache_dir: Path,
                                  min_count: int = 10,
                                  min_moves: int = 4,
                                  min_rate: float = 0.5,
                                  first_n: int = 50,
                                  dry_run: bool = False) -> Tuple[int, int]:
        """
        从KataGo缓存目录导入定式
        
        Args:
            cache_dir: KataGo棋谱缓存目录
            其他参数同上
        
        返回:
            (added_count, skipped_count)
        """
        from .katago_downloader import iter_sgf_from_tar
        
        # 收集所有tar文件
        tar_files = list(cache_dir.glob("*rating.tar.bz2"))
        
        # 收集所有SGF内容
        sgf_list = []
        for tar_path in tar_files:
            for sgf_data in iter_sgf_from_tar(tar_path):
                sgf_list.append(sgf_data)
        
        # 使用 import_from_sgfs 导入
        added, skipped, _ = self.import_from_sgfs(
            sgf_sources=sgf_list,
            min_count=min_count,
            min_moves=min_moves,
            min_rate=min_rate,
            first_n=first_n,
            dry_run=dry_run
        )
        
        return added, skipped
    
    # ========== 导出功能 ==========
    
    def export_to_sgf(self, 
                      output_path: Optional[str] = None,
                      category: Optional[str] = None,
                      min_moves: Optional[int] = None,
                      max_moves: Optional[int] = None,
                      tags: Optional[List[str]] = None,
                      ids: Optional[List[str]] = None) -> str:
        """
        将定式库导出到一个SGF文件，支持多种过滤条件
        
        Args:
            output_path: 输出文件路径，None则返回SGF字符串
            category: 按分类路径过滤（前缀匹配）
            min_moves: 最少手数
            max_moves: 最多手数
            tags: 包含任一指定标签
            ids: 指定定式ID列表
        
        返回:
            MULTIGOGM格式的SGF字符串
        """
        # 过滤定式
        filtered = self.joseki_list
        
        if category:
            filtered = [j for j in filtered 
                       if j.get('category_path', '').startswith(category)]
        
        if min_moves is not None:
            filtered = [j for j in filtered 
                       if len(j.get('moves', [])) >= min_moves]
        
        if max_moves is not None:
            filtered = [j for j in filtered 
                       if len(j.get('moves', [])) <= max_moves]
        
        if tags:
            filtered = [j for j in filtered 
                       if any(t in j.get('tags', []) for t in tags)]
        
        if ids:
            filtered = [j for j in filtered if j['id'] in ids]
        
        # 生成SGF
        parts = [f"(;CA[utf-8]FF[4]AP[JosekiDB]SZ[19]GM[1]KM[0]MULTIGOGM[1]C[导出 {len(filtered)}个定式]"]
        
        for joseki in filtered:
            name = joseki.get('name', joseki['id'])
            category_path = joseki.get('category_path', '')
            moves = joseki.get('moves', [])
            
            comment_parts = [name]
            if category_path:
                comment_parts.append(f"分类:{category_path}")
            comment = " | ".join(comment_parts)
            
            parts.append(f"(C[{comment}]")
            color = 'B'
            for coord in moves:
                if coord == '' or coord == 'pass':
                    parts.append(f";{color}[]")
                else:
                    parts.append(f";{color}[{coord}]")
                color = 'W' if color == 'B' else 'B'
            parts.append(")")
        
        parts.append(")")
        sgf = "".join(parts)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(sgf)
        
        return sgf
    
    # ========== 统计 ==========
    
    def stats(self) -> dict:
        """统计信息"""
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

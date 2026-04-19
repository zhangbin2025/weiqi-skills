#!/usr/bin/env python3
"""
围棋定式数据库核心模块
管理定式库的CRUD、匹配、8向生成、导出
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable, Set
from dataclasses import dataclass
from datetime import datetime
from collections import Counter

# 导入依赖模块
try:
    from .joseki_extractor import (
        CoordinateSystem, COORDINATE_SYSTEMS,
        extract_joseki_from_sgf, extract_joseki_from_sgf_raw, extract_joseki_from_sgf_multi,
        parse_multigogm, detect_corner, convert_to_top_right
    )
    from .katago_downloader import iter_sgf_from_tar
except ImportError:
    from joseki_extractor import (
        CoordinateSystem, COORDINATE_SYSTEMS,
        extract_joseki_from_sgf, extract_joseki_from_sgf_raw, extract_joseki_from_sgf_multi,
        parse_multigogm, detect_corner, convert_to_top_right
    )
    from katago_downloader import iter_sgf_from_tar


# 配置
DEFAULT_DB_DIR = Path.home() / ".weiqi-joseki"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "database.json"


@dataclass
class PrefixMatchResult:
    """前缀匹配结果 - 最长前缀优先，同前缀选总手数最短的"""
    id: str
    name: str
    prefix_len: int      # 匹配的前缀长度（最长优先）
    total_moves: int     # 定式总手数（同前缀时越短越优先）
    matched_direction: str  # "ruld" 或 "rudl"


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
        # 构建 ID -> 定式 的快速索引 (O(1) 查找)
        self._id_index = {j["id"]: j for j in self.joseki_list}
        # 构建快速索引以加速匹配
        self._build_fast_index()
    
    def _ensure_dir(self):
        """确保目录存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load(self) -> dict:
        """加载数据库（兼容旧格式列表和新格式字典）"""
        if self.db_path.exists():
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容旧格式: 直接是列表
                if isinstance(data, list):
                    return {"version": "1.0.0", "joseki_list": data}
                # 新格式: 字典
                return data
        return {"version": "1.0.0", "joseki_list": []}
    
    def _save(self):
        """保存数据库"""
        self.data["joseki_list"] = self.joseki_list
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def _now(self) -> str:
        return datetime.now().isoformat()
    
    def _build_trie(self):
        """
        构建前缀树索引（Trie）- 支持ruld和rudl两个方向
        用于前缀匹配：最长前缀优先，同前缀选总手数最短
        """
        self._trie = {}      # ruld方向前缀树
        self._trie_rudl = {} # rudl方向前缀树
        
        for j in self.joseki_list:
            moves = j.get("moves", [])
            if not moves:
                continue
            
            # ruld方向入树
            self._add_to_trie(self._trie, moves, j["id"])
            
            # rudl方向入树
            rudl_moves = self._convert_to_rudl(moves)
            self._add_to_trie(self._trie_rudl, rudl_moves, j["id"])
    
    def _add_to_trie(self, trie: dict, moves: List[str], joseki_id: str):
        """将定式着法序列加入前缀树"""
        node = trie
        for move in moves:
            if move not in node:
                node[move] = {'next': {}, 'ids': []}
            node[move]['ids'].append(joseki_id)
            node = node[move]['next']
    
    def _match_trie(self, trie: dict, moves: List[str], direction: str) -> List[Tuple[int, str, int]]:
        """
        在Trie中走前缀，返回所有命中的定式
        
        Returns:
            [(prefix_len, joseki_id, total_moves), ...]
        """
        node = trie
        matched_ids = {}  # id -> 最深匹配长度
        
        for i, move in enumerate(moves):
            if move not in node:
                break
            
            prefix_len = i + 1
            for joseki_id in node[move]['ids']:
                matched_ids[joseki_id] = prefix_len
            
            node = node[move]['next']
        
        # 获取完整定式手数
        results = []
        for joseki_id, match_len in matched_ids.items():
            joseki = self.get(joseki_id)
            if joseki:
                total_moves = len(joseki.get("moves", []))
                results.append((match_len, joseki_id, total_moves, direction))
        
        return results
    
    def _build_fast_index(self):
        """
        构建快速索引（向后兼容）
        现在使用Trie树实现
        """
        self._build_trie()
    
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
            # 首先检查tt（脱先标记）- 优先于坐标检查
            if m == 'tt' and not ignore_pass:
                result.append('tt')
            elif m.startswith(("B[", "W[")) and len(m) >= 3:
                coord = m[2:4] if len(m) >= 4 else ''
                if coord == '' and not ignore_pass:
                    result.append('')  # 保留pass标记为空字符串
                elif coord == 'tt' and not ignore_pass:
                    result.append('tt')  # 保留脱先标记
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
        # 更新ID索引
        self._id_index[joseki_id] = joseki
        
        # 更新Trie索引（ruld和rudl两个方向）
        if coord_moves:
            # ruld方向入树
            self._add_to_trie(self._trie, coord_moves, joseki_id)
            
            # rudl方向入树
            rudl_moves = self._convert_to_rudl(coord_moves)
            self._add_to_trie(self._trie_rudl, rudl_moves, joseki_id)
        
        self._save()
        return joseki_id, None
    
    def remove(self, joseki_id: str) -> bool:
        """删除定式"""
        if joseki_id in self._id_index:
            joseki = self._id_index[joseki_id]
            self.joseki_list.remove(joseki)
            # 删除ID索引
            del self._id_index[joseki_id]
            # 重建Trie索引
            self._build_fast_index()
            self._save()
            return True
        return False
    
    def clear(self) -> int:
        """清空定式库"""
        count = len(self.joseki_list)
        self.joseki_list = []
        self._id_index = {}
        self._trie = {}
        self._trie_rudl = {}
        self._save()
        return count
    
    def get(self, joseki_id: str) -> Optional[dict]:
        """获取定式详情 (O(1) 字典查找)"""
        return self._id_index.get(joseki_id)
    
    def list_all(self, category: str = None, sort_by: str = None, sort_order: str = "desc") -> List[dict]:
        """列出现式（精简字段）
        
        Args:
            category: 按分类路径过滤（前缀匹配）
            sort_by: 排序字段，可选：id, name, category_path, move_count, frequency, probability, created_at
            sort_order: 排序方向，asc（升序）或 desc（降序），默认 desc
        """
        result = self.joseki_list
        if category:
            result = [j for j in result if j.get("category_path", "").startswith(category)]
        
        # 构建结果列表
        items = [{
            "id": j["id"],
            "name": j.get("name", ""),
            "category_path": j.get("category_path", ""),
            "move_count": len(j.get("moves", [])),
            "moves": j.get("moves", []),
            "frequency": j.get("frequency"),
            "probability": j.get("probability"),
            "tags": j.get("tags", []),
            "created_at": j.get("created_at", "")
        } for j in result]
        
        # 排序处理
        if sort_by:
            # 有效的排序字段
            valid_fields = ["id", "name", "category_path", "move_count", "frequency", "probability", "created_at"]
            if sort_by not in valid_fields:
                sort_by = "id"  # 默认按ID排序
            
            # 反转标志：desc = True（降序），asc = False（升序）
            reverse = sort_order.lower() != "asc"
            
            def sort_key(item):
                value = item.get(sort_by)
                # 处理 None 值
                if value is None:
                    # 数值字段用 0，字符串用空字符串
                    if sort_by in ["move_count", "frequency", "probability"]:
                        return 0
                    return ""
                return value
            
            items.sort(key=sort_key, reverse=reverse)
        
        return items
    
    # ========== 匹配 ==========
    
    def match(self, moves: List[str], top_k: int = 5, corner: str = None) -> List[PrefixMatchResult]:
        """
        匹配定式 - 前缀匹配算法
        
        Args:
            moves: 着法序列
            top_k: 返回前K个结果
            corner: 指定角位 ('tl', 'tr', 'bl', 'br')，None则自动检测
        
        规则：
        1. 保留脱先标记tt
        2. 统一转为右上角匹配
        3. 找最长公共前缀的定式
        4. 同前缀长度，选总手数最短的
        """
        # 标准化（保留tt，只过滤空字符串）
        coord_seq = [m for m in self.normalize_moves(moves, ignore_pass=False) if m]
        if not coord_seq:
            return []
        
        # 检测角位并转换到右上角
        if corner:
            # 指定了角位，直接转换
            if corner != 'tr':
                coord_seq = convert_to_top_right(coord_seq, corner)
        else:
            # 自动检测角位
            detected_corner = detect_corner(coord_seq)
            if detected_corner and detected_corner != 'tr':
                coord_seq = convert_to_top_right(coord_seq, detected_corner)
        
        # 在两个方向找最长前缀
        results_ruld = self._match_trie(self._trie, coord_seq, "ruld")
        results_rudl = self._match_trie(self._trie_rudl, coord_seq, "rudl")
        
        # 合并结果：取每个定式的最大前缀长度
        best_matches = {}
        
        for prefix_len, joseki_id, total_moves, direction in results_ruld:
            if joseki_id not in best_matches or best_matches[joseki_id][0] < prefix_len:
                best_matches[joseki_id] = (prefix_len, total_moves, direction)
        
        for prefix_len, joseki_id, total_moves, direction in results_rudl:
            if joseki_id not in best_matches or best_matches[joseki_id][0] < prefix_len:
                best_matches[joseki_id] = (prefix_len, total_moves, direction)
        
        # 排序：前缀长度降序 → 总手数升序
        sorted_results = sorted(
            best_matches.items(),
            key=lambda x: (-x[1][0], x[1][1])  # -prefix_len, total_moves
        )
        
        # 构建返回结果
        results = []
        for joseki_id, (prefix_len, total_moves, direction) in sorted_results[:top_k]:
            joseki = self.get(joseki_id)
            if joseki:
                results.append(PrefixMatchResult(
                    id=joseki_id,
                    name=joseki.get("name", joseki_id),
                    prefix_len=prefix_len,
                    total_moves=total_moves,
                    matched_direction=direction
                ))
        
        return results
    
    def match_top_right(self, moves: List[str], top_k: int = 5) -> List[PrefixMatchResult]:
        """
        匹配右上角的定式 - 序列已经是右上角视角，不再转换
        """
        return self.match(moves, top_k=top_k, corner='tr')
    
    def identify_corners(self, sgf_data: str, top_k: int = 3, first_n: int = 80, corner_sizes: List[int] = None) -> Dict[str, List[PrefixMatchResult]]:
        """
        从SGF识别四角定式（支持多路匹配）
        
        Args:
            sgf_data: SGF棋谱内容
            top_k: 每个角返回前K个匹配结果
            first_n: 只分析前N手
            corner_sizes: 角大小列表，如 [9, 11, 13]，默认 [9, 11, 13]
        """
        if corner_sizes is None:
            corner_sizes = [9, 11, 13]
        
        # 收集每个尺寸在每个角的匹配结果
        all_results: Dict[str, List[PrefixMatchResult]] = {}
        
        for size in corner_sizes:
            multigogm_sgf = extract_joseki_from_sgf(sgf_data, first_n=first_n, corner_size=size)
            corner_sequences = parse_multigogm(multigogm_sgf)
            
            for corner_key, (comment, moves) in corner_sequences.items():
                if len(moves) >= 2:  # 至少2手才算定式
                    coord_seq = [coord for _, coord in moves if coord]
                    if coord_seq:
                        matches = self.match_top_right(coord_seq, top_k)
                        if corner_key not in all_results:
                            all_results[corner_key] = []
                        # 标记匹配来源的尺寸
                        for m in matches:
                            object.__setattr__(m, 'matched_from_size', size)
                        all_results[corner_key].extend(matches)
        
        # 对每个角的结果去重并排序（按 prefix_len 降序，相同 prefix_len 按 total_moves 升序）
        results = {}
        for corner_key, matches in all_results.items():
            # 按 id 和 direction 去重，保留 prefix_len 最大的
            seen = {}
            for m in matches:
                key = (m.id, m.matched_direction)
                if key not in seen or seen[key].prefix_len < m.prefix_len:
                    seen[key] = m
            
            # 排序并取 top_k
            unique_matches = list(seen.values())
            unique_matches.sort(key=lambda x: (-x.prefix_len, x.total_moves))
            results[corner_key] = unique_matches[:top_k]
        
        return results
    
    # ========== 导入功能 ==========
    
    def _extract_joseki_from_sources(
        self,
        sgf_sources: List,
        first_n: int,
        corner_size: int,
        verbose: bool,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[Dict[str, int], int, int, int, int]:
        """步骤1: 从所有源提取定式（优化版：消除双重解析）
        返回: (count_map, total_sources, total_sgf_files, total_extracted, unique_count)
        total_sources: 源文件/压缩包数量
        total_sgf_files: 实际的SGF文件数量（解压后）
        """
        count_map = {}
        total_sources = len(sgf_sources)
        total_sgf_files = 0
        total_joseki_extracted = 0
        unique_joseki_count = 0

        if verbose:
            print(f"📊 开始从 {total_sources} 个源提取定式...")

        for i, source in enumerate(sgf_sources):
            try:
                sgf_data = []
                if isinstance(source, Path):
                    if source.suffix == '.sgf':
                        sgf_data.append(source.read_text(encoding='utf-8', errors='ignore'))
                    else:
                        sgf_data = list(iter_sgf_from_tar(source))
                else:
                    sgf_data.append(source)
                
                total_sgf_files += len(sgf_data)
                
                # 优化：使用 extract_joseki_from_sgf_raw 直接获取解析后的数据
                # 避免先生成 SGF 字符串再解析回来的双重开销
                for sgf_item in sgf_data:
                    corner_dict = extract_joseki_from_sgf_raw(sgf_item, first_n=first_n, corner_size=corner_size)
                    
                    # corner_dict: {corner_key: [(color, coord), ...], ...}
                    for corner_key, moves in corner_dict.items():
                        coords = [coord for color, coord in moves if coord]
                        if len(coords) >= 2:
                            joseki_str = " ".join(coords)
                            if joseki_str not in count_map:
                                unique_joseki_count += 1
                            count_map[joseki_str] = count_map.get(joseki_str, 0) + 1
                            total_joseki_extracted += 1
                
                if progress_callback:
                    progress_callback(i + 1, total_sources, source, len(sgf_data))
                if verbose and ((i + 1) % 100 == 0 or i + 1 == total_sources):
                    print(f"\r  提取进度: {i + 1}/{total_sources} | SGF文件: {total_sgf_files} | 累计定式: {total_joseki_extracted} | 唯一序列: {unique_joseki_count}", end='', flush=True)
            except Exception:
                continue

        if verbose:
            print(f"\n✅ 提取完成: {total_sgf_files} 个SGF文件，{total_joseki_extracted} 个定式，{unique_joseki_count} 个唯一序列")

        return count_map, total_sources, total_sgf_files, total_joseki_extracted, unique_joseki_count

    def _accumulate_prefix_counts(
        self,
        count_map: Dict[str, int],
        verbose: bool
    ) -> Dict[str, int]:
        """步骤2: 前缀累加统计
        返回: 更新后的 count_map
        """
        if verbose:
            print(f"🔄 开始前缀累加计算...")
        
        sorted_joseki = sorted(count_map.keys())
        for i in range(len(sorted_joseki)):
            current = sorted_joseki[i]
            for j in range(i+1, len(sorted_joseki)):
                later = sorted_joseki[j]
                if later.startswith(current + " "):
                    count_map[current] += count_map[later]
                else:
                    break
            if verbose and (i + 1) % 1000 == 0 or i + 1 == len(sorted_joseki):
                print(f"\r  前缀累加进度: {i + 1}/{len(sorted_joseki)}", end='', flush=True)

        if verbose:
            print(f"\n✅ 前缀累加完成")
        
        return count_map

    def _filter_candidates(
        self,
        count_map: Dict[str, int],
        total_sgf_count: int,
        min_count: int,
        min_moves: int,
        min_rate: float,
        verbose: bool
    ) -> List[Tuple[str, int]]:
        """步骤3: 筛选候选定式
        返回: [(prefix, count), ...] 按频率降序排序
        """
        if verbose:
            print(f"🔍 筛选候选定式（次数≥{min_count}，手数≥{min_moves}，概率≥{min_rate}%）...")
        
        candidates = []
        for prefix, count in count_map.items():
            if len(prefix.split()) < min_moves:
                continue
            if count < min_count:
                continue
            if min_rate > 0 and (count/total_sgf_count)*100 < min_rate:
                continue
            candidates.append((prefix, count))

        candidates.sort(key=lambda x: -x[1])

        if verbose:
            print(f"✅ 筛选完成: {len(candidates)} 个候选定式")

        return candidates

    def _build_conflict_hash_sets(
        self,
        existing_joseki: List[dict]
    ) -> Tuple[Set[str], Set[str]]:
        """步骤4: 预计算已有定式的 hash sets
        返回: (ruld_hashes, rudl_hashes)
        """
        ruld_hashes = set()
        rudl_hashes = set()
        
        for joseki in existing_joseki:
            moves = joseki.get("moves", [])
            if moves:
                ruld_hashes.add(",".join(moves))
                rudl_moves = self._convert_to_rudl(moves)
                rudl_hashes.add(",".join(rudl_moves))
        
        return ruld_hashes, rudl_hashes

    def _convert_to_rudl(self, moves: List[str]) -> List[str]:
        """辅助: 将 ruld 方向的 moves 转换为 rudl 方向"""
        ruld = COORDINATE_SYSTEMS['ruld']
        rudl = COORDINATE_SYSTEMS['rudl']
        
        rudl_moves = []
        for m in moves:
            if not m or m == 'pass':
                rudl_moves.append(m)
            else:
                local = ruld._to_local_cache.get(m)
                new_sgf = rudl._to_sgf_cache.get(local, m)
                rudl_moves.append(new_sgf)
        
        return rudl_moves

    def _batch_add_joseki(
        self,
        candidates: List[Tuple[str, int]],
        total_sgf_count: int,
        category: str,
        name_prefix: str,
        ruld_hashes: Set[str],
        rudl_hashes: Set[str],
        verbose: bool
    ) -> Tuple[int, int, List[str]]:
        """步骤5: 批量添加定式（性能优化版）
        
        优化点：
        1. 使用 hash set 进行 O(1) 冲突检测
        2. 批量收集新定式，只调用一次 _save()
        
        返回: (added, skipped, candidate_strings)
        """
        added = 0
        skipped = 0
        new_joseki_list = []
        
        if verbose:
            print(f"💾 开始入库（分类: {category}）...")

        for idx, (prefix, count) in enumerate(candidates):
            coords = prefix.split()
            move_count = len(coords)
            probability = count / total_sgf_count if total_sgf_count > 0 else 0

            # 使用 hash set 进行 O(1) 冲突检测
            # 检查逻辑：
            # 1. 新定式的 ruld 是否在已有定式的 ruld_hashes 中（同方向重复）
            # 2. 新定式的 ruld 是否在已有定式的 rudl_hashes 中（反方向重复）
            prefix_ruld = ",".join(coords)
            
            if prefix_ruld in ruld_hashes or prefix_ruld in rudl_hashes:
                skipped += 1
                if verbose:
                    print(f"\r  [{idx+1}/{len(candidates)}] 跳过（冲突）| 手数:{move_count} | 频率:{count} | 概率:{probability:.2%}", end='', flush=True)
                continue

            if category == "/katago":
                # KataGo导入模式
                joseki_data = {
                    "id": f"joseki_{len(self.joseki_list) + len(new_joseki_list) + 1:03d}",
                    "category_path": "/katago",
                    "moves": coords,
                    "frequency": count,
                    "probability": round(probability, 4),
                    "move_count": move_count,
                    "created_at": self._now()
                }
                new_joseki_list.append(joseki_data)
                # 更新 hash sets 防止本次批量添加中的重复
                ruld_hashes.add(prefix_ruld)
                rudl_hashes.add(",".join(self._convert_to_rudl(coords)))
                added += 1
                if verbose:
                    print(f"\r  [{idx+1}/{len(candidates)}] 已入库 | 手数:{move_count} | 频率:{count} | 概率:{probability:.2%}", end='', flush=True)
            else:
                # 普通模式 - 使用 add 方法
                sgf_moves = []
                color = 'B'
                for c in coords:
                    sgf_moves.append(f"{color}[{c}]")
                    color = 'W' if color == 'B' else 'B'
                
                # 检查冲突（使用 check_conflict）
                conflict = self.check_conflict(sgf_moves)
                if conflict.has_conflict:
                    skipped += 1
                    if verbose:
                        print(f"\r  [{idx+1}/{len(candidates)}] 跳过（冲突）| 手数:{move_count} | 频率:{count} | 概率:{probability:.2%}", end='', flush=True)
                    continue
                
                name = f"{name_prefix}-{move_count}手"
                joseki_id, _ = self.add(
                    name=name,
                    category_path=category,
                    moves=sgf_moves,
                    force=False
                )
                
                if joseki_id:
                    added += 1
                    # 更新 hash sets
                    ruld_hashes.add(prefix_ruld)
                    rudl_hashes.add(",".join(self._convert_to_rudl(coords)))
                    if verbose:
                        print(f"\r  [{idx+1}/{len(candidates)}] 已入库 | 手数:{move_count} | 频率:{count} | 概率:{probability:.2%}", end='', flush=True)
                else:
                    skipped += 1
                    if verbose:
                        print(f"\r  [{idx+1}/{len(candidates)}] 跳过 | 手数:{move_count} | 频率:{count} | 概率:{probability:.2%}", end='', flush=True)

        # 批量保存（只调用一次）
        if new_joseki_list:
            self.joseki_list.extend(new_joseki_list)
            # 批量更新ID索引
            for joseki in new_joseki_list:
                self._id_index[joseki["id"]] = joseki
            self._save()

        if verbose:
            print(f"\n✅ 入库完成: 新增 {added} 个定式，跳过 {skipped} 个")

        return added, skipped, [f"{prefix} ({count}次)" for prefix, count in candidates]

    def set_cms_config(self, width: int = 200000, depth: int = 5):
        """设置 CMS 配置
        
        推荐配置：
        - 低内存: width=200000, depth=5, 内存~3.8MB, 误差~0.5%
        - 高精度: width=4194304, depth=4, 内存~64MB, 误差~0.024%
        
        需在调用 import_from_sgfs 前设置。
        """
        self._cms_width = width
        self._cms_depth = depth

    def import_from_sgfs(self,
                        sgf_sources: List,
                        min_count: int = 10,
                        min_moves: int = 4,
                        min_rate: float = 0.0,
                        first_n: int = 80,
                        corner_sizes: List[int] = None,
                        dry_run: bool = False,
                        progress_callback: Optional[Callable] = None,
                        category: str = "/自动",
                        name_prefix: str = "自动提取",
                        verbose: bool = True,
                        top_k: int = 200000) -> Tuple[int, int, List]:
        """从SGF列表导入定式 - CMS版本（支持大规模数据）
        
        使用 Count-Min Sketch 估算前缀频率，找到 top-k 前缀定式。
        
        Args:
            sgf_sources: SGF文件路径列表或内容列表
            min_count: 最少出现次数
            min_moves: 最少手数（前缀从此手数开始提取）
            min_rate: 最小出现概率百分比
            first_n: 每谱提取前N手
            corner_sizes: 角部大小列表 [9, 11, 13]
            dry_run: 试运行模式
            progress_callback: 进度回调函数
            category: 分类路径
            name_prefix: 名称前缀
            verbose: 详细输出
            top_k: 返回前k个高频定式，默认20万
        
        Returns:
            (added_count, skipped_count, candidates_list)
        """
        import heapq
        import tempfile
        import gzip
        
        try:
            from .cms import CountMinSketch
        except ImportError:
            from cms import CountMinSketch
        
        sizes = corner_sizes if corner_sizes else [9, 11, 13]  # 提取9/11/13路（考虑脱先场景）
        total_sources = len(sgf_sources)
        total_files = 0
        total_joseki = 0
        total_unique_sequences = 0  # 所有棋谱去重后的着法串总数（用于概率计算）
        
        # Phase 1: 初始化 CMS 和临时文件
        cms_width = getattr(self, '_cms_width', 200000)
        cms_depth = getattr(self, '_cms_depth', 5)
        cms = CountMinSketch(width=cms_width, depth=cms_depth)
        temp_file = tempfile.NamedTemporaryFile(mode='wb', suffix='.gz', delete=False)
        temp_path = Path(temp_file.name)
        
        if verbose:
            print(f"📊 CMS定式提取（路数: {sizes}, top_k: {top_k}）")
            print(f"   CMS配置: width={cms_width}, depth={cms_depth}")
            print(f"   CMS内存: ~{cms_width * cms_depth * 4 / 1024 / 1024:.1f}MB")
        
        # Phase 2: 遍历棋谱，提取定式串并写入临时文件，同时更新CMS（所有前缀）
        # 优化1: 每谱24个着法串（4角×3路×2方向）按字符串去重后再继续
        joseki_count = 0  # 定式串数量（不是前缀数量）
        prefix_count = 0   # 前缀数量（仅统计）
        with gzip.open(temp_path, 'wt', encoding='utf-8') as f_out:
            for i, source in enumerate(sgf_sources):
                try:
                    # 获取SGF内容
                    sgf_gen = []
                    if isinstance(source, Path):
                        if source.suffix == '.sgf':
                            sgf_gen = [(source.read_text(encoding='utf-8', errors='ignore'), source)]
                        else:
                            sgf_gen = iter_sgf_from_tar(source)
                    else:
                        sgf_gen = [(source, None)]
                    
                    for sgf_data in sgf_gen:
                        if isinstance(sgf_data, tuple):
                            sgf_content, _ = sgf_data
                        else:
                            sgf_content = sgf_data
                        
                        total_files += 1
                        
                        # 每谱的着法串去重集合
                        seen_sequences = set()
                        
                        # 优化7: 多路提取只解析一次SGF
                        # 提取四角定式（9/11/13路）
                        multi_result = extract_joseki_from_sgf_multi(
                            sgf_content, first_n=first_n, corner_sizes=sizes
                        )
                        
                        for size, corner_dict in multi_result.items():
                            for corner_key, moves in corner_dict.items():
                                coords = [c for _, c in moves if c]
                                if len(coords) < min_moves:
                                    continue
                                
                                # 生成 ruld 和 rudl 两个方向
                                ruld = " ".join(coords)
                                rudl = " ".join(self._convert_to_rudl(coords))
                                
                                # 优化1: 按字符串去重
                                for direction, seq in [('ruld', ruld), ('rudl', rudl)]:
                                    if seq in seen_sequences:
                                        continue
                                    seen_sequences.add(seq)
                                    
                                    # 写入临时文件：只写定式串
                                    f_out.write(f"{direction}|{seq}\n")
                                    joseki_count += 1
                                    
                                    # 展开所有前缀并更新CMS
                                    seq_parts = seq.split()
                                    for end in range(min_moves, len(seq_parts) + 1):
                                        prefix = " ".join(seq_parts[:end])
                                        cms.update(prefix)
                                        prefix_count += 1
                                
                                total_joseki += 2  # ruld + rudl
                        
                        # 累加每谱去重后的着法串数量（用于概率计算）
                        total_unique_sequences += len(seen_sequences)
                        
                        if progress_callback:
                            progress_callback(i + 1, total_sources, source, 0)
                        
                        if verbose and total_files % 1000 == 0:
                            print(f"\r  已处理: {total_files} 谱, {joseki_count} 定式串, {prefix_count} 前缀", end='', flush=True)
                            
                except Exception as e:
                    if verbose:
                        print(f"\n  跳过: {e}")
                    continue
        
        if verbose:
            print(f"\n✅ Phase 1: {total_files} 棋谱, {total_joseki} 定式, {joseki_count} 定式串（去重后）写入临时文件")
            print(f"   去重后着法串总数: {total_unique_sequences}")
        
        # Phase 3: 遍历临时文件，读取定式串，展开前缀，用 CMS 估算频率，选出 top-k
        # 新算法: 逆向遍历(从长到短) + 单链检测(子串代表父串)
        if verbose:
            print(f"🔄 Phase 2: CMS估算前缀并选取 top-{top_k}（逆向遍历+单链检测）...")
        
        class HeapItem:
            __slots__ = ['count', 'prefix', 'direction', 'prefix_hash']
            
            def __init__(self, count, prefix, direction, prefix_hash):
                self.count = count
                self.prefix = prefix
                self.direction = direction
                self.prefix_hash = prefix_hash
            
            def __lt__(self, other):
                return self.count < other.count
        
        heap = []  # 小顶堆，按 count 排序
        seen_hashes = {}  # prefix_hash -> True (只存hash，不存引用)
        
        def _get_hash(prefix_parts):
            """获取hash（前缀元组，不含方向）"""
            return tuple(prefix_parts)
        
        def _get_child_hash(prefix_parts, seq_parts):
            """获取子串hash（当前前缀+下一手，用于单链检测）"""
            if len(prefix_parts) >= len(seq_parts):
                return None
            child_parts = prefix_parts + [seq_parts[len(prefix_parts)]]
            return tuple(child_parts)
        
        processed = 0
        prefix_processed = 0
        skipped_single_chain = 0  # 单链跳过计数
        
        # 单链检测阈值：次数相差在5%以内认为是单链
        SINGLE_CHAIN_THRESHOLD = 0.05
        
        with gzip.open(temp_path, 'rt', encoding='utf-8') as f_in:
            for line in f_in:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                
                direction, joseki_str = line.split('|', 1)
                seq_parts = joseki_str.split()
                
                if len(seq_parts) < min_moves:
                    continue
                
                # 逆向遍历：从最长前缀到 min_moves
                last_count = float('inf')  # 上一个前缀的出现次数
                
                for end in range(len(seq_parts), min_moves - 1, -1):
                    prefix_parts = seq_parts[:end]
                    prefix = " ".join(prefix_parts)
                    
                    # CMS 估算频率
                    est_count = cms.estimate(prefix)
                    
                    # 过滤低频前缀
                    if est_count < min_count:
                        last_count = est_count
                        continue
                    
                    # 获取当前hash
                    prefix_hash = _get_hash(prefix_parts)
                    
                    # 单链检测：count和last_count相差不大，且下一前缀（子串）已处理
                    if last_count != float('inf'):
                        count_diff_ratio = abs(est_count - last_count) / max(est_count, last_count, 1)
                        if count_diff_ratio < SINGLE_CHAIN_THRESHOLD:
                            # 检查子串是否已处理（在堆中或被跳过）
                            child_hash = _get_child_hash(prefix_parts, seq_parts)
                            if child_hash and child_hash in seen_hashes:
                                # 单链：被子串代表，跳过
                                skipped_single_chain += 1
                                seen_hashes[prefix_hash] = False  # 标记为已处理（被代表）
                                last_count = est_count
                                continue
                    
                    last_count = est_count
                    
                    # 检查当前前缀是否已在堆中（或被跳过）
                    if prefix_hash in seen_hashes:
                        # 父串已经被处理过，不需要继续
                        break
                    
                    # 尝试入堆
                    if len(heap) < top_k:
                        item = HeapItem(est_count, prefix, direction, prefix_hash)
                        heapq.heappush(heap, item)
                        seen_hashes[prefix_hash] = True
                        prefix_processed += 1
                    elif est_count > heap[0].count:
                        # 比堆顶大，替换
                        old_item = heapq.heapreplace(heap, HeapItem(est_count, prefix, direction, prefix_hash))
                        del seen_hashes[old_item.prefix_hash]
                        seen_hashes[prefix_hash] = True
                        prefix_processed += 1
                    # 否则：进不了堆，但继续处理更短的前缀（因为更短的前缀次数可能更高）
                
                processed += 1
                if verbose and processed % 10000 == 0:
                    print(f"\r  处理: {processed}定式/{prefix_processed}前缀, 堆大小: {len(heap)}, 单链跳过: {skipped_single_chain}", end='', flush=True)
        
        if verbose:
            print(f"\n  堆中候选: {len(heap)} 个")
            print(f"  单链跳过: {skipped_single_chain} 个")
        
        # Phase 4: 收集候选，统一转ruld方向去重
        candidates = []
        seen_ruld = {}  # ruld_key -> count，用于去重保留最大count
        
        for item in heap:
            parts = item.prefix.split()
            
            # 统一转换为ruld方向
            if item.direction == 'ruld':
                ruld_parts = parts
            else:
                ruld_parts = self._convert_to_rudl(parts)  # rudl -> ruld
            
            ruld_key = tuple(ruld_parts)
            if ruld_key in seen_ruld:
                # 已存在，保留count更大的
                if item.count > seen_ruld[ruld_key]:
                    seen_ruld[ruld_key] = item.count
                continue
            
            seen_ruld[ruld_key] = item.count
            candidates.append({
                'moves': list(ruld_parts),
                'count': item.count,
                'move_str': " ".join(ruld_parts),
            })
        
        # 如果有重复的只保留一个，需要重新构建candidates
        final_candidates = []
        for moves_tuple, count in seen_ruld.items():
            move_list = list(moves_tuple)
            final_candidates.append({
                'moves': move_list,
                'count': count,
                'move_str': " ".join(move_list),
            })
        candidates = final_candidates
        
        # 按字符串顺序排序（方便查看）
        candidates.sort(key=lambda x: x['move_str'])
        
        # Phase 5: 入库
        if verbose:
            print(f"🔄 Phase 3: 入库（按字符串顺序）...")
            print(f"  候选定式: {len(candidates)} 个")
        
        # 清理临时文件
        temp_path.unlink()
        
        if dry_run:
            return len(candidates), 0, candidates
        
        added = 0
        skipped = 0
        # 优化5: 概率计算 = 前缀出现次数 / 所有棋谱去重后的着法串总数
        probability_denominator = total_unique_sequences if total_unique_sequences > 0 else 1
        
        # 构建已有定式的moves集合用于查重（入库时 moves 是纯坐标列表）
        existing_moves = set()
        for j in self.joseki_list:
            moves = j.get("moves", [])
            if moves:
                existing_moves.add(tuple(moves))
        
        for cand in candidates:
            coords = cand['moves']
            count = cand['count']
            
            # 检查是否已存在相同的着法序列
            if tuple(coords) in existing_moves:
                skipped += 1
                continue
            
            # 统一存储频率和概率（katago和导入模式）
            data = {
                "id": f"joseki_{len(self.joseki_list) + added + 1:03d}",
                "category_path": category,
                "moves": coords,
                "frequency": count,
                "probability": round(count / probability_denominator, 6),
                "move_count": len(coords),
                "created_at": self._now()
            }
            
            # 如果是手动导入，额外添加name字段
            if category != "/katago":
                data["name"] = f"{name_prefix}-{len(coords)}手"
            
            self.joseki_list.append(data)
            existing_moves.add(tuple(coords))  # 添加到查重集合
            added += 1
            
            if verbose and added % 1000 == 0:
                print(f"\r  入库: {added}", end='', flush=True)
        
        if added > 0:
            self._save()
        
        if verbose:
            if skipped > 0:
                print(f"\n✅ 完成: 新增 {added} 定式，跳过 {skipped} 个重复")
            else:
                print(f"\n✅ 完成: 新增 {added} 定式")
        
        return added, skipped, candidates
    
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
        
        # 收集所有tar文件
        tar_files = list(cache_dir.glob("*rating.tar.bz2"))
        
        # 使用 import_from_sgfs 导入
        added, skipped, _ = self.import_from_sgfs(
            sgf_sources=tar_files,
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
    
    # ========== 发现功能 ==========
    
    def discover(
        self,
        sgf_sources: List,
        first_n: int = 80,
        min_moves: int = 4,
        corner_sizes: List[int] = None,
        top_k: int = 1,
        limit: int = 50,
        verbose: bool = True
    ) -> Dict:
        """
        发现值得研究的定式（每个角最长匹配优先）
        
        排序规则（优先级从高到低）：
        1. 罕见定式（匹配前缀短）
        2. 低频定式（库中出现次数少）
        3. 复杂定式（手数多的优先）
        
        Args:
            sgf_sources: SGF文件路径列表，或包含SGF内容的字符串列表
            first_n: 分析前N手的定式（默认50）
            min_moves: 定式最少手数（默认4）
            corner_sizes: 角大小列表，如 [9, 11, 13]（默认[9, 11, 13]）
            limit: 最多返回多少个定式（默认50）
            verbose: 详细输出开关
        
        Returns:
            包含统计信息和定式列表的字典：
            - stats: 统计信息
              - total_files: 扫描的文件数
              - total_joseki: 提取的定式总数
              - unique_joseki: 去重后的定式数
              - rare_joseki: 罕见定式数量
              - common_joseki: 常见定式数量
            - joseki_list: 按研究价值排序的定式列表
        """
        from pathlib import Path
        
        # 步骤1: 收集所有定式
        joseki_records = []  # [(moves_tuple, sgf_info, corner)]
        total_files = 0
        
        if verbose:
            print(f"🔍 开始扫描 {len(sgf_sources)} 个源...")
        
        for source in sgf_sources:
            try:
                sgf_contents = []
                source_path = None
                
                if isinstance(source, Path):
                    if source.is_dir():
                        # 目录：递归收集所有SGF文件
                        for sgf_file in source.rglob("*.sgf"):
                            sgf_contents.append((sgf_file.read_text(encoding='utf-8', errors='ignore'), sgf_file))
                    elif source.suffix == '.sgf':
                        sgf_contents.append((source.read_text(encoding='utf-8', errors='ignore'), source))
                        source_path = source
                elif isinstance(source, str) and source.strip().startswith('('):
                    # SGF内容字符串
                    sgf_contents.append((source, None))
                elif isinstance(source, str):
                    # 可能是文件路径字符串
                    p = Path(source)
                    if p.exists():
                        if p.is_dir():
                            for sgf_file in p.rglob("*.sgf"):
                                sgf_contents.append((sgf_file.read_text(encoding='utf-8', errors='ignore'), sgf_file))
                        else:
                            sgf_contents.append((p.read_text(encoding='utf-8', errors='ignore'), p))
                
                for sgf_data, sgf_path in sgf_contents:
                    total_files += 1
                    # 解析SGF元信息
                    sgf_info = self._parse_sgf_info(sgf_data, sgf_path)
                    
                    # 提取四角定式（多路）
                    sizes = corner_sizes if corner_sizes else [9, 11, 13]
                    for size in sizes:
                        corner_dict = extract_joseki_from_sgf_raw(sgf_data, first_n=first_n, corner_size=size)
                        
                        for corner, moves in corner_dict.items():
                            # 提取坐标序列（保留脱先标记tt，过滤空字符串）
                            coords = [coord for color, coord in moves if coord]
                            # 注意：这里不再过滤有效手数，让后续逻辑处理
                            joseki_records.append((tuple(coords), sgf_info, corner, size))
                
            except Exception as e:
                if verbose:
                    print(f"  ⚠️ 处理源 {source} 时出错: {e}")
                continue
        
        total_joseki = len(joseki_records)
        if verbose:
            print(f"✅ 扫描完成: {total_files} 个文件，提取 {total_joseki} 个定式")
        
        # 步骤2: 按 (文件, 角, 路数) 收集所有 moves_tuple
        # 修改：保留路数信息，用于后续多路浅匹配过滤
        corner_sequences = {}  # {(file_path, corner, size): [(moves_tuple, sgf_info)]}
        source_counter = 0
        
        for moves_tuple, sgf_info, corner, size in joseki_records:
            file_path = sgf_info.get('file', 'unknown')
            if file_path == 'inline':
                source_counter += 1
                file_path = f"inline_{source_counter}"
            
            key = (file_path, corner, size)
            if key not in corner_sequences:
                corner_sequences[key] = []
            corner_sequences[key].append((moves_tuple, sgf_info))
        
        # 步骤3: 对每个 (file_path, corner) 进行多路浅匹配过滤
        # 新逻辑：
        # 1. 收集该角在所有路数下的匹配结果
        # 2. 如果所有路数的匹配前缀都很短（< 3），且9路着法串很短（< min_moves），则过滤掉
        # 3. 否则按 identify_corners 逻辑处理
        if verbose:
            print("🔎 正在比对定式库...")
        
        corner_best_matches = {}  # {(file_path, corner): [(joseki_id, direction, prefix_len, moves_tuple, match_result, sgf_info, size)]}
        
        # 先按 (file_path, corner) 分组
        file_corner_groups = {}  # {(file_path, corner): [(size, seq_list)]}
        for (file_path, corner, size), seq_list in corner_sequences.items():
            key = (file_path, corner)
            if key not in file_corner_groups:
                file_corner_groups[key] = []
            file_corner_groups[key].append((size, seq_list))
        
        # 对每个 (file_path, corner) 进行处理
        for (file_path, corner), size_seq_list in file_corner_groups.items():
            corner_matches = []  # 这个角的所有匹配
            all_prefix_lens = []  # 所有路数的最大匹配前缀
            nine_way_moves = None  # 9路的着法串
            
            # 对这个角的所有路数序列进行匹配
            for size, seq_list in size_seq_list:
                for moves_tuple, sgf_info in seq_list:
                    coords = list(moves_tuple)
                    
                    # 记录9路的着法串
                    if size == 9:
                        nine_way_moves = coords
                    
                    matches = self.match_top_right(coords, top_k=top_k)
                    
                    # 记录该路数的最大匹配前缀
                    max_prefix_len = matches[0].prefix_len if matches else 0
                    all_prefix_lens.append(max_prefix_len)
                    
                    if matches:
                        for match in matches:
                            corner_matches.append((match.id, match.matched_direction, match.prefix_len, moves_tuple, match, sgf_info, size))
                    else:
                        # 空库中没有匹配的定式，添加一个空匹配（prefix_len=0）
                        from scripts.joseki_db import PrefixMatchResult
                        empty_match = PrefixMatchResult(
                            id='',
                            name='',
                            prefix_len=0,
                            total_moves=len(coords),
                            matched_direction='ruld'
                        )
                        corner_matches.append(('', 'ruld', 0, moves_tuple, empty_match, sgf_info, size))
            
            # 【多路浅匹配过滤】
            # 如果所有路数的匹配前缀都很短（< 3），且9路着法串很短（< min_moves），则过滤掉
            if all_prefix_lens and max(all_prefix_lens) < 3:
                nine_way_effective_moves = len([c for c in (nine_way_moves or []) if c != 'tt'])
                if nine_way_effective_moves < min_moves:
                    if verbose:
                        print(f"  🗑️  过滤假定式: {file_path} {corner} (最大前缀:{max(all_prefix_lens)}, 9路手数:{nine_way_effective_moves})")
                    continue  # 跳过这个假定式
            
            # 先按 (joseki_id, direction) 去重，保留 prefix_len 最大的
            seen = {}
            for joseki_id, direction, prefix_len, moves_tuple, match_result, sgf_info, size in corner_matches:
                key = (joseki_id, direction)
                if key not in seen or seen[key][2] < prefix_len:
                    seen[key] = (joseki_id, direction, prefix_len, moves_tuple, match_result, sgf_info, size)
            
            # 再按 prefix_len 降序排序，取前top_k个
            unique_matches = list(seen.values())
            unique_matches.sort(key=lambda x: -x[2])  # 按 prefix_len 降序
            corner_best_matches[(file_path, corner)] = unique_matches[:top_k]  # 每个角最多top_k个
        
        # 步骤4: 按 (moves_tuple, joseki_id, direction) 聚合来源（同一序列+定式可能来自多个文件/角）
        unique_joseki = {}  # {(moves_tuple, joseki_id, direction): {'match_result': ..., 'sources': [], 'count': 0}}
        
        for (file_path, corner), matches in corner_best_matches.items():
            for joseki_id, direction, prefix_len, moves_tuple, match_result, sgf_info, size in matches:
                key = (moves_tuple, joseki_id, direction)
                if key not in unique_joseki:
                    unique_joseki[key] = {
                        'match_result': match_result,
                        'sources': [],
                        'count': 0,
                        'moves': list(moves_tuple)
                    }
                
                unique_joseki[key]['count'] += 1
                source_copy = sgf_info.copy()
                source_copy['corner'] = corner
                source_copy['size'] = size  # 保留路数信息
                unique_joseki[key]['sources'].append(source_copy)
        
        unique_count = len(unique_joseki)
        if verbose:
            print(f"📊 去重后: {unique_count} 个唯一定式")
        
        # 步骤6: 组装结果
        results = []
        
        for (moves_tuple, joseki_id, direction), data in unique_joseki.items():
            coords = data['moves']
            match_result = data['match_result']
            
            matched_prefix_len = match_result.prefix_len
            matched_prefix_moves = coords[:matched_prefix_len]
            
            # 获取匹配的定式序列
            matched_joseki = self.get(joseki_id)
            frequency = matched_joseki.get('frequency', 1) if matched_joseki else 1
            library_probability = matched_joseki.get('probability', 0.0) if matched_joseki else 0.0
            
            # 判断是否罕见：前缀长度是否达到 min_moves
            is_rare = matched_prefix_len < min_moves
            
            # 计算发现概率（出现次数 / 总文件数）
            discovery_probability = data['count'] / total_files if total_files > 0 else 0.0
            
            results.append({
                'joseki_id': joseki_id,
                'is_rare': is_rare,
                'moves': coords,
                'move_count': len(coords),
                'matched_prefix': matched_prefix_moves,
                'matched_prefix_len': matched_prefix_len,
                'matched_direction': direction,  # 添加 direction 字段
                'frequency': frequency,
                'probability': round(library_probability, 4),
                'discovery_probability': round(discovery_probability, 4),
                'sources': data['sources']
            })
        
        if verbose:
            print(f"\n✅ 比对完成")
        
        # 步骤4: 按最长匹配优先排序
        # 排序规则：
        # 1. 匹配前缀长的优先（最长匹配优先，与 identify 一致）
        # 2. 相同前缀长度：匹配定式频率高的优先
        results.sort(key=lambda x: (
            -x['matched_prefix_len'],   # 匹配前缀长的优先（负号表示降序）
            -x['frequency'],            # 频率高的优先
            -x['move_count']            # 手数多的优先
        ))
        
        # 步骤5: 添加排名并限制数量
        final_results = []
        for rank, item in enumerate(results[:limit], 1):
            item['rank'] = rank
            final_results.append(item)
        
        # 统计信息（基于限制后的结果）
        rare_count = sum(1 for r in final_results if r['is_rare'])
        common_count = sum(1 for r in final_results if not r['is_rare'])
        
        if verbose:
            print(f"\n📈 发现结果:")
            print(f"   罕见定式(前缀<{min_moves}): {rare_count} 个")
            print(f"   常见定式(前缀>={min_moves}): {common_count} 个")
            print(f"   总计: {len(final_results)} 个")
        
        # 构建返回结果（包含stats）
        result = {
            "stats": {
                "total_files": total_files,
                "total_joseki": total_joseki,
                "unique_joseki": unique_count,
                "rare_joseki": rare_count,
                "common_joseki": common_count
            },
            "joseki_list": final_results
        }
        
        return result
    
    def _parse_sgf_info(self, sgf_data: str, sgf_path: Optional[Path] = None) -> Dict:
        """解析SGF元信息，使用sgf_parser"""
        info = {
            'file': str(sgf_path) if sgf_path else 'inline',
            'black_player': '',
            'white_player': '',
            'event': '',
            'date': '',
            'result': ''
        }
        
        try:
            # 使用sgf_parser解析 - 尝试多种导入方式
            try:
                from .sgf_parser import parse_sgf
            except ImportError:
                from sgf_parser import parse_sgf
            
            parsed = parse_sgf(sgf_data)
            game_info = parsed.get('game_info', {})
            tree = parsed.get('tree', {})
            props = tree.get('properties', {})
            
            # 提取元信息 - 字段名映射 (sgf_parser使用短字段名)
            info['black_player'] = game_info.get('black', '')
            info['white_player'] = game_info.get('white', '')
            info['date'] = game_info.get('date', '')
            info['result'] = game_info.get('result', '')
            
            # 赛事信息：优先用EV，没有则用GN（野狐用GN）
            ev = props.get('EV', '')
            if isinstance(ev, list):
                ev = ev[0] if ev else ''
            if ev:
                info['event'] = ev
            else:
                gn = props.get('GN', '')
                if isinstance(gn, list):
                    gn = gn[0] if gn else ''
                info['event'] = gn
        except Exception:
            pass
        
        return info
    
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

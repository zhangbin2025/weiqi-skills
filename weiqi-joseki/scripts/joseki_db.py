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
        extract_joseki_from_sgf, extract_joseki_from_sgf_raw,
        parse_multigogm, detect_corner, convert_to_top_right
    )
    from .katago_downloader import iter_sgf_from_tar
except ImportError:
    from joseki_extractor import (
        CoordinateSystem, COORDINATE_SYSTEMS,
        extract_joseki_from_sgf, extract_joseki_from_sgf_raw,
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
    
    def list_all(self, category: str = None) -> List[dict]:
        """列出现式（精简字段）"""
        result = self.joseki_list
        if category:
            result = [j for j in result if j.get("category_path", "").startswith(category)]
        
        return [{
            "id": j["id"],
            "name": j.get("name", ""),
            "category_path": j.get("category_path", ""),
            "move_count": len(j.get("moves", [])),
            "frequency": j.get("frequency"),
            "probability": j.get("probability"),
            "tags": j.get("tags", [])
        } for j in result]
    
    # ========== 匹配 ==========
    
    def match(self, moves: List[str], top_k: int = 5) -> List[PrefixMatchResult]:
        """
        匹配定式 - 前缀匹配算法
        
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
        匹配右上角的定式 - 直接调用match（已统一转为右上角）
        """
        return self.match(moves, top_k=top_k)
    
    def identify_corners(self, sgf_data: str, top_k: int = 3, first_n: int = 80) -> Dict[str, List[PrefixMatchResult]]:
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
                coord_seq = [coord for _, coord in moves if coord]
                if coord_seq:
                    results[corner_key] = self.match_top_right(coord_seq, top_k)
        
        return results
    
    # ========== 导入功能 ==========
    
    def _extract_joseki_from_sources(
        self,
        sgf_sources: List,
        first_n: int,
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
                    corner_dict = extract_joseki_from_sgf_raw(sgf_item, first_n=first_n)
                    
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

    def import_from_sgfs(self,
                        sgf_sources: List,
                        min_count: int = 10,
                        min_moves: int = 4,
                        min_rate: float = 0.0,
                        first_n: int = 80,
                        dry_run: bool = False,
                        progress_callback: Optional[Callable] = None,
                        category: str = "/自动",
                        name_prefix: str = "自动提取",
                        verbose: bool = True) -> Tuple[int, int, List[str]]:
        """
        从SGF文件列表批量导入定式 - 主控流程

        Args:
            sgf_sources: SGF文件路径列表，或包含多个SGF文件的tar.bz2文件，或包含SGF内容的字符串列表（自动识别）
            min_count: 最少出现次数才入库
            min_moves: 定式至少多少手
            min_rate: 最小出现概率%
            first_n: 每谱提取前N手内的定式
            dry_run: 试运行，只统计不真入库
            progress_callback: 进度回调函数(current, total)
            category: 定式分类路径（默认"/自动"）
            name_prefix: 名称前缀（默认"自动提取"）
            verbose: 详细输出开关（默认True）

        返回:
            (added_count, skipped_count, candidates_list)
        """
        # 步骤1: 提取
        count_map, total_sources, total_sgf_files, total_extracted, unique_count = \
            self._extract_joseki_from_sources(sgf_sources, first_n, verbose, progress_callback)
        
        # 步骤2: 前缀累加
        count_map = self._accumulate_prefix_counts(count_map, verbose)
        
        # 步骤3: 筛选（使用实际的SGF文件数量）
        candidates = self._filter_candidates(count_map, total_sgf_files, min_count, min_moves, min_rate, verbose)
        
        if dry_run:
            return 0, 0, [f"{prefix} ({count}次)" for prefix, count in candidates]
        
        # 步骤4: 预计算 hash
        ruld_hashes, rudl_hashes = self._build_conflict_hash_sets(self.joseki_list)
        
        # 步骤5: 批量入库（使用实际的SGF文件数量计算概率）
        added, skipped, _ = self._batch_add_joseki(
            candidates, total_sgf_files, category, name_prefix,
            ruld_hashes, rudl_hashes, verbose
        )
        
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
        first_n: int = 50,
        min_moves: int = 4,
        limit: int = 50,
        verbose: bool = True
    ) -> Dict:
        """
        发现值得研究的定式（罕见定式优先）
        
        排序规则（优先级从高到低）：
        1. 罕见定式（匹配前缀短）
        2. 低频定式（库中出现次数少）
        3. 复杂定式（手数多的优先）
        
        Args:
            sgf_sources: SGF文件路径列表，或包含SGF内容的字符串列表
            first_n: 分析前N手的定式（默认50）
            min_moves: 定式最少手数（默认4）
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
                    # 提取四角定式
                    corner_dict = extract_joseki_from_sgf_raw(sgf_data, first_n=first_n)
                    
                    # 解析SGF元信息
                    sgf_info = self._parse_sgf_info(sgf_data, sgf_path)
                    
                    for corner, moves in corner_dict.items():
                        # 提取坐标序列（保留脱先标记tt，过滤空字符串）
                        coords = [coord for color, coord in moves if coord]
                        # 计算有效手数（非tt的坐标）
                        effective_moves = len([c for c in coords if c != 'tt'])
                        if effective_moves >= min_moves:
                            joseki_records.append((tuple(coords), sgf_info, corner))
                
            except Exception as e:
                if verbose:
                    print(f"  ⚠️ 处理源 {source} 时出错: {e}")
                continue
        
        total_joseki = len(joseki_records)
        if verbose:
            print(f"✅ 扫描完成: {total_files} 个文件，提取 {total_joseki} 个定式")
        
        # 步骤2: 去重并聚合来源
        unique_joseki = {}  # {moves_tuple: {'sources': [], 'count': 0}}
        seen_sources = {}  # {moves_tuple: set(source_keys)}
        source_counter = 0  # 用于区分内联SGF
        
        for moves_tuple, sgf_info, corner in joseki_records:
            if moves_tuple not in unique_joseki:
                unique_joseki[moves_tuple] = {
                    'sources': [],
                    'count': 0,
                    'moves': list(moves_tuple),
                    'move_count': len(moves_tuple)
                }
                seen_sources[moves_tuple] = set()
            
            unique_joseki[moves_tuple]['count'] += 1
            
            # 生成唯一来源键
            file_path = sgf_info.get('file', 'unknown')
            if file_path == 'inline':
                # 内联SGF使用计数器区分
                source_counter += 1
                source_key = f"inline_{source_counter}_{corner}"
            else:
                source_key = f"{file_path}_{corner}"
            
            # 避免重复添加相同来源
            if source_key not in seen_sources[moves_tuple]:
                seen_sources[moves_tuple].add(source_key)
                source_copy = sgf_info.copy()
                source_copy['corner'] = corner
                unique_joseki[moves_tuple]['sources'].append(source_copy)
        
        unique_count = len(unique_joseki)
        if verbose:
            print(f"📊 去重后: {unique_count} 个唯一定式")
        
        # 步骤3: 查询每个定式在库中的情况
        results = []
        
        if verbose:
            print("🔎 正在比对定式库...")
        
        for idx, (moves_tuple, data) in enumerate(unique_joseki.items()):
            coords = data['moves']
            
            # 查询最佳匹配的定式（使用新的前缀匹配）
            matches = self.match_top_right(coords, top_k=1)
            
            best_id = ''
            matched_prefix_len = 0
            matched_prefix_moves = []
            frequency = 0
            is_rare = True  # 默认为罕见
            
            if matches:
                best_match = matches[0]
                best_id = best_match.id
                matched_prefix_len = best_match.prefix_len
                matched_prefix_moves = coords[:matched_prefix_len]
                
                # 获取匹配的定式序列
                matched_joseki = self.get(best_id)
                if matched_joseki:
                    frequency = matched_joseki.get('frequency', 1)
                
                # 判断是否罕见：前缀长度是否达到 min_moves
                is_rare = matched_prefix_len < min_moves
            
            results.append({
                'joseki_id': best_id,
                'is_rare': is_rare,
                'moves': coords,
                'move_count': len(coords),
                'matched_prefix': matched_prefix_moves,
                'matched_prefix_len': matched_prefix_len,
                'frequency': frequency,
                'sources': data['sources']
            })
            
            if verbose and (idx + 1) % 100 == 0:
                print(f"  进度: {idx + 1}/{len(unique_joseki)}", end='', flush=True)
        
        if verbose:
            print(f"\n✅ 比对完成")
        
        # 步骤4: 按研究价值排序
        # 排序规则：
        # 1. 罕见的优先（is_rare=True）
        # 2. 罕见内部：匹配前缀短的优先（前缀短的更罕见）
        # 3. 相同前缀长度：匹配定式频率少的优先
        # 4. 最后排不罕见的（is_rare=False）
        results.sort(key=lambda x: (
            not x['is_rare'],           # 罕见的在前
            x['matched_prefix_len'],    # 匹配前缀短的优先
            x['frequency'],             # 频率少的优先
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

#!/usr/bin/env python3
"""
KataGo定式库构建器
基于KataGo Archive棋谱构建定式库

核心算法（与原代码保持一致）：
1. Phase 1: CMS统计频率 + 临时文件存储
2. Phase 2: 逆向遍历 + 单链检测 + 小顶堆选top-k
3. Phase 3: 统一转ruld方向去重
4. Phase 4: 入库
"""

import gzip
import heapq
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter
from datetime import datetime

from extraction import extract_moves_all_corners, get_move_sequence
from extraction.katago_downloader import iter_sgf_from_tar
from core.coords import convert_to_top_right
from storage.json_storage import JsonStorage, DEFAULT_DB_PATH
from utils import CountMinSketch

from auto import AutoState, get_adaptive_cms_config


# 四角配置
CORNERS = ['tl', 'tr', 'bl', 'br']


def convert_to_rudl(moves: List[str]) -> List[str]:
    """
    将ruld方向的着法序列转换为rudl方向
    
    使用 COORDINATE_SYSTEMS 中定义的坐标系进行转换：
    - ruld: 右上(左→下) - 原点是tr, x往左, y往下
    - rudl: 右上(下→左) - 原点是tr, x往下, y往左
    
    转换步骤：
    1. 用 ruld 坐标系将 SGF 坐标转为局部坐标 (x, y)
    2. 用 rudl 坐标系将局部坐标 (x, y) 转回 SGF 坐标
    """
    from core.coords import COORDINATE_SYSTEMS
    
    if not moves:
        return []
    
    # 获取坐标系转换器
    ruld_system = COORDINATE_SYSTEMS['ruld']
    rudl_system = COORDINATE_SYSTEMS['rudl']
    
    result = []
    for coord in moves:
        # ruld -> 局部坐标 (col, row)
        local_x, local_y = ruld_system._sgf_to_local(coord)
        # 局部坐标 -> rudl
        rudl_coord = rudl_system._local_to_sgf(local_x, local_y)
        result.append(rudl_coord)
    
    return result


def convert_to_ruld(moves: List[str]) -> List[str]:
    """
    将rudl方向的着法序列转换回ruld方向
    （convert_to_rudl的逆操作）
    
    使用 COORDINATE_SYSTEMS 中定义的坐标系进行转换
    """
    from core.coords import COORDINATE_SYSTEMS
    
    if not moves:
        return []
    
    # 获取坐标系转换器
    ruld_system = COORDINATE_SYSTEMS['ruld']
    rudl_system = COORDINATE_SYSTEMS['rudl']
    
    result = []
    for coord in moves:
        # rudl -> 局部坐标 (col, row)
        local_x, local_y = rudl_system._sgf_to_local(coord)
        # 局部坐标 -> ruld
        ruld_coord = ruld_system._local_to_sgf(local_x, local_y)
        result.append(ruld_coord)
    
    return result


class HeapItem:
    """小顶堆元素，用于top-k选择"""
    def __init__(self, count: int, prefix: str, direction: str, prefix_hash: tuple):
        self.count = count
        self.prefix = prefix
        self.direction = direction
        self.prefix_hash = prefix_hash
    
    def __lt__(self, other):
        # 小顶堆：计数小的在前
        return self.count < other.count
    
    def __eq__(self, other):
        return self.count == other.count and self.prefix_hash == other.prefix_hash
    
    def __hash__(self):
        return hash((self.count, self.prefix_hash))


class KatagoJosekiBuilder:
    """KataGo定式库构建器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Args:
            db_path: 数据库路径，默认使用 ~/.weiqi-joseki/database.json
        """
        self.storage = JsonStorage(db_path)
    
    def _extract_from_tar_to_temp(
        self,
        tar_path: Path,
        temp_f_out,
        cms: CountMinSketch,
        config: dict,
        verbose: bool = False
    ) -> tuple:
        """从单个tar文件提取四角着法到temp文件，同时更新CMS
        
        这是一个可复用的核心函数，供自定义构建和自动构建共用。
        
        Args:
            tar_path: tar文件路径
            temp_f_out: 临时文件写入句柄（gzip.open后的文件对象）
            cms: CountMinSketch实例
            config: 配置字典，包含 first_n, distance_threshold, min_moves
            verbose: 是否打印进度
            
        Returns:
            (processed_sgf, joseki_count, prefix_count, unique_sequences)
        """
        first_n = config.get('first_n', 80)
        distance_threshold = config.get('distance_threshold', 4)
        min_moves = config.get('min_moves', 4)
        
        processed = 0
        joseki_count = 0
        prefix_count = 0
        total_unique_sequences = 0
        
        for sgf_data in iter_sgf_from_tar(str(tar_path)):
            try:
                corner_moves_dict = extract_moves_all_corners(
                    sgf_data, first_n=first_n, distance_threshold=distance_threshold
                )
                
                seen_sequences = set()
                
                for corner in CORNERS:
                    moves = corner_moves_dict.get(corner)
                    if not moves or len(moves) < min_moves:
                        continue
                    
                    coords = get_move_sequence(moves)
                    if len(coords) < min_moves:
                        continue
                    
                    tr_coords = convert_to_top_right(coords, corner)
                    ruld = " ".join(tr_coords)
                    rudl = " ".join(convert_to_rudl(tr_coords))
                    
                    for direction, seq in [('ruld', ruld), ('rudl', rudl)]:
                        if seq in seen_sequences:
                            continue
                        seen_sequences.add(seq)
                        
                        temp_f_out.write(f"{direction}|{seq}\n")
                        joseki_count += 1
                        
                        seq_parts = seq.split()
                        for end in range(min_moves, len(seq_parts) + 1):
                            prefix = " ".join(seq_parts[:end])
                            cms.update(prefix)
                            prefix_count += 1
                
                total_unique_sequences += len(seen_sequences)
                processed += 1
                
            except Exception:
                continue
            
            if verbose and processed % 1000 == 0:
                print(f"\r  已处理: {processed}谱", end='', flush=True)
        
        if verbose:
            print(f"\r  完成: {processed}谱, {joseki_count}定式串, {prefix_count}前缀")
        
        return processed, joseki_count, prefix_count, total_unique_sequences
    
    def _iter_temp_files(self, temp_paths):
        """流式迭代多个temp文件的内容
        
        Args:
            temp_paths: temp文件路径列表
            
        Yields:
            每行的内容 (str)
        """
        for temp_path in temp_paths:
            with gzip.open(temp_path, 'rt', encoding='utf-8') as f_in:
                for line in f_in:
                    yield line
    
    def _build_from_cms_and_temp(
        self, 
        temp_source,  # Path or List[Path]
        cms, 
        min_freq: int, 
        top_k: int,
        min_moves: int, 
        max_moves: int, 
        total_sequences: int, 
        verbose: bool
    ) -> List[dict]:
        """从CMS和临时文件构建定式（Phase 2-4）
        
        Args:
            temp_source: 单个Path或Path列表（支持多文件流式读取）
        """
        if verbose:
            print(f"🔄 Phase 2: 逆向遍历+单链检测，选取top-{top_k}...")
        
        heap = []
        seen_hashes = {}
        SINGLE_CHAIN_THRESHOLD = 0.05
        
        processed_seq = 0
        prefix_processed = 0
        skipped_single_chain = 0
        
        # 根据temp_source类型选择迭代方式
        if isinstance(temp_source, list):
            line_iter = self._iter_temp_files(temp_source)
        else:
            line_iter = gzip.open(temp_source, 'rt', encoding='utf-8')
        
        try:
            for line in line_iter:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                
                direction, joseki_str = line.split('|', 1)
                seq_parts = joseki_str.split()
                
                if len(seq_parts) < min_moves:
                    continue
                
                last_count = float('inf')
                
                for end in range(len(seq_parts), min_moves - 1, -1):
                    prefix_parts = seq_parts[:end]
                    prefix = " ".join(prefix_parts)
                    est_count = cms.estimate(prefix)
                    
                    if est_count < min_freq:
                        last_count = est_count
                        continue
                    
                    prefix_hash = tuple(prefix_parts)
                    
                    if last_count != float('inf'):
                        count_diff_ratio = abs(est_count - last_count) / max(est_count, last_count, 1)
                        if count_diff_ratio < SINGLE_CHAIN_THRESHOLD:
                            skipped_single_chain += 1
                            last_count = est_count
                            continue
                    
                    last_count = est_count
                    
                    if prefix_hash in seen_hashes:
                        break
                    
                    if len(heap) < top_k:
                        item = HeapItem(est_count, prefix, direction, prefix_hash)
                        heapq.heappush(heap, item)
                        seen_hashes[prefix_hash] = True
                        prefix_processed += 1
                    elif est_count > heap[0].count:
                        old_item = heapq.heapreplace(heap, HeapItem(est_count, prefix, direction, prefix_hash))
                        del seen_hashes[old_item.prefix_hash]
                        seen_hashes[prefix_hash] = True
                        prefix_processed += 1
                
                processed_seq += 1
                if verbose and processed_seq % 10000 == 0:
                    print(f"\r  处理: {processed_seq}定式/{prefix_processed}前缀, "
                          f"堆大小: {len(heap)}, 单链跳过: {skipped_single_chain}", 
                          end='', flush=True)
        finally:
            # 如果是单文件模式，需要关闭文件
            if not isinstance(temp_source, list) and hasattr(line_iter, 'close'):
                line_iter.close()
        
        if verbose:
            print(f"\n✅ Phase 2完成: {processed_seq}定式串/{prefix_processed}前缀候选, "
                  f"堆大小: {len(heap)}, 单链跳过: {skipped_single_chain}")
        
        # Phase 3: 统一转ruld方向并去重
        if verbose:
            print(f"🔄 Phase 3: 统一转ruld方向并去重...")
        
        temp_list = []
        for item in heap:
            moves = item.prefix.split()
            
            # 统一转ruld方向
            if item.direction == 'rudl':
                moves = convert_to_ruld(moves)
            
            temp_list.append({
                'moves': moves,
                'count': item.count,
                'original_direction': item.direction
            })
        
        # 去重
        seen = {}
        discard = set()
        
        for item in temp_list:
            moves_tuple = tuple(item['moves'])
            if moves_tuple in seen:
                discard.add(moves_tuple)
            else:
                seen[moves_tuple] = item
        
        # 按频率排序
        candidates = [item for key, item in seen.items() if key not in discard]
        candidates.sort(key=lambda x: -x['count'])
        
        # 最终去重（使用rudl作为key）
        final_discard = set()
        for item in candidates:
            rudl_moves = tuple(convert_to_rudl(item['moves']))
            rudl_str = ' '.join(rudl_moves)
            if rudl_str in final_discard:
                continue
            final_discard.add(rudl_str)
        
        if verbose:
            print(f"  去重前: {len(temp_list)}  去重后: {len(candidates)}")
        
        # Phase 4: 转换为定式格式
        total_seq = max(total_sequences, 1)
        joseki_list = []
        for i, cand in enumerate(candidates):
            joseki = {
                "id": f"kj_{i+1:05d}",
                "source": "katago",
                "moves": cand['moves'],
                "frequency": cand['count'],
                "probability": round(cand['count'] / total_seq, 6),
                "created_at": datetime.now().isoformat()
            }
            joseki_list.append(joseki)
        
        if verbose:
            print(f"✅ 构建完成: {len(joseki_list)} 条定式")
        
        return joseki_list

    def build_from_tar(self, 
                       tar_path: str,
                       min_freq: int = 5,
                       top_k: int = 10000,
                       first_n: int = 80,
                       distance_threshold: int = 4,
                       min_moves: int = 4,
                       max_moves: int = 50,
                       verbose: bool = True) -> List[dict]:
        """从单个 tar 文件构建定式库（便捷方法）"""
        return self.build_from_files(
            [Path(tar_path)],
            min_freq=min_freq,
            top_k=top_k,
            first_n=first_n,
            distance_threshold=distance_threshold,
            min_moves=min_moves,
            max_moves=max_moves,
            verbose=verbose
        )
    
    
    def save_to_db(self, joseki_list: List[dict], append: bool = False):
        """批量保存定式列表到数据库（优化版）"""
        if not append:
            self.storage._data["joseki_list"] = []
        
        # 批量添加到内存，最后统一写入
        self.storage._data["joseki_list"].extend(joseki_list)
        self.storage._save()
        
        print(f"已保存 {len(joseki_list)} 条定式到 {self.storage.db_path}")


# ========== 自动增量构建方法 ==========

def _ensure_auto_dirs(auto_dir: Path):
    """确保自动构建目录存在"""
    (auto_dir / "temp").mkdir(parents=True, exist_ok=True)


class KatagoJosekiBuilderAutoMixin:
    """自动构建功能混入类（简化版）
    
    核心思想：状态即文件系统，不依赖复杂的进度跟踪。
    通过多重继承或monkey patch方式添加到KatagoJosekiBuilder。
    """
    
    def run_auto(self, state: AutoState, cache_dir: Path) -> Optional[List[dict]]:
        """自动增量构建主入口（批量保存优化版）
        
        优化：每30天保存一次CMS，减少写入次数
        
        Args:
            state: 状态管理器（只使用config）
            cache_dir: tar文件缓存目录
            
        Returns:
            重建后的定式列表
        """
        print("=" * 60)
        print("🚀 Katago 自动增量构建")
        print("=" * 60)
        
        # 确保目录存在
        _ensure_auto_dirs(state.auto_dir)
        
        # 获取所有tar文件（按日期升序）
        tar_files = sorted(cache_dir.glob("*rating.tar.bz2"))
        
        if not tar_files:
            print("⚠️  缓存目录中没有tar文件")
            return None
        
        # 检查断点（读取cms文件的修改时间）
        cms_path = state.auto_dir / "cms.pkl"
        last_date = None
        if cms_path.exists():
            mtime = cms_path.stat().st_mtime
            last_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            print(f"📍 断点恢复：上次处理到 {last_date}")
        
        # 过滤tar文件（从断点下一个开始）
        if last_date:
            tar_files = [f for f in tar_files 
                         if f.name.replace("rating.tar.bz2", "") > last_date]
            if not tar_files:
                print("✅ 所有日期已处理，无需增量")
        
        # 加载或创建CMS
        cms_config = get_adaptive_cms_config(state.config.get('global_top_k', 100000) * 20)
        if cms_path.exists():
            cms = CountMinSketch.load_from_file(cms_path)
            print(f"📊 加载CMS: width={cms.width}, depth={cms.depth}")
        else:
            cms = CountMinSketch(width=cms_config['width'], depth=cms_config['depth'])
            print(f"📊 创建CMS: width={cms.width}, depth={cms.depth}")
        
        config = {
            'first_n': state.config.get('first_n', 80),
            'distance_threshold': state.config.get('distance_threshold', 4),
            'min_moves': state.config.get('min_moves', 4)
        }
        
        # 步骤1&2: 提取并批量更新CMS
        print("\n【步骤1/2】提取棋谱并更新CMS...")
        
        BATCH_SIZE = 30  # 每30天保存一次
        processed_count = 0
        batch_count = 0
        
        for idx, tar_path in enumerate(tar_files, 1):
            date_str = tar_path.name.replace("rating.tar.bz2", "")
            temp_path = state.auto_dir / "temp" / f"{date_str}.txt.gz"
            
            # 如果temp已存在且有效，跳过（已处理过）
            if temp_path.exists() and temp_path.stat().st_size > 100:
                continue
            
            print(f"   处理: {date_str}...")
            
            # 提取到temp
            with gzip.open(temp_path, 'wt', encoding='utf-8') as f_out:
                dummy_cms = CountMinSketch(width=1000, depth=2)
                processed, joseki_count, _, _ = self._extract_from_tar_to_temp(
                    tar_path, f_out, dummy_cms, config, verbose=False
                )
            
            if processed == 0:
                print(f"      ⚠️  未提取到有效棋谱")
                continue
            
            # 更新CMS
            with gzip.open(temp_path, 'rt', encoding='utf-8') as f_in:
                for line in f_in:
                    line = line.strip()
                    if not line or '|' not in line:
                        continue
                    
                    direction, seq = line.split('|', 1)
                    seq_parts = seq.split()
                    min_moves = config['min_moves']
                    
                    for end in range(min_moves, len(seq_parts) + 1):
                        prefix = " ".join(seq_parts[:end])
                        cms.update(prefix)
            
            processed_count += 1
            print(f"      ✅ 提取: {processed}谱, {joseki_count}定式串")
            
            # 每30天或最后一个保存一次
            if processed_count % BATCH_SIZE == 0 or idx == len(tar_files):
                cms.save_to_file(cms_path)
                # 更新mtime为当前处理日期（断点记录）
                timestamp = datetime.strptime(date_str, "%Y-%m-%d").timestamp()
                os.utime(cms_path, (timestamp, timestamp))
                batch_count += 1
                print(f"      💾 批次 {batch_count} 保存完成（{min(BATCH_SIZE, processed_count % BATCH_SIZE or BATCH_SIZE)}天）")
        
        if processed_count == 0:
            print("   ℹ️  没有新的棋谱需要处理")
        else:
            print(f"   ✅ 共处理 {processed_count} 个新日期，保存 {batch_count} 次")
        
        # 步骤3: 重建
        print("\n【步骤3】重建定式库...")
        return self._auto_rebuild(state, cms, config)
    
    def _auto_rebuild(self, state: AutoState, cms: CountMinSketch, config: dict) -> List[dict]:
        """步骤3: 重建定式库"""
        print("🔄 重建定式库...")
        
        # 收集所有temp文件
        temp_dir = state.auto_dir / "temp"
        temp_files = sorted(temp_dir.glob("*.txt.gz"))
        
        if not temp_files:
            print("⚠️  没有可用的temp文件")
            return []
        
        print(f"   共 {len(temp_files)} 个temp文件")
        
        # 估算总序列数
        total_sequences = sum(1 for _ in self._iter_temp_files(temp_files)) // 2
        
        # 调用构建函数
        joseki_list = self._build_from_cms_and_temp(
            temp_files,
            cms,
            min_freq=state.config.get('min_freq', 5),
            top_k=state.config.get('global_top_k', 10000),
            min_moves=state.config.get('min_moves', 4),
            max_moves=state.config.get('max_moves', 50),
            total_sequences=max(total_sequences, 1),
            verbose=True
        )
        
        # 整库替换
        self.save_to_db(joseki_list, append=False)
        
        print(f"✅ 重建完成，共 {len(joseki_list)} 条定式")
        return joseki_list


# 将自动构建方法混入KatagoJosekiBuilder
KatagoJosekiBuilder.run_auto = KatagoJosekiBuilderAutoMixin.run_auto
KatagoJosekiBuilder._auto_rebuild = KatagoJosekiBuilderAutoMixin._auto_rebuild


def build_katago_joseki_db(
    tar_path: str,
    db_path: Optional[str] = None,
    min_freq: int = 5,
    top_k: int = 10000,
    first_n: int = 80,
    distance_threshold: int = 4,
    min_moves: int = 4,
    max_moves: int = 50
) -> int:
    """便捷函数：从KataGo棋谱构建定式库"""
    builder = KatagoJosekiBuilder(db_path)
    
    joseki_list = builder.build_from_tar(
        tar_path=tar_path,
        min_freq=min_freq,
        top_k=top_k,
        first_n=first_n,
        distance_threshold=distance_threshold,
        min_moves=min_moves,
        max_moves=max_moves
    )
    
    builder.save_to_db(joseki_list, append=False)
    return len(joseki_list)

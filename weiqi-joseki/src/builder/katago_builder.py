#!/usr/bin/env python3
"""
KataGo定式库构建器
基于KataGo Archive棋谱构建定式库
"""

import json
import tarfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Iterator
from collections import Counter
from datetime import datetime

from ..extraction import extract_moves_all_corners, get_move_sequence
from ..extraction.katago_downloader import iter_sgf_from_tar
from ..core.coords import convert_to_top_right, COORDINATE_SYSTEMS
from ..storage.json_storage import JsonStorage, DEFAULT_DB_PATH


# 四角配置
CORNERS = ['tl', 'tr', 'bl', 'br']


def convert_to_rudl(moves: List[str]) -> List[str]:
    """
    将ruld方向的着法序列转换为rudl方向
    
    ruld: 右上(左→下) - 原点是sa(18,0)
    rudl: 右上(下→左) - 原点是ss(18,18)
    
    转换: (x,y) → (y,x) 然后取反
    """
    rudl_moves = []
    for sgf in moves:
        if not sgf or sgf == 'pass' or sgf == 'tt':
            rudl_moves.append(sgf)
        else:
            # ruld SGF坐标 → 局部坐标
            c = ord(sgf[0]) - ord('a')  # 0-18
            r = ord(sgf[1]) - ord('a')  # 0-18
            # ruld局部坐标: x = 18-c, y = r
            x = 18 - c
            y = r
            # rudl局部坐标: x' = y, y' = x
            # rudl SGF: col = 18-y', row = 18-x'
            new_col = 18 - y
            new_row = 18 - x
            new_sgf = chr(ord('a') + new_col) + chr(ord('a') + new_row)
            rudl_moves.append(new_sgf)
    return rudl_moves


def generate_eight_directions(corner_moves: Dict[str, List[str]]) -> List[Tuple[str, List[str]]]:
    """
    生成8个方向的着法串（四角 × 两方向）
    
    Args:
        corner_moves: {corner: [coord, ...], ...} 原始SGF坐标
    
    Returns:
        [(direction_id, moves), ...]
        direction_id: 如 "tr_ruld", "tr_rudl", "tl_ruld", ...
    """
    results = []
    
    for corner in CORNERS:
        moves = corner_moves.get(corner)
        if not moves or len(moves) < 2:
            continue
        
        # 转换到右上角视角
        tr_moves = convert_to_top_right(moves, corner)
        
        # ruld方向
        results.append((f"{corner}_ruld", tr_moves))
        
        # rudl方向
        rudl_moves = convert_to_rudl(tr_moves)
        results.append((f"{corner}_rudl", rudl_moves))
    
    return results


def extract_prefixes(moves: List[str], min_moves: int = 4) -> List[str]:
    """
    从着法串提取所有可能的前缀
    
    与原代码保持一致：
    - 从 min_moves 开始到序列末尾
    - 没有最大长度限制
    - 使用空格分隔（与原代码一致）
    
    Args:
        moves: 着法序列
        min_moves: 最少手数（前缀从此手数开始提取）
    
    Returns:
        前缀列表（空格分隔的字符串）
    """
    prefixes = []
    n = len(moves)
    
    for i in range(min_moves, n + 1):
        prefix = ' '.join(moves[:i])
        prefixes.append(prefix)
    
    return prefixes


class KatagoJosekiBuilder:
    """KataGo定式库构建器"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.storage = JsonStorage(db_path)
        self.prefix_counter = Counter()
    
    def process_sgf(self, sgf_data: str, first_n: int = 80, 
                    distance_threshold: int = 4) -> Dict[str, List[str]]:
        """
        处理单个SGF，提取四角着法
        
        Returns:
            {corner: [coord, ...], ...} 原始SGF坐标
        """
        corner_moves = extract_moves_all_corners(
            sgf_data, 
            first_n=first_n, 
            distance_threshold=distance_threshold
        )
        
        # 转换为纯坐标序列
        return {corner: get_move_sequence(moves) 
                for corner, moves in corner_moves.items()}
    
    def process_tar_file(self, tar_path: str, max_games: int = None,
                         first_n: int = 80, distance_threshold: int = 4) -> Counter:
        """
        处理tar文件中的所有SGF，统计前缀频率
        
        Args:
            tar_path: tar文件路径
            max_games: 最大处理棋谱数（None表示全部）
            first_n: 提取前N手
            distance_threshold: 连通块距离阈值
        
        Returns:
            Counter: 前缀频率统计
        """
        counter = Counter()
        processed = 0
        
        print(f"开始处理: {tar_path}")
        
        for sgf_data in iter_sgf_from_tar(tar_path):
            if max_games and processed >= max_games:
                break
            
            try:
                # 提取四角着法
                corner_moves = self.process_sgf(sgf_data, first_n, distance_threshold)
                
                # 生成8个方向
                eight_directions = generate_eight_directions(corner_moves)
                
                # 提取所有前缀（从min_moves开始）
                for direction_id, moves in eight_directions:
                    prefixes = extract_prefixes(moves, min_moves=4)
                    for prefix in prefixes:
                        # 前缀格式: "direction_id:moves"
                        key = f"{direction_id}:{prefix}"
                        counter[key] += 1
                
                processed += 1
                if processed % 1000 == 0:
                    print(f"  已处理 {processed} 局棋谱，当前前缀数: {len(counter)}")
            
            except Exception as e:
                # 跳过有问题的棋谱
                continue
        
        print(f"处理完成: {processed} 局棋谱，共 {len(counter)} 个唯一前缀")
        return counter
    
    def build_from_tar(self, tar_path: str, 
                       min_freq: int = 5,
                       top_k: int = 10000,
                       max_games: int = None,
                       first_n: int = 80,
                       distance_threshold: int = 4) -> List[dict]:
        """
        从tar文件构建定式库
        
        Args:
            tar_path: tar文件路径
            min_freq: 最小出现频率
            top_k: 入库定式数量上限
            max_games: 最大处理棋谱数
            first_n: 提取前N手
            distance_threshold: 连通块距离阈值
        
        Returns:
            入库的定式列表
        """
        # 统计前缀频率
        counter = self.process_tar_file(tar_path, max_games, first_n, distance_threshold)
        
        # 过滤低频前缀
        frequent_prefixes = {k: v for k, v in counter.items() if v >= min_freq}
        
        print(f"频率>={min_freq}的前缀: {len(frequent_prefixes)} 个")
        
        # 按频率排序，取top-k
        sorted_prefixes = sorted(frequent_prefixes.items(), key=lambda x: -x[1])[:top_k]
        
        # 转换为定式格式
        joseki_list = []
        for i, (key, freq) in enumerate(sorted_prefixes):
            direction_id, moves_str = key.split(':', 1)
            corner, direction = direction_id.rsplit('_', 1)
            moves = moves_str.split()  # 空格分隔，与原代码一致
            
            joseki = {
                "id": f"kj_{i+1:05d}",
                "source": "katago",
                "corner": corner,
                "direction": direction,
                "moves": moves,
                "frequency": freq,
                "created_at": datetime.now().isoformat()
            }
            joseki_list.append(joseki)
        
        print(f"构建完成: {len(joseki_list)} 条定式")
        return joseki_list
    
    def save_to_db(self, joseki_list: List[dict], append: bool = False):
        """
        保存定式列表到数据库
        
        Args:
            joseki_list: 定式列表
            append: 是否追加（False则清空后写入）
        """
        if not append:
            self.storage.clear()
        
        for joseki in joseki_list:
            self.storage.add(joseki)
        
        print(f"已保存 {len(joseki_list)} 条定式到 {self.storage.db_path}")


def build_katago_joseki_db(
    tar_path: str,
    db_path: Optional[str] = None,
    min_freq: int = 5,
    top_k: int = 10000,
    max_games: int = None,
    first_n: int = 80,
    distance_threshold: int = 4
) -> int:
    """
    便捷函数：从KataGo棋谱构建定式库
    
    Returns:
        入库的定式数量
    """
    builder = KatagoJosekiBuilder(db_path)
    
    # 构建定式
    joseki_list = builder.build_from_tar(
        tar_path=tar_path,
        min_freq=min_freq,
        top_k=top_k,
        max_games=max_games,
        first_n=first_n,
        distance_threshold=distance_threshold
    )
    
    # 保存到数据库
    builder.save_to_db(joseki_list, append=False)
    
    return len(joseki_list)

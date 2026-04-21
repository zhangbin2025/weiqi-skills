#!/usr/bin/env python3
"""
定式发现模块 (discover)
替代原match/identify接口，简化设计
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..extraction import extract_moves_all_corners, get_move_sequence
from ..core.coords import convert_to_top_right
from ..matching import TrieMatcher, PrefixMatchResult
from ..builder import convert_to_rudl


@dataclass
class DiscoverResult:
    """定式发现结果"""
    joseki_id: str           # 定式ID
    name: str                # 定式名称
    prefix: str              # 匹配的前缀着法串
    prefix_len: int          # 匹配的前缀长度
    total_moves: int         # 定式总手数
    source_corner: str       # 棋谱来源角 "tl"/"tr"/"bl"/"br"
    direction: str           # 匹配方向 "ruld" 或 "rudl"


class JosekiDiscoverer:
    """定式发现器"""
    
    def __init__(self, joseki_list: List[dict]):
        """
        初始化发现器
        
        Args:
            joseki_list: 定式列表，每个定式包含 id, name, moves
        """
        self.matcher = TrieMatcher()
        self.matcher.build(joseki_list)
    
    def discover_corner(self, moves: List[str], corner: str) -> List[DiscoverResult]:
        """
        发现单个角的定式
        
        流程：
        1. 转换到右上角视角
        2. 生成 ruld 和 rudl 两个方向
        3. 用 Trie 树匹配最长前缀
        4. 收集结果
        
        Args:
            moves: 着法坐标列表（原始SGF坐标）
            corner: 来源角 "tl"/"tr"/"bl"/"br"
        
        Returns:
            DiscoverResult列表
        """
        if not moves or len(moves) < 2:
            return []
        
        # 转换到右上角视角 (ruld方向)
        tr_moves = convert_to_top_right(moves, corner)
        
        results = []
        
        # 先尝试ruld方向
        ruld_matches = self.matcher.match(tr_moves, top_k=1)
        if ruld_matches:
            ruld_match = ruld_matches[0]
            ruld_prefix = " ".join(tr_moves[:ruld_match.prefix_len])
            results.append(DiscoverResult(
                joseki_id=ruld_match.id,
                name=ruld_match.name,
                prefix=ruld_prefix,
                prefix_len=ruld_match.prefix_len,
                total_moves=ruld_match.total_moves,
                source_corner=corner,
                direction="ruld"
            ))
        
        # 再尝试rudl方向
        rudl_moves = convert_to_rudl(tr_moves)
        rudl_matches = self.matcher.match(rudl_moves, top_k=1)
        if rudl_matches:
            rudl_match = rudl_matches[0]
            rudl_prefix = " ".join(rudl_moves[:rudl_match.prefix_len])
            results.append(DiscoverResult(
                joseki_id=rudl_match.id,
                name=rudl_match.name,
                prefix=rudl_prefix,
                prefix_len=rudl_match.prefix_len,
                total_moves=rudl_match.total_moves,
                source_corner=corner,
                direction="rudl"
            ))
        
        return results
    
    def discover(self, sgf_data: str, first_n: int = 80, 
                 distance_threshold: int = 4) -> Dict[str, List[DiscoverResult]]:
        """
        从SGF发现定式
        
        Args:
            sgf_data: SGF棋谱内容
            first_n: 提取前N手
            distance_threshold: 连通块距离阈值
        
        Returns:
            {corner: [DiscoverResult, ...], ...}
            corner: "tl"/"tr"/"bl"/"br"
        """
        # 使用新提取接口提取四角着法
        corner_moves_dict = extract_moves_all_corners(
            sgf_data, 
            first_n=first_n, 
            distance_threshold=distance_threshold
        )
        
        results = {}
        
        for corner in ['tl', 'tr', 'bl', 'br']:
            moves = corner_moves_dict.get(corner)
            if not moves:
                continue
            
            coords = get_move_sequence(moves)
            corner_results = self.discover_corner(coords, corner)
            
            if corner_results:
                results[corner] = corner_results
        
        return results


def discover_joseki(
    sgf_data: str,
    joseki_list: List[dict],
    first_n: int = 80,
    distance_threshold: int = 4
) -> Dict[str, List[DiscoverResult]]:
    """
    便捷函数：从SGF发现定式
    
    Args:
        sgf_data: SGF棋谱内容
        joseki_list: 定式列表
        first_n: 提取前N手
        distance_threshold: 连通块距离阈值
    
    Returns:
        {corner: [DiscoverResult, ...], ...}
    """
    discoverer = JosekiDiscoverer(joseki_list)
    return discoverer.discover(sgf_data, first_n, distance_threshold)

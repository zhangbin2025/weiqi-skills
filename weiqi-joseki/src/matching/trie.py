#!/usr/bin/env python3
"""
Trie树实现
用于定式着法串的前缀匹配
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PrefixMatchResult:
    """前缀匹配结果 - 最长前缀优先，同前缀选总手数最短的"""
    id: str
    name: str
    prefix_len: int      # 匹配的前缀长度（最长优先）
    total_moves: int     # 定式总手数（同前缀时越短越优先）
    matched_direction: str  # "ruld" 或 "rudl"


class TrieMatcher:
    """Trie树匹配器 - 支持ruld和rudl两个方向"""
    
    def __init__(self):
        self._trie: Dict = {}      # ruld方向前缀树
        self._trie_rudl: Dict = {} # rudl方向前缀树
        self._joseki_map: Dict[str, dict] = {}  # id -> 定式数据
    
    def build(self, joseki_list: List[dict]):
        """
        从定式列表构建Trie树
        
        Args:
            joseki_list: 定式列表，每个定式包含 id, name, moves
        """
        self._trie = {}
        self._trie_rudl = {}
        self._joseki_map = {}
        
        for j in joseki_list:
            joseki_id = j.get("id")
            if not joseki_id:
                continue
            
            self._joseki_map[joseki_id] = j
            moves = j.get("moves", [])
            if not moves:
                continue
            
            # ruld方向入树
            self._add_to_trie(self._trie, moves, joseki_id)
            
            # rudl方向入树
            rudl_moves = self._convert_to_rudl(moves)
            self._add_to_trie(self._trie_rudl, rudl_moves, joseki_id)
    
    def _add_to_trie(self, trie: dict, moves: List[str], joseki_id: str):
        """将定式着法序列加入前缀树"""
        node = trie
        for move in moves:
            if move not in node:
                node[move] = {'next': {}, 'ids': []}
            node[move]['ids'].append(joseki_id)
            node = node[move]['next']
    
    def match(self, moves: List[str], top_k: int = 3) -> List[PrefixMatchResult]:
        """
        匹配着法序列，返回最佳匹配的定式
        
        Args:
            moves: 着法序列
            top_k: 返回结果数量上限
        
        Returns:
            匹配结果列表，按 prefix_len 降序，相同按 total_moves 升序
        """
        # 在ruld方向匹配
        ruld_results = self._match_direction(self._trie, moves, "ruld")
        
        # 在rudl方向匹配
        rudl_moves = self._convert_to_rudl(moves)
        rudl_results = self._match_direction(self._trie_rudl, rudl_moves, "rudl")
        
        # 合并结果
        all_results = ruld_results + rudl_results
        
        # 按 id 和 direction 去重，保留 prefix_len 最大的
        seen = {}
        for prefix_len, joseki_id, total_moves, direction in all_results:
            key = (joseki_id, direction)
            if key not in seen or seen[key][0] < prefix_len:
                seen[key] = (prefix_len, total_moves, direction)
        
        # 构建结果对象
        results = []
        for (joseki_id, direction), (prefix_len, total_moves, _) in seen.items():
            joseki = self._joseki_map.get(joseki_id, {})
            results.append(PrefixMatchResult(
                id=joseki_id,
                name=joseki.get("name", joseki_id),
                prefix_len=prefix_len,
                total_moves=total_moves,
                matched_direction=direction
            ))
        
        # 排序：按 prefix_len 降序，相同按 total_moves 升序
        results.sort(key=lambda x: (-x.prefix_len, x.total_moves))
        
        return results[:top_k]
    
    def _match_direction(self, trie: dict, moves: List[str], direction: str) -> List[Tuple[int, str, int, str]]:
        """
        在指定方向的Trie中匹配
        
        Returns:
            [(prefix_len, joseki_id, total_moves, direction), ...]
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
            joseki = self._joseki_map.get(joseki_id, {})
            total_moves = len(joseki.get("moves", []))
            results.append((match_len, joseki_id, total_moves, direction))
        
        return results
    
    @staticmethod
    def _convert_to_rudl(moves: List[str]) -> List[str]:
        """
        将ruld方向的着法序列转换为rudl方向
        
        转换原理:
        ruld: 右上(左→下) - 原点是sa(18,0)
        rudl: 右上(下→左) - 原点是ss(18,18)
        
        对于19路棋盘:
        - ruld局部坐标(x,y) → SGF: chr(ord('a') + (18-x)) + chr(ord('a') + y)
        - rudl局部坐标(x,y) → SGF: chr(ord('a') + (18-y)) + chr(ord('a') + (18-x))
        
        因此转换: (x,y) → (y,x) 然后取反
        """
        rudl_moves = []
        for sgf in moves:
            if not sgf or sgf == 'pass' or sgf == 'tt':
                rudl_moves.append(sgf)
            else:
                # ruld SGF坐标 → 局部坐标
                c = ord(sgf[0]) - ord('a')  # 0-18, ruld中18是左边界
                r = ord(sgf[1]) - ord('a')  # 0-18, ruld中0是上边界
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
    
    def export_tree(self, prefix: List[str] = None, main_branch: List[str] = None, limit: int = 100) -> str:
        """导出树状SGF"""
        # 定位前缀
        trie = self._trie
        for move in (prefix or []):
            if move not in trie:
                return "(;C[前缀不存在])"
            trie = trie[move]['next']
        
        # 收集包含前缀的定式终点
        paths = self._collect_joseki_endpoints(prefix or [])
        
        # 按频率排序，取limit
        paths.sort(key=lambda x: -x[1])
        selected = paths[:limit]
        
        # 构建路径到ids的映射
        ids_map = {tuple(p[0]): p[2] for p in paths}
        
        # 主分支放第一个（使用完整路径以正确合并前缀）
        if main_branch:
            # 如果主分支匹配某个定式，保留该定式的频率
            main_path_tuple = tuple(main_branch)
            if main_path_tuple in ids_map:
                # 主分支是定式路径，保留频率
                main_freq = next(p[1] for p in paths if p[0] == main_branch)
                main_tuple = (main_branch, main_freq, ids_map[main_path_tuple])
            else:
                # 主分支不是定式路径
                main_tuple = (main_branch, 0, [])
            # 移除已存在的相同路径
            selected = [p for p in selected if p[0] != main_branch]
            selected.insert(0, main_tuple)
            selected = selected[:limit]
        
        # 构建树（传递主分支用于标记）
        tree = self._build_tree_from_paths(selected, main_branch)
        
        # 使用 sgfmill 生成SGF
        prefix_str = " ".join(prefix) if prefix else "all"
        return self._tree_to_sgf(tree, 0, main_branch, 0, prefix_str)
    
    def _collect_joseki_endpoints(self, prefix):
        """收集包含指定前缀的所有定式终点
        返回: [(path, freq, ids), ...]，其中path是完整着法序列
        """
        results = []
        prefix_tuple = tuple(prefix)
        
        for joseki_id, joseki in self._joseki_map.items():
            moves = joseki.get('moves', [])
            
            # 检查是否包含前缀
            if len(moves) < len(prefix):
                continue
            if tuple(moves[:len(prefix)]) != prefix_tuple:
                continue
            
            # 这是包含前缀的定式，记录其完整路径
            freq = joseki.get('frequency', 0)
            results.append((moves, freq, [joseki_id]))
        
        return results
    
    def _build_tree_from_paths(self, paths, main_branch=None):
        """从路径列表构建树，paths是 (path, freq, ids) 三元组列表
        main_branch: 主分支路径，用于标记主分支节点
        """
        root = {}
        main_set = set()
        if main_branch:
            # 构建主分支前缀集合，用于快速判断
            for i in range(1, len(main_branch) + 1):
                main_set.add(tuple(main_branch[:i]))
        
        for path, freq, ids in paths:
            node = root
            for i, move in enumerate(path):
                if move not in node:
                    node[move] = {'next': {}, 'freq': 0, 'ids': [], 'is_main': False}
                # 标记是否为主分支的一部分
                path_so_far = tuple(path[:i+1])
                if path_so_far in main_set:
                    node[move]['is_main'] = True
                # 只在终点设置 freq 和 ids
                if i == len(path) - 1:
                    node[move]['freq'] = freq
                    node[move]['ids'] = ids
                node = node[move]['next']
        return root
    
    def _tree_to_sgf(self, tree, depth, main_branch=None, main_depth=0, prefix_str='all'):
        """使用 sgfmill 生成 SGF 字符串"""
        from sgfmill import sgf
        
        # 创建游戏树
        game = sgf.Sgf_game(19)
        root = game.get_root()
        root.set('AP', ('WeiqiJoseki', '1.0'))
        root.set('C', f'定式树: {prefix_str}')
        
        # 转换为 sgfmill 坐标
        def to_sgfmill(move):
            if move == 'tt':
                return None
            col = ord(move[0]) - ord('a')
            row = ord(move[1]) - ord('a')
            return (18 - row, col)
        
        # 构建树结构
        def build_tree(tree, depth, main_branch, main_depth, parent_node):
            if not tree and not (main_branch and main_depth < len(main_branch)):
                return
            
            # 确定当前节点
            current_move = None
            current_node = None
            
            if main_branch and main_depth < len(main_branch):
                current_move = main_branch[main_depth]
                if tree and current_move in tree:
                    current_node = tree[current_move]
            
            if current_node is None and tree:
                items = sorted(tree.items(), key=lambda x: -x[1].get('freq', 0))
                current_move, current_node = items[0]
            
            if current_node is None:
                # 输出剩余主分支
                if main_branch and main_depth < len(main_branch):
                    node = parent_node
                    for i in range(main_depth, len(main_branch)):
                        color = 'b' if i % 2 == 0 else 'w'
                        new_node = node.new_child()
                        new_node.set_move(color, to_sgfmill(main_branch[i]))
                        node = new_node
                return
            
            # 添加当前节点
            color = 'b' if depth % 2 == 0 else 'w'
            new_node = parent_node.new_child()
            new_node.set_move(color, to_sgfmill(current_move))
            
            # 添加频率注释
            freq = current_node.get('freq', 0)
            ids = current_node.get('ids', [])
            if ids and freq > 0:
                new_node.set('C', f'出现次数:{freq}')
            
            # 处理子节点
            next_tree = current_node.get('next', {})
            main_next = None
            has_main_remaining = main_branch and main_depth + 1 < len(main_branch)
            if has_main_remaining:
                main_next = main_branch[main_depth + 1]
            
            # 收集子节点
            all_children = []
            for move, node in next_tree.items():
                is_main = (move == main_next)
                all_children.append((move, node, is_main))
            
            # 排序：主分支优先，然后按频率
            all_children.sort(key=lambda x: (-x[2], -x[1].get('freq', 0)))
            
            # 添加所有子节点为分支
            for i, (child_move, child_node, is_main) in enumerate(all_children):
                if i == 0:
                    # 第一个子节点作为主延续
                    build_tree({child_move: child_node}, depth + 1, 
                              main_branch if is_main else None,
                              main_depth + 1 if is_main else 0,
                              new_node)
                else:
                    # 其他作为分支
                    branch_node = new_node.new_child()
                    color = 'b' if (depth + 1) % 2 == 0 else 'w'
                    branch_node.set_move(color, to_sgfmill(child_move))
                    
                    child_freq = child_node.get('freq', 0)
                    child_ids = child_node.get('ids', [])
                    if child_ids and child_freq > 0:
                        branch_node.set('C', f'出现次数:{child_freq}')
                    
                    # 递归构建分支
                    build_tree(child_node.get('next', {}), depth + 2, None, 0, branch_node)
            
            # 如果子树为空但主分支还有剩余
            if not all_children and has_main_remaining:
                node = new_node
                for i in range(main_depth + 1, len(main_branch)):
                    color = 'b' if i % 2 == 0 else 'w'
                    new_child = node.new_child()
                    new_child.set_move(color, to_sgfmill(main_branch[i]))
                    node = new_child
        
        # 从根开始构建
        if tree:
            first_move = list(tree.keys())[0]
            first_node = tree[first_move]
            color = 'b' if depth % 2 == 0 else 'w'
            node = game.extend_main_sequence()
            node.set_move(color, to_sgfmill(first_move))
            
            freq = first_node.get('freq', 0)
            ids = first_node.get('ids', [])
            if ids and freq > 0:
                node.set('C', f'出现次数:{freq}')
            
            build_tree(first_node.get('next', {}), depth + 1, main_branch, main_depth + 1, node)
        
        return game.serialise().decode('utf-8')
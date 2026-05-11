#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
围棋实战选点 - 主脚本

功能：
1. 解析SGF棋谱
2. 检测棋谱格式（野狐/KataGo/星阵）
3. 提取选点题
4. 生成做题网页

使用示例：
    python3 quiz.py game.sgf
    python3 quiz.py game.sgf -o output.html
    python3 quiz.py game.sgf -t blunder --phase middle
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 导入SGF解析器
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sgf_parser import parse_sgf, coord_to_pos


# ==================== 格式适配器 ====================

class FormatAdapter:
    """格式适配器基类"""
    
    def detect(self, sgf_content: str) -> bool:
        """检测是否匹配此格式"""
        return False
    
    def parse_winrate(self, comment: str) -> Optional[Dict]:
        """解析胜率信息
        Returns: {'color': 'B'/'W', 'rate': float, 'text': str} 或 None
        """
        return None
    
    def get_name(self) -> str:
        return 'default'


class FoxWQAdapter(FormatAdapter):
    """野狐围棋适配器"""
    
    PATTERNS = ['胜率', '绝艺', '黑.*?%', '白.*?%']
    WINRATE_PATTERN = re.compile(r'([黑白]).*?(\d+\.?\d*)%')
    
    def detect(self, sgf_content: str) -> bool:
        for pattern in self.PATTERNS:
            if re.search(pattern, sgf_content):
                return True
        return False
    
    def parse_winrate(self, comment: str) -> Optional[Dict]:
        match = self.WINRATE_PATTERN.search(comment)
        if match:
            color_cn = match.group(1)
            color = 'B' if color_cn == '黑' else 'W'
            rate = float(match.group(2))
            return {'color': color, 'rate': rate, 'text': f"{color_cn}{rate}%"}
        return None
    
    def get_name(self) -> str:
        return 'foxwq'


class KataGoAdapter(FormatAdapter):
    """KataGo适配器"""
    
    PATTERNS = ['KataGo', 'winrate', r'B \d+', r'W \d+']
    WINRATE_PATTERN = re.compile(r'([BW])\s+(\d+\.?\d*)%')
    
    def detect(self, sgf_content: str) -> bool:
        for pattern in self.PATTERNS:
            if re.search(pattern, sgf_content):
                return True
        return False
    
    def parse_winrate(self, comment: str) -> Optional[Dict]:
        match = self.WINRATE_PATTERN.search(comment)
        if match:
            color = match.group(1)
            rate = float(match.group(2))
            return {'color': color, 'rate': rate, 'text': f"{color} {rate}%"}
        return None
    
    def get_name(self) -> str:
        return 'katago'


class XingZhenAdapter(FormatAdapter):
    """星阵适配器"""
    
    PATTERNS = ['星阵', '推荐', '胜率']
    WINRATE_PATTERN = re.compile(r'胜率[:\s]*([黑白])\s*(\d+\.?\d*)%')
    
    def detect(self, sgf_content: str) -> bool:
        for pattern in self.PATTERNS:
            if re.search(pattern, sgf_content):
                return True
        return False
    
    def parse_winrate(self, comment: str) -> Optional[Dict]:
        match = self.WINRATE_PATTERN.search(comment)
        if match:
            color_cn = match.group(1)
            color = 'B' if color_cn == '黑' else 'W'
            rate = float(match.group(2))
            return {'color': color, 'rate': rate, 'text': f"{color_cn}{rate}%"}
        return None
    
    def get_name(self) -> str:
        return 'xingzhen'


# 格式适配器注册表
FORMAT_ADAPTERS = [
    FoxWQAdapter(),
    KataGoAdapter(),
    XingZhenAdapter(),
]


def detect_format(sgf_content: str) -> str:
    """检测棋谱格式"""
    for adapter in FORMAT_ADAPTERS:
        if adapter.detect(sgf_content):
            return adapter.get_name()
    return 'default'


def get_adapter(format_type: str) -> FormatAdapter:
    """获取指定格式的适配器"""
    for adapter in FORMAT_ADAPTERS:
        if adapter.get_name() == format_type:
            return adapter
    return FormatAdapter()


# ==================== 题目提取 ====================

class Problem:
    """单个选点题"""
    
    def __init__(self, move_num: int, position: List[Dict], variations: List[Dict]):
        self.move_num = move_num  # 题目标记的手数
        self.position = position  # 题目前的历史局面着法
        self.variations = variations  # 变化图（选项）
        self.phase = self._classify_phase(move_num)
        self.difficulty = self._classify_difficulty(variations)
        self.is_blunder = self._check_blunder(variations)
    
    def _classify_phase(self, move_num: int) -> str:
        """分类题目阶段"""
        if move_num <= 60:
            return 'layout'  # 布局
        elif move_num <= 180:
            return 'middle'  # 中盘
        else:
            return 'endgame'  # 官子
    
    def _classify_difficulty(self, variations: List[Dict]) -> str:
        """分类难度"""
        if len(variations) < 2:
            return 'easy'
        
        rates = []
        for v in variations:
            rate_info = self._parse_var_winrate(v)
            if rate_info:
                rates.append(rate_info['rate'])
        
        if len(rates) < 2:
            return 'easy'
        
        rates.sort(reverse=True)
        diff = rates[0] - rates[1]
        
        if diff > 15:
            return 'easy'
        elif diff > 5:
            return 'medium'
        else:
            return 'hard'
    
    def _check_blunder(self, variations: List[Dict]) -> bool:
        """检查是否为恶手题"""
        if len(variations) < 2:
            return False
        
        rates = []
        for v in variations:
            rate_info = self._parse_var_winrate(v)
            if rate_info:
                rates.append(rate_info['rate'])
        
        if len(rates) < 2:
            return False
        
        rates.sort(reverse=True)
        return (rates[0] - rates[1]) > 20
    
    def _parse_var_winrate(self, variation: Dict) -> Optional[Dict]:
        """解析变化的胜率"""
        comment = variation.get('comment', '')
        # 尝试各种格式
        patterns = [
            r'([黑白]).*?(\d+\.?\d*)%',
            r'([BW])\s+(\d+\.?\d*)%',
            r'胜率[:\s]*([黑白])\s*(\d+\.?\d*)%',
        ]
        for pattern in patterns:
            match = re.search(pattern, comment)
            if match:
                color_str = match.group(1)
                rate = float(match.group(2))
                color = 'B' if color_str in ['黑', 'B'] else 'W'
                return {'color': color, 'rate': rate}
        return None


def deduplicate_variations(variations: List[Dict], format_type: str) -> List[Dict]:
    """变化去重 - 第一步相同的变化只保留胜率最高的"""
    seen = {}
    adapter = get_adapter(format_type)
    
    for var in variations:
        if not var.get('moves'):
            continue
        
        first_coord = var['moves'][0]['coord']
        
        # 解析胜率
        rate = 0
        comment = var.get('comment', '')
        winrate_info = adapter.parse_winrate(comment)
        if winrate_info:
            rate = winrate_info['rate']
        else:
            # 尝试通用解析
            match = re.search(r'(\d+\.?\d*)%', comment)
            if match:
                rate = float(match.group(1))
        
        if first_coord not in seen or rate > seen[first_coord]['rate']:
            seen[first_coord] = {
                'variation': var,
                'rate': rate
            }
    
    return [v['variation'] for v in seen.values()]


def extract_problems(moves: List[Dict], variations: Dict, format_type: str = 'default',
                     problem_type: Optional[str] = None, phase: Optional[str] = None) -> List[Problem]:
    """
    提取选点题
    
    Args:
        moves: 主分支着法
        variations: 变化图字典 {move_num: [variations]}
        format_type: 棋谱格式
        problem_type: 题目类型筛选 (blunder/easy/medium/hard)
        phase: 阶段筛选 (layout/middle/endgame)
    
    Returns:
        Problem对象列表
    """
    problems = []
    
    for move_num, vars_at_move in variations.items():
        if len(vars_at_move) < 2:
            continue  # 至少需要两个选项
        
        # 去重
        deduped = deduplicate_variations(vars_at_move, format_type)
        if len(deduped) < 2:
            continue
        
        # 截取历史局面
        position = moves[:move_num]
        
        problem = Problem(move_num, position, deduped)
        
        # 应用筛选
        if problem_type:
            if problem_type == 'blunder' and not problem.is_blunder:
                continue
            elif problem_type in ['easy', 'medium', 'hard'] and problem.difficulty != problem_type:
                continue
        
        if phase and problem.phase != phase:
            continue
        
        problems.append(problem)
    
    # 按手数排序
    problems.sort(key=lambda p: p.move_num)
    return problems


# ==================== HTML生成 ====================

def generate_quiz_html(problems: List[Problem], game_info: Dict, sgf_content: str,
                       output_path: Optional[str] = None) -> str:
    """生成做题网页"""
    
    if not problems:
        print("警告: 没有提取到选点题")
        return ""
    
    # 读取模板
    template_path = Path(__file__).parent.parent / 'templates' / 'quiz.html'
    if not template_path.exists():
        print(f"错误: 模板文件不存在 {template_path}")
        return ""
    
    template = template_path.read_text(encoding='utf-8')
    
    # 准备题目数据
    problems_data = []
    for i, p in enumerate(problems):
        # 为每个变化分配选项字母
        options = []
        letters = ['A', 'B', 'C', 'D', 'E', 'F']
        
        # 按胜率排序，最高的为正确答案
        sorted_vars = sorted(p.variations, 
                           key=lambda v: _extract_rate(v.get('comment', '')), 
                           reverse=True)
        
        for j, var in enumerate(sorted_vars[:6]):  # 最多6个选项
            letter = letters[j] if j < len(letters) else f"{j+1}"
            first_move = var['moves'][0] if var.get('moves') else None
            
            options.append({
                'letter': letter,
                'coord': first_move['coord'] if first_move else '',
                'color': first_move['color'] if first_move else 'B',
                'winrate': var.get('winRate', ''),
                'comment': var.get('comment', ''),
                'moves': var.get('moves', []),
                'is_correct': j == 0  # 胜率最高的是正确答案
            })
        
        problems_data.append({
            'index': i,
            'move_num': p.move_num,
            'phase': p.phase,
            'difficulty': p.difficulty,
            'is_blunder': p.is_blunder,
            'position': p.position,
            'options': options
        })
    
    # 准备模板变量
    board_size = int(game_info.get('board_size', 19))
    handicap_stones = game_info.get('handicap_stones', [])
    
    template_vars = {
        'GAME_NAME': game_info.get('game_name', '围棋实战选点'),
        'GAME_TITLE': f"{game_info.get('black', '黑棋')} vs {game_info.get('white', '白棋')}",
        'GAME_INFO': f"{game_info.get('date', '')} {game_info.get('result', '')}",
        'BLACK_NAME': game_info.get('black', '黑棋'),
        'WHITE_NAME': game_info.get('white', '白棋'),
        'BOARD_SIZE': board_size,
        'HANDICAP_STONES': json.dumps(handicap_stones),
        'HANDICAP_COUNT': len(handicap_stones),
        'PROBLEMS_JSON': json.dumps(problems_data, ensure_ascii=False),
        'SGF_DATA': sgf_content.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$'),
        'TOTAL_PROBLEMS': len(problems_data),
    }
    
    # 替换模板变量
    html = template
    for key, value in template_vars.items():
        placeholder = '{{' + key + '}}'
        html = html.replace(placeholder, str(value))
    
    # 写入文件
    if output_path:
        output_path = Path(output_path)
        output_path.write_text(html, encoding='utf-8')
        print(f"已生成做题网页: {output_path.absolute()}")
    
    return html


def _extract_rate(comment: str) -> float:
    """从注释中提取胜率数值"""
    match = re.search(r'(\d+\.?\d*)%', comment)
    if match:
        return float(match.group(1))
    return 0


# ==================== 命令行入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description='围棋实战选点 - 从SGF棋谱中提取选点题，生成交互式做题网页',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 quiz.py game.sgf                    # 生成全部选点题
  python3 quiz.py game.sgf -o quiz.html       # 指定输出文件
  python3 quiz.py game.sgf -t blunder         # 只生成恶手题
  python3 quiz.py game.sgf --phase middle     # 只生成中盘题
  python3 quiz.py game.sgf -t easy --phase layout  # 布局阶段的简单题
        """
    )
    
    parser.add_argument('sgf', help='输入SGF文件路径')
    parser.add_argument('-o', '--output', help='输出HTML文件路径（默认: 输入文件名.html）')
    parser.add_argument('-t', '--type', 
                       choices=['blunder', 'easy', 'medium', 'hard'],
                       help='题目类型筛选')
    parser.add_argument('--phase',
                       choices=['layout', 'middle', 'endgame'],
                       help='阶段筛选（布局/中盘/官子）')
    
    args = parser.parse_args()
    
    # 读取SGF文件
    sgf_path = Path(args.sgf)
    if not sgf_path.exists():
        print(f"错误: 文件不存在 {sgf_path}")
        sys.exit(1)
    
    sgf_content = sgf_path.read_text(encoding='utf-8')
    
    # 解析SGF
    print(f"正在解析: {sgf_path}")
    result = parse_sgf(sgf_content)
    moves = result['moves']
    variations = result['variations']
    game_info = result['game_info']
    errors = result.get('errors', [])
    
    if errors:
        print(f"解析警告: {errors}")
    
    print(f"棋局: {game_info.get('black', '黑棋')} vs {game_info.get('white', '白棋')}")
    print(f"主分支手数: {len(moves)}")
    print(f"变化图数量: {sum(len(v) for v in variations.values())}")
    
    # 检测格式
    format_type = detect_format(sgf_content)
    adapter = get_adapter(format_type)
    print(f"检测到的格式: {format_type}")
    
    # 提取题目
    print("\n正在提取选点题...")
    problems = extract_problems(moves, variations, format_type, args.type, args.phase)
    print(f"提取到 {len(problems)} 道题目")
    
    if not problems:
        print("未找到符合条件的选点题，请检查棋谱是否包含AI分析数据")
        sys.exit(0)
    
    # 统计信息
    phase_counts = {'layout': 0, 'middle': 0, 'endgame': 0}
    difficulty_counts = {'easy': 0, 'medium': 0, 'hard': 0}
    blunder_count = 0
    
    for p in problems:
        phase_counts[p.phase] = phase_counts.get(p.phase, 0) + 1
        difficulty_counts[p.difficulty] = difficulty_counts.get(p.difficulty, 0) + 1
        if p.is_blunder:
            blunder_count += 1
    
    print(f"  - 布局: {phase_counts['layout']}, 中盘: {phase_counts['middle']}, 官子: {phase_counts['endgame']}")
    print(f"  - 简单: {difficulty_counts['easy']}, 中等: {difficulty_counts['medium']}, 困难: {difficulty_counts['hard']}")
    print(f"  - 恶手题: {blunder_count}")
    
    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        output_path = sgf_path.with_suffix('.html')
    
    # 生成HTML
    print(f"\n正在生成做题网页...")
    generate_quiz_html(problems, game_info, sgf_content, output_path)


if __name__ == '__main__':
    main()

"""
围棋实战选点 - 等级判定模块（三级划分）

从棋谱段位信息判定整局等级：职业/高段/普通
"""
import re
from typing import Dict, Optional

# 等级映射表：内部标识 -> 显示名称
# 三级划分：职业 / 高段 / 普通
LEVEL_MAP = {
    'pro': '职业',      # 职业棋手（P段/职业/九段...初段）
    'high': '高段',     # 业余5段以上（野狐5d+）
    'normal': '普通'    # 业余1-4段、级位、未知
}


def parse_rank(rank_str: str) -> Optional[str]:
    """
    解析段位字符串，返回内部等级标识
    
    三级划分：
    - 职业: 职业/九段...初段/P段
    - 高段: 业余5段以上（野狐5d+）
    - 普通: 业余1-4段、级位、未知
    """
    if not rank_str:
        return None
    
    rank_str = str(rank_str).strip()
    
    # 职业棋手
    if '职业' in rank_str:
        return 'pro'
    if re.match(r'[九八七六五四三二初]段$', rank_str):
        return 'pro'
    # 野狐格式：P9段（P表示职业 Professional）
    if re.match(r'P\d+段$', rank_str, re.IGNORECASE):
        return 'pro'
    
    # 业余段位 (支持 "x段" 或 "xd" 格式，1-9段有效)
    match = re.match(r'(\d+)[段d]$', rank_str, re.IGNORECASE)
    if match:
        d = int(match.group(1))
        if d < 1 or d > 9:
            return None       # 超出有效段位范围
        if d >= 5:
            return 'high'     # 高段：5-9段
        else:
            return 'normal'   # 普通：1-4段
    
    # 级位归入普通
    if re.match(r'\d+[级kK]$', rank_str):
        return 'normal'
    
    return None


def determine_game_level(game_info: Dict) -> str:
    """
    判定整局棋的等级
    
    规则：取双方段位中较高的一方作为整局等级
    """
    b = parse_rank(game_info.get('black_rank', ''))
    w = parse_rank(game_info.get('white_rank', ''))
    
    levels = [l for l in [b, w] if l]
    if not levels:
        return LEVEL_MAP['normal']  # 无段位信息归入普通
    
    # 优先级顺序：职业 > 高段 > 普通
    priority = ['pro', 'high', 'normal']
    for p in priority:
        if p in levels:
            return LEVEL_MAP[p]
    
    return LEVEL_MAP['normal']

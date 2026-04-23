"""
段位解析单元测试（三级划分）

测试 parse_rank 函数对各种段位格式的解析
"""
import pytest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from game_level import parse_rank


class TestParseRank:
    """测试段位解析功能 - 三级划分"""
    
    def test_pro_rank(self):
        """职业棋手识别"""
        assert parse_rank('职业') == 'pro'
        assert parse_rank('九段') == 'pro'
        assert parse_rank('初段') == 'pro'
    
    def test_foxwq_pro_format(self):
        """野狐职业格式识别（Px段）"""
        assert parse_rank('P9段') == 'pro'
        assert parse_rank('p9段') == 'pro'
    
    def test_high_rank(self):
        """高段识别（5段以上）"""
        assert parse_rank('9段') == 'high'
        assert parse_rank('8段') == 'high'
        assert parse_rank('5段') == 'high'
        assert parse_rank('5d') == 'high'
    
    def test_normal_rank(self):
        """普通识别（1-4段）"""
        assert parse_rank('4段') == 'normal'
        assert parse_rank('1段') == 'normal'
        assert parse_rank('1d') == 'normal'
    
    def test_kyu_rank(self):
        """级位归入普通"""
        assert parse_rank('1级') == 'normal'
        assert parse_rank('5k') == 'normal'
    
    def test_unknown_rank(self):
        """无效段位返回None"""
        assert parse_rank('') is None
        assert parse_rank(None) is None
        assert parse_rank('10段') is None  # 超出范围
    
    def test_whitespace_handling(self):
        """空格处理"""
        assert parse_rank(' 九段 ') == 'pro'
        assert parse_rank('  5段  ') == 'high'
        assert parse_rank('\t2段\n') == 'normal'

"""
整局等级判定测试（三级划分）

测试 determine_game_level 函数对整局棋等级的判定
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from game_level import determine_game_level


class TestGameLevel:
    """测试整局等级判定功能 - 三级划分"""
    
    def test_pro_vs_pro(self):
        """职业对职业 -> 职业"""
        info = {'black_rank': '九段', 'white_rank': '职业'}
        assert determine_game_level(info) == '职业'
    
    def test_pro_vs_high(self):
        """职业对高段 -> 职业"""
        info = {'black_rank': '职业', 'white_rank': '6段'}
        assert determine_game_level(info) == '职业'
    
    def test_pro_vs_normal(self):
        """职业对普通 -> 职业"""
        info = {'black_rank': 'P9段', 'white_rank': '3段'}
        assert determine_game_level(info) == '职业'
    
    def test_high_vs_normal(self):
        """高段对普通 -> 高段"""
        info = {'black_rank': '5段', 'white_rank': '3段'}
        assert determine_game_level(info) == '高段'
    
    def test_high_vs_high(self):
        """高段对高段 -> 高段"""
        info = {'black_rank': '9段', 'white_rank': '5d'}
        assert determine_game_level(info) == '高段'
    
    def test_normal_vs_normal(self):
        """普通对普通 -> 普通"""
        info = {'black_rank': '4段', 'white_rank': '1段'}
        assert determine_game_level(info) == '普通'
    
    def test_normal_vs_kyu(self):
        """普通对级位 -> 普通"""
        info = {'black_rank': '2段', 'white_rank': '1级'}
        assert determine_game_level(info) == '普通'
    
    def test_kyu_vs_kyu(self):
        """级位对级位 -> 普通"""
        info = {'black_rank': '3级', 'white_rank': '5k'}
        assert determine_game_level(info) == '普通'
    
    def test_no_rank(self):
        """无段位信息 -> 普通"""
        info = {'black_rank': '', 'white_rank': ''}
        assert determine_game_level(info) == '普通'
    
    def test_only_one_rank(self):
        """只有一方有段位"""
        info = {'black_rank': '6段', 'white_rank': ''}
        assert determine_game_level(info) == '高段'
        
        info = {'black_rank': '', 'white_rank': '2段'}
        assert determine_game_level(info) == '普通'
    
    def test_invalid_rank(self):
        """无效段位 -> 普通"""
        info = {'black_rank': 'Invalid', 'white_rank': 'Unknown'}
        assert determine_game_level(info) == '普通'

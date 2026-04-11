#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weiqi-db 核心功能测试
"""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path

# 添加 weiqi-db 脚本路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-db/scripts')

import db

# 测试数据路径
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


@pytest.fixture
def temp_db():
    """使用临时数据库进行测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 保存原始路径
        original_db_path = db.DB_PATH
        original_db_dir = db.DB_DIR
        
        # 设置临时路径
        temp_db_dir = Path(tmpdir) / ".weiqi-db"
        temp_db_dir.mkdir(parents=True, exist_ok=True)
        temp_db_path = temp_db_dir / "database.json"
        
        db.DB_PATH = temp_db_path
        db.DB_DIR = temp_db_dir
        
        yield temp_db_path
        
        # 恢复原始路径
        db.DB_PATH = original_db_path
        db.DB_DIR = original_db_dir


@pytest.fixture
def sample1_path():
    return FIXTURES_DIR / 'sample1.sgf'


@pytest.fixture
def sample2_path():
    return FIXTURES_DIR / 'sample2.sgf'


class TestInitClear:
    """测试初始化和清空功能"""
    
    def test_init_creates_database(self, temp_db):
        """测试初始化创建数据库"""
        from tinydb import TinyDB
        
        # 初始化数据库
        database = db.ensure_db()
        assert isinstance(database, TinyDB)
        assert temp_db.exists()
    
    def test_clear_removes_all_data(self, temp_db):
        """测试清空数据库"""
        # 先添加一些数据
        database = db.ensure_db()
        table = database.table('games')
        table.insert({'id': 'test1', 'black': 'Test'})
        
        # 清空
        result = db.cmd_clear(type('Args', (), {})())
        assert result['success'] is True
        
        # 验证数据已清空
        database = db.ensure_db()
        table = database.table('games')
        assert len(table.all()) == 0


class TestAddSingleFile:
    """测试添加单文件功能"""
    
    def test_add_single_file_success(self, temp_db, sample1_path):
        """测试成功添加单个文件"""
        args = type('Args', (), {
            'file': str(sample1_path),
            'dir': None,
            'black': None,
            'white': None,
            'black_rank': None,
            'white_rank': None,
            'date': None,
            'event': None,
            'result': None,
            'komi': None,
            'tag': None,
            'conflict': 'skip'
        })()
        
        result = db.cmd_add(args)
        
        assert result['success'] is True
        assert result['added'] == 1
        assert result['total'] == 1
        
        # 验证数据已写入
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        assert len(games) == 1
        assert games[0]['black'] == '柯洁'
        assert games[0]['white'] == '申真谞'
        assert games[0]['date'] == '2024-01-15'
    
    def test_add_nonexistent_file(self, temp_db):
        """测试添加不存在的文件"""
        args = type('Args', (), {
            'file': '/nonexistent/path.sgf',
            'dir': None,
            'black': None,
            'white': None,
            'black_rank': None,
            'white_rank': None,
            'date': None,
            'event': None,
            'result': None,
            'komi': None,
            'tag': None,
            'conflict': 'skip'
        })()
        
        result = db.cmd_add(args)
        
        assert result['success'] is False
        assert 'error' in result


class TestAddDirectory:
    """测试添加目录功能"""
    
    def test_add_directory(self, temp_db):
        """测试添加整个目录"""
        args = type('Args', (), {
            'file': None,
            'dir': str(FIXTURES_DIR),
            'black': None,
            'white': None,
            'black_rank': None,
            'white_rank': None,
            'date': None,
            'event': None,
            'result': None,
            'komi': None,
            'tag': None,
            'conflict': 'skip'
        })()
        
        result = db.cmd_add(args)
        
        assert result['success'] is True
        assert result['added'] >= 2  # 至少添加2个不同文件
        
        # 验证数据库中有记录
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        assert len(games) >= 2


class TestAddWithMetadataOverride:
    """测试元数据覆盖功能"""
    
    def test_override_metadata(self, temp_db, sample1_path):
        """测试覆盖元数据"""
        args = type('Args', (), {
            'file': str(sample1_path),
            'dir': None,
            'black': 'Override黑棋',
            'white': 'Override白棋',
            'black_rank': '5d',
            'white_rank': '3d',
            'date': '2025-12-31',
            'event': '测试赛事',
            'result': 'W+R',
            'komi': '7.5',
            'tag': ['测试标签'],
            'conflict': 'skip'
        })()
        
        result = db.cmd_add(args)
        
        assert result['success'] is True
        assert result['added'] == 1
        
        # 验证覆盖后的元数据
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        assert len(games) == 1
        assert games[0]['black'] == 'Override黑棋'
        assert games[0]['white'] == 'Override白棋'
        assert games[0]['black_rank'] == '5d'
        assert games[0]['white_rank'] == '3d'
        assert games[0]['date'] == '2025-12-31'
        assert games[0]['event'] == '测试赛事'
        assert games[0]['result'] == 'W+R'
        assert games[0]['komi'] == '7.5'
        assert games[0]['tags'] == ['测试标签']


class TestQueryBasic:
    """测试基本查询功能"""
    
    def test_list_all_games(self, temp_db, sample1_path, sample2_path):
        """测试列出所有棋谱"""
        # 先添加两个棋谱
        args = type('Args', (), {
            'file': None,
            'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 查询所有
        list_args = type('Args', (), {'limit': None})()
        result = db.cmd_list(list_args)
        
        assert result['success'] is True
        assert result['count'] >= 2
        assert result['total'] >= 2
        
        # 验证返回的数据不包含sgf和hash
        for game in result['games']:
            assert 'sgf' not in game
            assert 'hash' not in game
    
    def test_query_by_exact_match(self, temp_db, sample1_path, sample2_path):
        """测试精确匹配查询"""
        # 添加棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 按黑棋名查询
        query_args = type('Args', (), {
            'where': '{"black": "柯洁"}',
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        assert result['count'] >= 1
        
        # 验证结果
        for game in result['games']:
            assert game['black'] == '柯洁'


class TestQueryAdvanced:
    """测试高级查询功能"""
    
    def test_fuzzy_query(self, temp_db, sample1_path, sample2_path):
        """测试模糊查询"""
        # 添加棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 模糊查询赛事（包含"LG杯"）
        query_args = type('Args', (), {
            'where': '{"event~": "LG杯"}',
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        # 至少有一个匹配
        assert result['count'] >= 1
    
    def test_range_query(self, temp_db, sample1_path, sample2_path):
        """测试范围查询"""
        # 添加棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 按日期范围查询（>= 2024-01-01）
        query_args = type('Args', (), {
            'where': '{"date>=": "2024-01-01"}',
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        # 应该有2024年的记录
        assert result['count'] >= 1
    
    def test_combined_query(self, temp_db, sample1_path, sample2_path):
        """测试组合查询"""
        # 添加棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 使用$and组合条件
        query_args = type('Args', (), {
            'where': '{"$and": [{"black": "柯洁"}, {"date>=": "2024-01-01"}]}',
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        # 验证结果满足所有条件
        for game in result['games']:
            assert game['black'] == '柯洁'
    
    def test_keyword_search(self, temp_db, sample1_path):
        """测试关键词搜索"""
        # 添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 关键词搜索
        query_args = type('Args', (), {
            'where': '{"keyword": "柯洁"}',
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        assert result['count'] == 1


class TestUpdateDelete:
    """测试更新和删除功能"""
    
    def test_update_metadata(self, temp_db, sample1_path):
        """测试更新元数据"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        
        # 获取添加的ID
        game_id = add_result['results'][0]['id']
        
        # 更新元数据
        update_args = type('Args', (), {
            'id': game_id,
            'set': '{"event": "更新后的赛事", "black_rank": "10d"}'
        })()
        result = db.cmd_update(update_args)
        
        assert result['success'] is True
        assert result['id'] == game_id
        
        # 验证更新
        database = db.ensure_db()
        table = database.table('games')
        game = table.get(db.Query().id == game_id)
        assert game['event'] == '更新后的赛事'
        assert game['black_rank'] == '10d'
    
    def test_delete_game(self, temp_db, sample1_path):
        """测试删除棋谱"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 删除
        delete_args = type('Args', (), {'id': game_id})()
        result = db.cmd_delete(delete_args)
        
        assert result['success'] is True
        assert result['deleted'] is True
        
        # 验证已删除
        database = db.ensure_db()
        table = database.table('games')
        assert table.get(db.Query().id == game_id) is None
    
    def test_update_nonexistent_id(self, temp_db):
        """测试更新不存在的ID"""
        update_args = type('Args', (), {
            'id': 'nonexistent123',
            'set': '{"event": "测试"}'
        })()
        result = db.cmd_update(update_args)
        
        assert result['success'] is False
        assert 'error' in result


class TestTagManagement:
    """测试标签管理功能"""
    
    def test_add_tag(self, temp_db, sample1_path):
        """测试添加标签"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 添加标签
        tag_args = type('Args', (), {'id': game_id, 'add': '重要', 'remove': None})()
        result = db.cmd_tag(tag_args)
        
        assert result['success'] is True
        assert result['action'] == 'add_tag'
        
        # 验证标签已添加
        database = db.ensure_db()
        table = database.table('games')
        game = table.get(db.Query().id == game_id)
        assert '重要' in game['tags']
    
    def test_remove_tag(self, temp_db, sample1_path):
        """测试移除标签"""
        # 先添加带标签的棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': ['标签1', '标签2'], 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 移除标签
        tag_args = type('Args', (), {'id': game_id, 'add': None, 'remove': '标签1'})()
        result = db.cmd_tag(tag_args)
        
        assert result['success'] is True
        assert result['action'] == 'remove_tag'
        
        # 验证标签已移除
        database = db.ensure_db()
        table = database.table('games')
        game = table.get(db.Query().id == game_id)
        assert '标签1' not in game['tags']
        assert '标签2' in game['tags']
    
    def test_list_tags(self, temp_db, sample1_path):
        """测试列出标签"""
        # 先添加带标签的棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': ['标签A', '标签B'], 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 列出标签
        tag_args = type('Args', (), {'id': game_id, 'add': None, 'remove': None})()
        result = db.cmd_tag(tag_args)
        
        assert result['success'] is True
        assert '标签A' in result['tags']
        assert '标签B' in result['tags']


class TestGetCommand:
    """测试获取单个棋谱功能 (get 命令)"""
    
    def test_get_game_success(self, temp_db, sample1_path):
        """测试成功获取单个棋谱（含SGF）"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 获取棋谱
        get_args = type('Args', (), {'id': game_id})()
        result = db.cmd_get(get_args)
        
        assert result['success'] is True
        assert result['game']['id'] == game_id
        assert result['game']['black'] == '柯洁'
        assert result['game']['white'] == '申真谞'
        # 验证包含SGF字段
        assert 'sgf' in result['game']
        assert 'sgf_content' in result['game'] or len(result['game']['sgf']) > 0
    
    def test_get_game_not_found(self, temp_db):
        """测试获取不存在的棋谱ID"""
        get_args = type('Args', (), {'id': 'nonexistent123456'})()
        result = db.cmd_get(get_args)
        
        assert result['success'] is False
        assert 'error' in result
        assert '未找到ID' in result['error']
    
    def test_get_game_without_id(self, temp_db):
        """测试不指定ID时获取棋谱"""
        get_args = type('Args', (), {'id': None})()
        result = db.cmd_get(get_args)
        
        assert result['success'] is False
        assert 'error' in result
        assert '需要指定 --id' in result['error']
    
    def test_get_returns_full_game_data(self, temp_db, sample1_path):
        """测试获取的棋谱包含完整数据（包括SGF）"""
        # 添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': ['测试标签'], 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 获取棋谱
        get_args = type('Args', (), {'id': game_id})()
        result = db.cmd_get(get_args)
        
        assert result['success'] is True
        game = result['game']
        
        # 验证所有字段都存在
        assert 'id' in game
        assert 'sgf' in game
        assert 'hash' in game
        assert 'black' in game
        assert 'white' in game
        assert 'black_rank' in game
        assert 'white_rank' in game
        assert 'date' in game
        assert 'event' in game
        assert 'result' in game
        assert 'komi' in game
        assert 'handicap' in game
        assert 'movenum' in game
        assert 'tags' in game
        assert 'created' in game
        
        # 验证标签正确
        assert '测试标签' in game['tags']
        
        # 验证SGF内容不为空
        assert len(game['sgf']) > 0
        assert game['sgf'].startswith('(;')


class TestStats:
    """测试统计功能"""
    
    def test_stats_basic(self, temp_db, sample1_path, sample2_path):
        """测试基本统计"""
        # 添加两个棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': ['测试'], 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 获取统计
        result = db.cmd_stats(type('Args', (), {})())
        
        assert result['success'] is True
        assert result['total_games'] >= 2
        
        # 验证有top_players
        assert 'top_players' in result
        
        # 验证有top_tags
        assert 'top_tags' in result
        assert any(tag[0] == '测试' for tag in result['top_tags'])
        
        # 验证有date_range
        assert 'date_range' in result
    
    def test_stats_empty_database(self, temp_db):
        """测试空数据库统计"""
        result = db.cmd_stats(type('Args', (), {})())
        
        assert result['success'] is True
        assert result['total_games'] == 0
        assert result['top_players'] == []
        assert result['top_tags'] == []

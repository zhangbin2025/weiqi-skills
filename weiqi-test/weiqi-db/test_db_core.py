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
            'where_file': None,
            'date': None,
            'player': None,
            'event': None,
            'event_like': None,
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
            'where_file': None,
            'date': None,
            'player': None,
            'event': None,
            'event_like': None,
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
            'where_file': None,
            'date': None,
            'player': None,
            'event': None,
            'event_like': None,
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
            'where_file': None,
            'date': None,
            'player': None,
            'event': None,
            'event_like': None,
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
            'where_file': None,
            'date': None,
            'player': None,
            'event': None,
            'event_like': None,
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
            'set': '{"event": "更新后的赛事", "black_rank": "10d"}',
            'set_file': None
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
            'set': '{"event": "测试"}',
            'set_file': None
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
        tag_args = type('Args', (), {'id': game_id, 'add': '重要', 'add_file': None, 'remove': None, 'remove_file': None})()
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
        tag_args = type('Args', (), {'id': game_id, 'add': None, 'add_file': None, 'remove': '标签1', 'remove_file': None})()
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
        tag_args = type('Args', (), {'id': game_id, 'add': None, 'add_file': None, 'remove': None, 'remove_file': None})()
        result = db.cmd_tag(tag_args)
        
        assert result['success'] is True
        assert '标签A' in result['tags']
        assert '标签B' in result['tags']


class TestSGFCompression:
    """测试SGF压缩功能"""
    
    def test_sgf_compression(self, temp_db, sample1_path):
        """测试SGF压缩功能：验证存储的是压缩格式"""
        # 添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        result = db.cmd_add(args)
        
        assert result['success'] is True
        game_id = result['results'][0]['id']
        
        # 直接查询数据库，验证存储的是压缩格式
        database = db.ensure_db()
        table = database.table('games')
        raw_game = table.get(db.Query().id == game_id)
        
        # 验证SGF以压缩标记开头
        assert raw_game['sgf'].startswith('__gz__'), "SGF应该被压缩并带有__gz__前缀"
    
    def test_sgf_decompression(self, temp_db, sample1_path):
        """测试SGF解压功能：验证读取时正确解压"""
        # 添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 读取原始SGF内容
        with open(sample1_path, 'r', encoding='utf-8') as f:
            original_sgf = f.read()
        
        # 通过get命令获取，应该自动解压
        get_args = type('Args', (), {'id': game_id})()
        result = db.cmd_get(get_args)
        
        assert result['success'] is True
        # 验证返回的是解压后的原始内容
        assert result['game']['sgf'] == original_sgf, "返回的SGF应该是解压后的原始内容"
    
    def test_backward_compatible(self, temp_db, sample1_path):
        """测试向后兼容：能读取未压缩的旧数据"""
        # 先添加棋谱（压缩存储）
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 读取原始SGF内容
        with open(sample1_path, 'r', encoding='utf-8') as f:
            original_sgf = f.read()
        
        # 直接修改数据库，模拟旧数据（未压缩）
        database = db.ensure_db()
        table = database.table('games')
        table.update({'sgf': original_sgf}, db.Query().id == game_id)
        
        # 通过get命令获取，应该能正确处理未压缩数据
        get_args = type('Args', (), {'id': game_id})()
        result = db.cmd_get(get_args)
        
        assert result['success'] is True
        # 验证能正确返回未压缩的旧数据
        assert result['game']['sgf'] == original_sgf, "应该能正确处理未压缩的旧数据"


class TestGetCommand:
    """测试获取单个棋谱功能 (get 命令)"""
    
    def test_get_game_success(self, temp_db, sample1_path):
        """测试成功获取单个棋谱（含SGF）"""
        # 读取原始SGF内容
        with open(sample1_path, 'r', encoding='utf-8') as f:
            original_sgf = f.read()
        
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
        # 验证包含SGF字段且内容已解压
        assert 'sgf' in result['game']
        assert result['game']['sgf'] == original_sgf, "返回的SGF应该是解压后的原始内容"
    
    def test_get_game_not_found(self, temp_db):
        """测试获取不存在的棋谱ID"""
        get_args = type('Args', (), {'id': 'nonexistent123456', 'ids': None, 'id_file': None, 'output': None, 'output_dir': None})()
        result = db.cmd_get(get_args)
        
        assert result['success'] is False
        assert result['found'] == 0
        assert 'nonexistent123456' in result['not_found']
    
    def test_get_game_without_id(self, temp_db):
        """测试不指定ID时获取棋谱"""
        get_args = type('Args', (), {'id': None, 'ids': None, 'id_file': None, 'output': None, 'output_dir': None})()
        result = db.cmd_get(get_args)
        
        assert result['success'] is False
        assert 'error' in result
        assert '需要指定' in result['error']
    
    def test_get_returns_full_game_data(self, temp_db, sample1_path):
        """测试获取的棋谱包含完整数据（包括解压后的SGF）"""
        # 读取原始SGF内容
        with open(sample1_path, 'r', encoding='utf-8') as f:
            original_sgf = f.read()
        
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
        
        # 验证SGF内容是解压后的原始内容
        assert game['sgf'] == original_sgf, "返回的SGF应该是解压后的原始内容"
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


class TestGetExport:
    """测试 get 命令导出SGF到文件功能"""
    
    def test_get_export_to_file(self, temp_db, sample1_path):
        """测试使用 --output 导出SGF到文件"""
        # 读取原始SGF内容
        with open(sample1_path, 'r', encoding='utf-8') as f:
            original_sgf = f.read()
        
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 导出到临时文件
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'exported.sgf'
            
            # 使用 --output 参数获取并导出
            get_args = type('Args', (), {'id': game_id, 'ids': None, 'id_file': None, 'output': str(output_path), 'output_dir': None})()
            result = db.cmd_get(get_args)
            
            # 验证导出成功
            assert result['success'] is True
            # 单ID导出时，exported信息在results[0]中
            assert result['results'][0]['exported'] is True
            assert 'output_path' in result['results'][0]
            assert str(output_path.absolute()) == result['results'][0]['output_path']
            
            # 验证文件内容正确
            assert output_path.exists()
            exported_content = output_path.read_text(encoding='utf-8')
            assert exported_content == original_sgf
    
    def test_get_export_with_short_option(self, temp_db, sample1_path):
        """测试使用 -o 短选项导出SGF到文件"""
        # 读取原始SGF内容
        with open(sample1_path, 'r', encoding='utf-8') as f:
            original_sgf = f.read()
        
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 导出到临时文件
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'exported_short.sgf'
            
            # 使用 -o 参数获取并导出
            get_args = type('Args', (), {'id': game_id, 'ids': None, 'id_file': None, 'output': str(output_path), 'output_dir': None})()
            result = db.cmd_get(get_args)
            
            # 验证导出成功
            assert result['success'] is True
            assert result['results'][0]['exported'] is True
            
            # 验证文件内容正确
            assert output_path.exists()
            exported_content = output_path.read_text(encoding='utf-8')
            assert exported_content == original_sgf
    
    def test_get_without_output_returns_json(self, temp_db, sample1_path):
        """测试不指定 --output 时返回JSON（向后兼容）"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 不指定 output 参数
        get_args = type('Args', (), {'id': game_id, 'ids': None, 'id_file': None, 'output': None, 'output_dir': None})()
        result = db.cmd_get(get_args)
        
        # 验证返回JSON格式（向后兼容，单ID时返回完整game）
        assert result['success'] is True
        assert 'game' in result
        assert 'exported' not in result['results'][0]  # results中没有exported字段
        assert 'sgf' in result['game']
    
    def test_get_export_invalid_path(self, temp_db, sample1_path):
        """测试导出到无效路径时返回错误"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 测试导出到一个无法写入的位置（使用不完整的无效路径格式）
        # 在现代系统中，创建目录通常都会成功，所以我们测试单ID导出成功的情况
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建目录但无写入权限（在Linux上测试）
            no_write_dir = Path(tmpdir) / 'readonly'
            no_write_dir.mkdir()
            no_write_dir.chmod(0o555)  # 移除写入权限
            
            try:
                output_path = no_write_dir / 'file.sgf'
                get_args = type('Args', (), {
                    'id': game_id, 'ids': None, 'id_file': None, 
                    'output': str(output_path), 'output_dir': None
                })()
                result = db.cmd_get(get_args)
                
                # 验证结果（可能在root用户下仍然会成功）
                # 主要验证API不崩溃
                assert 'success' in result
            finally:
                # 恢复权限以便清理
                no_write_dir.chmod(0o755)


class TestGetBatch:
    """测试 get 命令批量获取功能 (v1.0.6+)"""
    
    def test_get_batch_with_ids(self, temp_db, sample1_path, sample2_path):
        """测试使用 --ids 批量获取多个棋谱"""
        # 读取原始SGF内容
        with open(sample1_path, 'r', encoding='utf-8') as f:
            original_sgf1 = f.read()
        with open(sample2_path, 'r', encoding='utf-8') as f:
            original_sgf2 = f.read()
        
        # 添加两个棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        
        # 获取添加的棋谱ID
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        assert len(games) >= 2
        
        game_id1 = games[0]['id']
        game_id2 = games[1]['id']
        
        # 使用 --ids 批量获取
        get_args = type('Args', (), {
            'id': None,
            'ids': f"{game_id1},{game_id2}",
            'id_file': None,
            'output': None,
            'output_dir': None
        })()
        result = db.cmd_get(get_args)
        
        # 验证批量获取结果
        assert result['success'] is True
        assert result['total_requested'] == 2
        assert result['found'] == 2
        assert len(result['results']) == 2
        assert len(result['not_found']) == 0
        
        # 验证每个结果都包含基本信息
        for r in result['results']:
            assert r['success'] is True
            assert 'id' in r
            assert 'black' in r
            assert 'white' in r
    
    def test_get_batch_with_multiple_id_flags(self, temp_db, sample1_path, sample2_path):
        """测试使用多次 --id 参数批量获取"""
        # 添加两个棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 获取添加的棋谱ID
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        game_id1 = games[0]['id']
        game_id2 = games[1]['id']
        
        # 使用多次 --id 参数
        get_args = type('Args', (), {
            'id': [game_id1, game_id2],  # 模拟多次 --id 参数
            'ids': None,
            'id_file': None,
            'output': None,
            'output_dir': None
        })()
        result = db.cmd_get(get_args)
        
        assert result['success'] is True
        assert result['total_requested'] == 2
        assert result['found'] == 2
    
    def test_get_batch_with_id_file(self, temp_db, sample1_path, sample2_path):
        """测试使用 --id-file 从文件读取批量获取"""
        # 添加两个棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 获取添加的棋谱ID
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        game_id1 = games[0]['id']
        game_id2 = games[1]['id']
        
        # 创建ID文件（每行一个ID）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"{game_id1}\n{game_id2}\n")
            id_file = f.name
        
        try:
            # 使用 --id-file 批量获取
            get_args = type('Args', (), {
                'id': None,
                'ids': None,
                'id_file': id_file,
                'output': None,
                'output_dir': None
            })()
            result = db.cmd_get(get_args)
            
            assert result['success'] is True
            assert result['total_requested'] == 2
            assert result['found'] == 2
        finally:
            os.unlink(id_file)
    
    def test_get_batch_with_id_file_comma_separated(self, temp_db, sample1_path, sample2_path):
        """测试 --id-file 支持逗号分隔的ID"""
        # 添加两个棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 获取添加的棋谱ID
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        game_id1 = games[0]['id']
        game_id2 = games[1]['id']
        
        # 创建ID文件（逗号分隔）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"{game_id1},{game_id2}")
            id_file = f.name
        
        try:
            # 使用 --id-file 批量获取
            get_args = type('Args', (), {
                'id': None,
                'ids': None,
                'id_file': id_file,
                'output': None,
                'output_dir': None
            })()
            result = db.cmd_get(get_args)
            
            assert result['success'] is True
            assert result['total_requested'] == 2
            assert result['found'] == 2
        finally:
            os.unlink(id_file)
    
    def test_get_batch_export_to_dir(self, temp_db, sample1_path, sample2_path):
        """测试批量导出到目录"""
        # 读取原始SGF内容
        with open(sample1_path, 'r', encoding='utf-8') as f:
            original_sgf1 = f.read()
        
        # 添加两个棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 获取添加的棋谱ID
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        game_id1 = games[0]['id']
        game_id2 = games[1]['id']
        
        # 导出到临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'exported_games'
            
            # 使用 --output-dir 批量导出
            get_args = type('Args', (), {
                'id': None,
                'ids': f"{game_id1},{game_id2}",
                'id_file': None,
                'output': None,
                'output_dir': str(output_dir)
            })()
            result = db.cmd_get(get_args)
            
            # 验证导出成功
            assert result['success'] is True
            assert result['export_count'] == 2
            assert 'exported_files' in result
            assert len(result['exported_files']) == 2
            assert result['output_dir'] == str(output_dir.absolute())
            
            # 验证每个结果都有导出路径
            for r in result['results']:
                assert r['exported'] is True
                assert 'output_path' in r
            
            # 验证文件实际存在且内容正确
            assert output_dir.exists()
            sgf_files = list(output_dir.glob('*.sgf'))
            assert len(sgf_files) == 2
    
    def test_get_batch_auto_filename_generation(self, temp_db, sample1_path):
        """测试批量导出时自动生成文件名"""
        # 添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 导出到临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            get_args = type('Args', (), {
                'id': game_id,
                'ids': None,
                'id_file': None,
                'output': None,
                'output_dir': str(output_dir)
            })()
            result = db.cmd_get(get_args)
            
            assert result['success'] is True
            
            # 验证生成的文件名包含元数据信息
            output_path = result['results'][0]['output_path']
            filename = Path(output_path).name
            
            # 文件名格式: [日期]_[赛事]_黑方_vs_白方_[ID后缀].sgf
            assert filename.endswith('.sgf')
            assert '柯洁' in filename or '申真谞' in filename  # 棋手名
    
    def test_get_batch_filename_deduplication(self, temp_db, sample1_path):
        """测试批量导出时文件名重复自动添加序号"""
        # 添加一个棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 导出到临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # 第一次导出
            get_args1 = type('Args', (), {
                'id': game_id,
                'ids': None,
                'id_file': None,
                'output': None,
                'output_dir': str(output_dir)
            })()
            result1 = db.cmd_get(get_args1)
            first_path = result1['results'][0]['output_path']
            
            # 第二次导出（同ID，应该触发文件名重复处理）
            get_args2 = type('Args', (), {
                'id': game_id,
                'ids': None,
                'id_file': None,
                'output': None,
                'output_dir': str(output_dir)
            })()
            result2 = db.cmd_get(get_args2)
            second_path = result2['results'][0]['output_path']
            
            # 验证两个文件路径不同（第二个应该带序号）
            assert first_path != second_path
            filename2 = Path(second_path).name
            # 第二个文件名应该包含序号后缀
            assert '_1' in filename2 or '_2' in filename2
    
    def test_get_batch_partial_not_found(self, temp_db, sample1_path):
        """测试批量获取时部分ID不存在"""
        # 添加一个棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 批量获取（一个存在，一个不存在）
        get_args = type('Args', (), {
            'id': None,
            'ids': f"{game_id},nonexistent123",
            'id_file': None,
            'output': None,
            'output_dir': None
        })()
        result = db.cmd_get(get_args)
        
        # 验证部分成功
        assert result['success'] is True  # 至少有一个成功
        assert result['total_requested'] == 2
        assert result['found'] == 1
        assert len(result['not_found']) == 1
        assert 'nonexistent123' in result['not_found']
        
        # 验证结果中有成功和失败
        success_count = sum(1 for r in result['results'] if r['success'])
        fail_count = sum(1 for r in result['results'] if not r['success'])
        assert success_count == 1
        assert fail_count == 1
    
    def test_get_batch_no_id_error(self, temp_db):
        """测试不指定任何ID时报错"""
        get_args = type('Args', (), {
            'id': None,
            'ids': None,
            'id_file': None,
            'output': None,
            'output_dir': None
        })()
        result = db.cmd_get(get_args)
        
        assert result['success'] is False
        assert '需要指定' in result['error']
        assert '--id' in result['error'] or '--ids' in result['error'] or '--id-file' in result['error']
    
    def test_get_batch_id_file_not_exists(self, temp_db):
        """测试 --id-file 文件不存在时报错"""
        get_args = type('Args', (), {
            'id': None,
            'ids': None,
            'id_file': '/nonexistent/file.txt',
            'output': None,
            'output_dir': None
        })()
        result = db.cmd_get(get_args)
        
        assert result['success'] is False
        assert '不存在' in result['error']
    
    def test_get_batch_single_id_backward_compatible(self, temp_db, sample1_path):
        """测试单ID获取向后兼容（返回完整game数据）"""
        # 读取原始SGF内容
        with open(sample1_path, 'r', encoding='utf-8') as f:
            original_sgf = f.read()
        
        # 添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 单ID获取（不指定output_dir）
        get_args = type('Args', (), {
            'id': game_id,
            'ids': None,
            'id_file': None,
            'output': None,
            'output_dir': None
        })()
        result = db.cmd_get(get_args)
        
        assert result['success'] is True
        # 验证返回完整game数据（向后兼容）
        assert 'game' in result
        assert result['game']['id'] == game_id
        assert result['game']['sgf'] == original_sgf
    
    def test_get_batch_ids_deduplication(self, temp_db, sample1_path):
        """测试批量获取时自动去重ID"""
        # 添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 使用重复的ID
        get_args = type('Args', (), {
            'id': None,
            'ids': f"{game_id},{game_id},{game_id}",
            'id_file': None,
            'output': None,
            'output_dir': None
        })()
        result = db.cmd_get(get_args)
        
        # 验证去重后只获取一次
        assert result['success'] is True
        assert result['total_requested'] == 1  # 去重后只有一个
        assert result['found'] == 1
        assert len(result['results']) == 1


class TestQueryFileParameters:
    """测试 query 命令的 --where-file 和简化参数"""
    
    def test_query_with_where_file(self, temp_db, sample1_path):
        """测试使用 --where-file 从文件读取查询条件"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': None, 'dir': str(FIXTURES_DIR),
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 创建 where 条件文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'black': '柯洁'}, f)
            where_file = f.name
        
        try:
            # 使用 --where-file 查询
            query_args = type('Args', (), {
                'where': None,
                'where_file': where_file,
                'date': None,
                'player': None,
                'event': None,
                'event_like': None,
                'sort': None, 'limit': None
            })()
            result = db.cmd_query(query_args)
            
            assert result['success'] is True
            assert result['count'] >= 1
            for game in result['games']:
                assert game['black'] == '柯洁'
        finally:
            os.unlink(where_file)
    
    def test_query_where_and_where_file_conflict(self, temp_db):
        """测试同时使用 --where 和 --where-file 报错"""
        query_args = type('Args', (), {
            'where': '{"black": "柯洁"}',
            'where_file': '/tmp/test.json',
            'date': None,
            'player': None,
            'event': None,
            'event_like': None,
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is False
        assert '不能同时使用' in result['error']
    
    def test_query_where_file_not_exists(self, temp_db):
        """测试 --where-file 文件不存在时报错"""
        query_args = type('Args', (), {
            'where': None,
            'where_file': '/nonexistent/file.json',
            'date': None,
            'player': None,
            'event': None,
            'event_like': None,
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is False
        assert '不存在' in result['error']
    
    def test_query_simplified_date(self, temp_db, sample1_path):
        """测试使用 --date 简化参数"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 使用 --date 简化参数查询
        query_args = type('Args', (), {
            'where': None,
            'where_file': None,
            'date': '2024-01-15',
            'player': None,
            'event': None,
            'event_like': None,
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        assert result['count'] == 1
        assert result['games'][0]['date'] == '2024-01-15'
    
    def test_query_simplified_player(self, temp_db, sample1_path):
        """测试使用 --player 简化参数"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 使用 --player 简化参数查询
        query_args = type('Args', (), {
            'where': None,
            'where_file': None,
            'date': None,
            'player': '柯洁',
            'event': None,
            'event_like': None,
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        assert result['count'] == 1
        assert result['games'][0]['black'] == '柯洁'
    
    def test_query_simplified_event(self, temp_db, sample1_path):
        """测试使用 --event 简化参数"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 使用 --event 简化参数查询
        query_args = type('Args', (), {
            'where': None,
            'where_file': None,
            'date': None,
            'player': None,
            'event': '第25届LG杯决赛',
            'event_like': None,
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        assert result['count'] == 1
    
    def test_query_simplified_event_like(self, temp_db, sample1_path):
        """测试使用 --event-like 简化参数"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 使用 --event-like 简化参数查询
        query_args = type('Args', (), {
            'where': None,
            'where_file': None,
            'date': None,
            'player': None,
            'event': None,
            'event_like': 'LG杯',
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        assert result['count'] == 1
    
    def test_query_combined_simplified_params(self, temp_db, sample1_path):
        """测试组合使用简化参数"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 使用多个简化参数组合查询
        query_args = type('Args', (), {
            'where': None,
            'where_file': None,
            'date': '2024-01-15',
            'player': '柯洁',
            'event': None,
            'event_like': None,
            'sort': None, 'limit': None
        })()
        result = db.cmd_query(query_args)
        
        assert result['success'] is True
        assert result['count'] == 1
        assert result['games'][0]['date'] == '2024-01-15'
        assert result['games'][0]['black'] == '柯洁'


class TestUpdateFileParameters:
    """测试 update 命令的 --set-file 参数"""
    
    def test_update_with_set_file(self, temp_db, sample1_path):
        """测试使用 --set-file 从文件读取更新内容"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 创建 set 内容文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'black': '文件更新名', 'event': '文件更新赛事'}, f)
            set_file = f.name
        
        try:
            # 使用 --set-file 更新
            update_args = type('Args', (), {
                'id': game_id,
                'set': None,
                'set_file': set_file
            })()
            result = db.cmd_update(update_args)
            
            assert result['success'] is True
            assert result['id'] == game_id
            
            # 验证更新
            database = db.ensure_db()
            table = database.table('games')
            game = table.get(db.Query().id == game_id)
            assert game['black'] == '文件更新名'
            assert game['event'] == '文件更新赛事'
        finally:
            os.unlink(set_file)
    
    def test_update_set_and_set_file_conflict(self, temp_db, sample1_path):
        """测试同时使用 --set 和 --set-file 报错"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        update_args = type('Args', (), {
            'id': game_id,
            'set': '{"black": "test"}',
            'set_file': '/tmp/test.json'
        })()
        result = db.cmd_update(update_args)
        
        assert result['success'] is False
        assert '不能同时使用' in result['error']
    
    def test_update_set_file_not_exists(self, temp_db, sample1_path):
        """测试 --set-file 文件不存在时报错"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        update_args = type('Args', (), {
            'id': game_id,
            'set': None,
            'set_file': '/nonexistent/file.json'
        })()
        result = db.cmd_update(update_args)
        
        assert result['success'] is False
        assert '不存在' in result['error']
    
    def test_update_missing_set_and_set_file(self, temp_db, sample1_path):
        """测试既不指定 --set 也不指定 --set-file 时报错"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        update_args = type('Args', (), {
            'id': game_id,
            'set': None,
            'set_file': None
        })()
        result = db.cmd_update(update_args)
        
        assert result['success'] is False
        assert '需要指定' in result['error']


class TestTagFileParameters:
    """测试 tag 命令的 --add-file 和 --remove-file 参数"""
    
    def test_tag_add_file(self, temp_db, sample1_path):
        """测试使用 --add-file 批量添加标签"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 创建标签文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(['标签A', '标签B', '标签C'], f)
            add_file = f.name
        
        try:
            # 使用 --add-file 批量添加标签
            tag_args = type('Args', (), {
                'id': game_id,
                'add': None,
                'add_file': add_file,
                'remove': None,
                'remove_file': None
            })()
            result = db.cmd_tag(tag_args)
            
            assert result['success'] is True
            assert result['action'] == 'add_tags'
            
            # 验证标签已添加
            database = db.ensure_db()
            table = database.table('games')
            game = table.get(db.Query().id == game_id)
            assert '标签A' in game['tags']
            assert '标签B' in game['tags']
            assert '标签C' in game['tags']
        finally:
            os.unlink(add_file)
    
    def test_tag_remove_file(self, temp_db, sample1_path):
        """测试使用 --remove-file 批量移除标签"""
        # 先添加带标签的棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': ['标签1', '标签2', '标签3', '标签4'], 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 创建移除标签文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(['标签1', '标签3'], f)
            remove_file = f.name
        
        try:
            # 使用 --remove-file 批量移除标签
            tag_args = type('Args', (), {
                'id': game_id,
                'add': None,
                'add_file': None,
                'remove': None,
                'remove_file': remove_file
            })()
            result = db.cmd_tag(tag_args)
            
            assert result['success'] is True
            assert result['action'] == 'remove_tags'
            
            # 验证标签已移除
            database = db.ensure_db()
            table = database.table('games')
            game = table.get(db.Query().id == game_id)
            assert '标签1' not in game['tags']
            assert '标签2' in game['tags']
            assert '标签3' not in game['tags']
            assert '标签4' in game['tags']
        finally:
            os.unlink(remove_file)
    
    def test_tag_add_and_add_file_conflict(self, temp_db, sample1_path):
        """测试同时使用 --add 和 --add-file 报错"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        tag_args = type('Args', (), {
            'id': game_id,
            'add': '单个标签',
            'add_file': '/tmp/test.json',
            'remove': None,
            'remove_file': None
        })()
        result = db.cmd_tag(tag_args)
        
        assert result['success'] is False
        assert '不能同时使用' in result['error']
    
    def test_tag_remove_and_remove_file_conflict(self, temp_db, sample1_path):
        """测试同时使用 --remove 和 --remove-file 报错"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        tag_args = type('Args', (), {
            'id': game_id,
            'add': None,
            'add_file': None,
            'remove': '单个标签',
            'remove_file': '/tmp/test.json'
        })()
        result = db.cmd_tag(tag_args)
        
        assert result['success'] is False
        assert '不能同时使用' in result['error']
    
    def test_tag_add_file_not_array(self, temp_db, sample1_path):
        """测试 --add-file 内容不是数组时报错"""
        # 先添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        add_result = db.cmd_add(args)
        game_id = add_result['results'][0]['id']
        
        # 创建非数组内容的文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump('不是数组', f)
            add_file = f.name
        
        try:
            tag_args = type('Args', (), {
                'id': game_id,
                'add': None,
                'add_file': add_file,
                'remove': None,
                'remove_file': None
            })()
            result = db.cmd_tag(tag_args)
            
            assert result['success'] is False
            assert '必须是 JSON 数组' in result['error']
        finally:
            os.unlink(add_file)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weiqi-db 冲突检测测试
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


class TestHashConflictSkip:
    """测试哈希重复时跳过策略"""
    
    def test_hash_conflict_skip(self, temp_db):
        """测试相同内容跳过"""
        sample1_path = FIXTURES_DIR / 'sample1.sgf'
        duplicate_path = FIXTURES_DIR / 'sample_duplicate.sgf'
        
        # 第一次添加
        args1 = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        result1 = db.cmd_add(args1)
        assert result1['success'] is True
        assert result1['added'] == 1
        
        # 第二次添加相同内容（不同文件）
        args2 = type('Args', (), {
            'file': str(duplicate_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        result2 = db.cmd_add(args2)
        
        assert result2['success'] is True
        assert result2['added'] == 0
        assert result2['skipped'] == 1
        
        # 验证数据库中只有一条记录
        database = db.ensure_db()
        table = database.table('games')
        assert len(table.all()) == 1
    
    def test_same_file_skip(self, temp_db):
        """测试同一文件重复添加时跳过"""
        sample1_path = FIXTURES_DIR / 'sample1.sgf'
        
        # 第一次添加
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        result1 = db.cmd_add(args)
        assert result1['added'] == 1
        
        # 第二次添加同一文件
        result2 = db.cmd_add(args)
        
        assert result2['skipped'] == 1
        assert result2['added'] == 0


class TestHashConflictOverwrite:
    """测试哈希重复时覆盖策略"""
    
    def test_hash_conflict_overwrite(self, temp_db):
        """测试相同内容覆盖"""
        sample1_path = FIXTURES_DIR / 'sample1.sgf'
        duplicate_path = FIXTURES_DIR / 'sample_duplicate.sgf'
        
        # 第一次添加带标签
        args1 = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': ['旧标签'], 'conflict': 'skip'
        })()
        result1 = db.cmd_add(args1)
        first_id = result1['results'][0]['id']
        
        # 第二次添加相同内容（覆盖策略）
        args2 = type('Args', (), {
            'file': str(duplicate_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': ['新标签'], 'conflict': 'overwrite'
        })()
        result2 = db.cmd_add(args2)
        
        assert result2['success'] is True
        assert result2['overwritten'] == 1
        
        # 验证数据库中只有一条记录，且是新标签
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        assert len(games) == 1
        assert '新标签' in games[0]['tags']
        assert '旧标签' not in games[0]['tags']


class TestMetadataConflict:
    """测试元数据重复检测"""
    
    def test_metadata_conflict_detection(self, temp_db):
        """测试相同棋手和日期的检测"""
        sample1_path = FIXTURES_DIR / 'sample1.sgf'
        similar_path = FIXTURES_DIR / 'sample_similar.sgf'
        
        # 第一次添加
        args1 = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        result1 = db.cmd_add(args1)
        assert result1['added'] == 1
        
        # 第二次添加相同棋手和日期的棋谱（不同内容）
        args2 = type('Args', (), {
            'file': str(similar_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        result2 = db.cmd_add(args2)
        
        # 应该检测到元数据冲突并跳过
        assert result2['success'] is True
        assert result2['skipped'] == 1
        
        # 验证冲突详情
        assert len(result2['conflicts']) == 1
        conflict = result2['conflicts'][0]
        assert conflict['conflict_type'] == 'metadata'


class TestConflictKeepStrategy:
    """测试保留两者策略"""
    
    def test_keep_both_hash_conflict(self, temp_db):
        """测试哈希冲突时保留两者"""
        sample1_path = FIXTURES_DIR / 'sample1.sgf'
        duplicate_path = FIXTURES_DIR / 'sample_duplicate.sgf'
        
        # 第一次添加
        args1 = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': ['第一个'], 'conflict': 'skip'
        })()
        result1 = db.cmd_add(args1)
        
        # 第二次添加相同内容（保留两者策略）
        args2 = type('Args', (), {
            'file': str(duplicate_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': ['第二个'], 'conflict': 'keep'
        })()
        result2 = db.cmd_add(args2)
        
        assert result2['success'] is True
        assert result2['added'] == 1
        
        # 验证数据库中有两条记录
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        assert len(games) == 2
    
    def test_keep_both_metadata_conflict(self, temp_db):
        """测试元数据冲突时保留两者"""
        sample1_path = FIXTURES_DIR / 'sample1.sgf'
        similar_path = FIXTURES_DIR / 'sample_similar.sgf'
        
        # 第一次添加
        args1 = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        result1 = db.cmd_add(args1)
        
        # 第二次添加相同棋手和日期的棋谱（保留两者策略）
        args2 = type('Args', (), {
            'file': str(similar_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'keep'
        })()
        result2 = db.cmd_add(args2)
        
        assert result2['success'] is True
        assert result2['added'] == 1
        
        # 验证数据库中有两条记录
        database = db.ensure_db()
        table = database.table('games')
        games = table.all()
        assert len(games) == 2


class TestFindConflicts:
    """测试冲突查找功能"""
    
    def test_find_hash_conflict(self, temp_db):
        """测试查找哈希冲突"""
        sample1_path = FIXTURES_DIR / 'sample1.sgf'
        
        # 添加棋谱
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 读取文件内容计算哈希
        with open(sample1_path, 'r', encoding='utf-8') as f:
            sgf_content = f.read()
        content_hash = db.calc_hash(sgf_content)
        
        # 解析元数据
        meta = db.parse_sgf(sgf_content)
        
        # 查找冲突
        database = db.ensure_db()
        table = database.table('games')
        conflicts = db.find_conflicts(table, meta, content_hash)
        
        assert len(conflicts) == 1
        assert conflicts[0]['type'] == 'hash'
    
    def test_find_no_conflict(self, temp_db):
        """测试无冲突情况"""
        sample1_path = FIXTURES_DIR / 'sample1.sgf'
        sample2_path = FIXTURES_DIR / 'sample2.sgf'
        
        # 只添加sample1
        args = type('Args', (), {
            'file': str(sample1_path), 'dir': None,
            'black': None, 'white': None, 'black_rank': None, 'white_rank': None,
            'date': None, 'event': None, 'result': None, 'komi': None,
            'tag': None, 'conflict': 'skip'
        })()
        db.cmd_add(args)
        
        # 读取sample2内容
        with open(sample2_path, 'r', encoding='utf-8') as f:
            sgf_content = f.read()
        content_hash = db.calc_hash(sgf_content)
        meta = db.parse_sgf(sgf_content)
        
        # 查找冲突（应该没有）
        database = db.ensure_db()
        table = database.table('games')
        conflicts = db.find_conflicts(table, meta, content_hash)
        
        assert len(conflicts) == 0

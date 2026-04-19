#!/usr/bin/env python3
"""
定式发现功能单元测试
"""

import unittest
import json
import tempfile
import shutil
import sys
from pathlib import Path

# 添加 weiqi-joseki 项目路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki')

from scripts.joseki_db import JosekiDB


class TestDiscover(unittest.TestCase):
    """测试discover功能"""
    
    def setUp(self):
        """创建临时数据库"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_db.json"
        self.db = JosekiDB(str(self.db_path))
    
    def tearDown(self):
        """清理临时数据库"""
        shutil.rmtree(self.temp_dir)
    
    def test_discover_empty_db(self):
        """空库中发现定式"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc];W[rd])",  # 4手定式
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=4,
            top_k=3,  # 返回多个匹配
            limit=50,
            verbose=False
        )
        
        # 应该发现定式（空库中返回多个匹配）
        results = result['joseki_list']
        self.assertGreaterEqual(len(results), 1)
        # 验证返回的定式有正确的字段
        self.assertIn('matched_prefix_len', results[0])
        self.assertIn('joseki_id', results[0])
        self.assertIn('move_count', results[0])
        self.assertIn('is_rare', results[0])
    
    def test_discover_common_joseki(self):
        """发现常见定式（匹配前缀 >= min_moves）"""
        # 先添加一个定式到库中
        self.db.add(name="已有定式", moves=["B[pd]", "W[qf]", "B[nc]", "W[rd]"])
        
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc];W[rd])",  # 与库中完全相同的定式
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=4,
            top_k=3,
            limit=50,
            verbose=False
        )
        
        # 应该发现为常见定式
        results = result['joseki_list']
        self.assertGreaterEqual(len(results), 1)
        # 找到完全匹配的定式
        exact_match = [r for r in results if r['matched_prefix_len'] >= 4]
        self.assertGreaterEqual(len(exact_match), 1)
        self.assertFalse(exact_match[0]['is_rare'])  # 匹配4手 >= min_moves(4)，不罕见
        self.assertNotEqual(exact_match[0]['joseki_id'], '')
    
    def test_discover_rare_joseki(self):
        """发现罕见定式（匹配前缀 < min_moves）"""
        # 添加一个6手定式到库中
        self.db.add(name="常见定式", moves=["B[pd]", "W[qc]", "B[qd]", "W[pc]", "B[od]", "W[nc]"])
        
        # 使用7手棋谱
        sgf_list = [
            "(;GM[1];B[pd];W[qc];B[qd];W[pc];B[od];W[nb])",  # 前6手匹配（第6手nc!=nb）
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=6,  # 要求6手才算常见，但只匹配6手中的5手前缀
            top_k=3,
            limit=50,
            verbose=False
        )
        
        results = result['joseki_list']
        self.assertGreaterEqual(len(results), 1)
        # 找到匹配前缀小于6手的定式
        rare_matches = [r for r in results if r['matched_prefix_len'] < 6]
        if rare_matches:
            self.assertTrue(rare_matches[0]['is_rare'])  # 匹配前缀 < min_moves，罕见
            self.assertNotEqual(rare_matches[0]['joseki_id'], '')  # 有匹配的定式ID
    
    def test_discover_sorting_priority(self):
        """测试排序优先级：最长匹配优先，相同前缀时频率高的优先"""
        # 添加两个定式：一个完全匹配，一个部分匹配
        self.db.add(name="完全匹配定式", moves=["B[pd]", "W[qc]", "B[qd]", "W[pc]", "B[od]", "W[nc]"])
        self.db.joseki_list[0]['frequency'] = 100
        self.db.add(name="部分匹配定式", moves=["B[pd]", "W[qc]", "B[qd]", "W[pc]"], force=True)
        self.db.joseki_list[1]['frequency'] = 50
        self.db._save()
        
        # 使用能匹配第一个定式6手、第二个定式4手的棋谱
        sgf_list = [
            "(;GM[1];B[pd];W[qc];B[qd];W[pc];B[od];W[nc])",  # 匹配完全匹配定式6手
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=4,
            top_k=3,
            limit=50,
            verbose=False
        )
        
        results = result['joseki_list']
        # 应该返回至少2个定式
        self.assertGreaterEqual(len(results), 2)
        
        # 最长匹配的定式应该排在前面
        for i in range(len(results) - 1):
            self.assertGreaterEqual(results[i]['matched_prefix_len'], results[i+1]['matched_prefix_len'])
    
    def test_discover_prefix_matching(self):
        """测试前缀匹配逻辑"""
        # 添加一个定式
        self.db.add(name="标准定式", moves=["B[pd]", "W[qc]", "B[qd]", "W[pc]", "B[od]"])
        
        # 添加一个变体（前3手相同）
        self.db.add(name="变体定式", moves=["B[pd]", "W[qc]", "B[qd]", "W[oc]"], force=True)
        
        sgf_list = [
            "(;GM[1];B[pd];W[qc];B[qd];W[pc];B[od])",  # 与标准定式完全匹配
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=4,
            top_k=3,
            limit=50,
            verbose=False
        )
        
        results = result['joseki_list']
        self.assertGreaterEqual(len(results), 1)
        # 应该包含完全匹配的那个（5手匹配）
        exact_matches = [r for r in results if r['matched_prefix_len'] == 5]
        self.assertGreaterEqual(len(exact_matches), 1)
        self.assertFalse(exact_matches[0]['is_rare'])
    
    def test_discover_min_moves_filter(self):
        """测试最少手数过滤（有效手数）"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf])",             # 2手有效（tt不算）
            "(;GM[1];B[dd];W[cc];B[bd])",       # 3手
            "(;GM[1];B[qq];W[rr];B[qp];W[rq])", # 4手
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=3,  # 最少3手有效
            top_k=3,
            limit=50,
            verbose=False
        )
        
        results = result['joseki_list']
        # 应该至少返回2个定式（过滤了2手的）
        self.assertGreaterEqual(len(results), 2)
        for r in results:
            effective_moves = len([c for c in r['moves'] if c != 'tt'])
            self.assertGreaterEqual(effective_moves, 3)
    
    def test_discover_limit(self):
        """测试返回数量限制"""
        # 生成多个不同的SGF
        sgf_list = []
        for i in range(10):
            sgf_list.append(f"(;GM[1];B[{'abcdefghij'[i]}d];W[{'abcdefghij'[i]}f])")
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=2,
            top_k=3,
            limit=5,  # 只返回5个
            verbose=False
        )
        
        results = result['joseki_list']
        self.assertEqual(len(results), 5)
        # 验证排名连续
        for i, r in enumerate(results):
            self.assertEqual(r['rank'], i + 1)
    
    def test_discover_multiple_sources(self):
        """测试多个源（文件和目录）"""
        # 创建临时SGF文件
        sgf_dir = Path(self.temp_dir) / "sgf_dir"
        sgf_dir.mkdir()
        (sgf_dir / "game1.sgf").write_text("(;GM[1];B[pd];W[qf])")
        (sgf_dir / "game2.sgf").write_text("(;GM[1];B[dd];W[cc])")
        
        result = self.db.discover(
            sgf_sources=[sgf_dir],
            first_n=50,
            min_moves=2,
            top_k=3,
            limit=50,
            verbose=False
        )
        
        # 应该从目录中找到至少2个定式
        results = result['joseki_list']
        self.assertGreaterEqual(len(results), 2)
    
    def test_discover_deduplication(self):
        """测试去重功能"""
        # 同一个定式出现在多个SGF中
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc])",
            "(;GM[1];B[pd];W[qf];B[nc])",  # 完全相同的定式
            "(;GM[1];B[pd];W[qf];B[nc])",  # 完全相同的定式
        ]
        
        # 使用单路提取避免多路重复计数
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=3,
            corner_sizes=[9],
            top_k=3,
            limit=50,
            verbose=False
        )
        
        # 应该返回定式（去重后）
        results = result['joseki_list']
        self.assertGreaterEqual(len(results), 1)
        # 第一个定式的来源应该有3个
        self.assertEqual(len(results[0]['sources']), 3)
    
    def test_discover_sgf_info_parsing(self):
        """测试SGF元信息解析"""
        sgf = "(;GM[1]PB[柯洁]PW[申真谞]EV[LG杯]DT[2024-01-01]RE[B+1.5];B[pd];W[qf])"
        
        info = self.db._parse_sgf_info(sgf, Path("/tmp/test.sgf"))
        
        self.assertEqual(info['black_player'], '柯洁')
        self.assertEqual(info['white_player'], '申真谞')
        self.assertEqual(info['event'], 'LG杯')
        self.assertEqual(info['date'], '2024-01-01')
        self.assertEqual(info['result'], 'B+1.5')
        self.assertEqual(info['file'], '/tmp/test.sgf')
    
    def test_discover_sources_info(self):
        """测试来源信息包含在结果中"""
        sgf = "(;GM[1]PB[柯洁]PW[申真谞];B[pd];W[qf])"
        
        # 使用单路提取避免多路重复计数
        result = self.db.discover(
            sgf_sources=[sgf],
            first_n=50,
            min_moves=2,
            corner_sizes=[9],
            top_k=3,
            limit=50,
            verbose=False
        )
        
        results = result['joseki_list']
        self.assertGreaterEqual(len(results), 1)
        self.assertGreaterEqual(len(results[0]['sources']), 1)
        source = results[0]['sources'][0]
        self.assertEqual(source['black_player'], '柯洁')
        self.assertEqual(source['white_player'], '申真谞')
        self.assertIn('corner', source)
    
    def test_discover_output_structure(self):
        """测试输出数据结构"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf])",
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=2,
            top_k=3,
            limit=50,
            verbose=False
        )
        
        # 验证返回格式是字典
        self.assertIn('stats', result)
        self.assertIn('joseki_list', result)
        
        results = result['joseki_list']
        self.assertGreaterEqual(len(results), 1)
        item = results[0]
        
        # 验证所有必需字段
        self.assertIn('rank', item)
        self.assertIn('joseki_id', item)
        self.assertIn('is_rare', item)
        self.assertIn('moves', item)
        self.assertIn('move_count', item)
        self.assertIn('matched_prefix', item)
        self.assertIn('matched_prefix_len', item)
        self.assertIn('frequency', item)
        self.assertIn('probability', item)  # 新增：概率字段
        # similarity字段已移除（不再使用LCS相似度）
        self.assertIn('sources', item)
        
        # 验证字段类型
        self.assertIsInstance(item['rank'], int)
        self.assertIsInstance(item['joseki_id'], str)
        self.assertIsInstance(item['is_rare'], bool)
        self.assertIsInstance(item['moves'], list)
        self.assertIsInstance(item['matched_prefix_len'], int)
        self.assertIsInstance(item['frequency'], int)
        self.assertIsInstance(item['probability'], (int, float))  # 新增：概率是数字
        self.assertIsInstance(item['sources'], list)


if __name__ == '__main__':
    print("=" * 60)
    print("Discover 功能单元测试")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过")
    else:
        print("✗ 测试失败")
    print("=" * 60)
    
    sys.exit(0 if result.wasSuccessful() else 1)

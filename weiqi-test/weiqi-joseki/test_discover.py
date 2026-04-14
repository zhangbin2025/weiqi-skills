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
    
    def test_discover_new_joseki(self):
        """发现新定式"""
        # 空库中，任何定式都是新定式
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc];W[rd])",  # 4手定式
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=4,
            limit=50,
            verbose=False
        )
        
        # 应该发现一个新定式
        results = result['joseki_list']
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]['is_new'])
        self.assertEqual(results[0]['joseki_id'], '')
        self.assertEqual(results[0]['move_count'], 4)
        self.assertEqual(results[0]['frequency'], 0)
    
    def test_discover_existing_joseki(self):
        """发现已存在的定式"""
        # 先添加一个定式到库中
        self.db.add(name="已有定式", moves=["B[pd]", "W[qf]", "B[nc]", "W[rd]"])
        
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc];W[rd])",  # 与库中相同的定式
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=4,
            limit=50,
            verbose=False
        )
        
        # 应该发现为已存在的定式
        results = result['joseki_list']
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]['is_new'])
        self.assertNotEqual(results[0]['joseki_id'], '')
        self.assertEqual(results[0]['move_count'], 4)
    
    def test_discover_rare_joseki(self):
        """发现罕见定式（频率低）"""
        # 添加两个不同的定式，一个频率高，一个频率低
        # 使用 force=True 确保都能添加
        self.db.add(name="常见定式", moves=["B[pd]", "W[qf]", "B[nc]"])
        self.db.joseki_list[0]['frequency'] = 100
        # 完全不同的定式（dd, cc 在左上区域）
        self.db.add(name="罕见定式", moves=["B[dd]", "W[cc]", "B[fc]"], force=True)
        self.db.joseki_list[1]['frequency'] = 2
        self.db._save()
        
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc])",   # 常见定式
            "(;GM[1];B[dd];W[cc];B[fc])",   # 罕见定式
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=3,
            limit=50,
            verbose=False
        )
        
        # 罕见定式应该排在常见定式前面
        results = result['joseki_list']
        self.assertEqual(len(results), 2)
        # 罕见定式（frequency=2）应该排在常见定式（frequency=100）前面
        rare_idx = 0 if results[0]['frequency'] == 2 else 1
        common_idx = 1 if results[0]['frequency'] == 2 else 0
        self.assertLess(rare_idx, common_idx)  # 罕见定式排名更靠前
    
    def test_discover_sorting_priority(self):
        """测试排序优先级：新定式 > 罕见定式 > 复杂定式"""
        # 添加一个已有定式（频率中等）
        self.db.add(name="已有定式", moves=["B[pd]", "W[qf]"])
        self.db.joseki_list[0]['frequency'] = 10
        self.db._save()
        
        sgf_list = [
            "(;GM[1];B[pd];W[qf])",                          # 已有定式
            "(;GM[1];B[dd];W[cc];B[bd];W[cd])",              # 新定式（4手）
            "(;GM[1];B[qq];W[rr];B[qp];W[rq];B[qo];W[ro])",  # 新定式（6手）
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=2,
            limit=50,
            verbose=False
        )
        
        # 验证排序：新定式在前，然后按手数降序
        results = result['joseki_list']
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0]['is_new'])  # 第一个是新定式
        self.assertTrue(results[1]['is_new'])  # 第二个也是新定式
        # 新定式中，手数多的排前面
        self.assertGreaterEqual(results[0]['move_count'], results[1]['move_count'])
    
    def test_discover_min_moves_filter(self):
        """测试最少手数过滤"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf])",             # 2手，应该被过滤
            "(;GM[1];B[dd];W[cc];B[bd])",       # 3手
            "(;GM[1];B[qq];W[rr];B[qp];W[rq])", # 4手
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=3,  # 最少3手
            limit=50,
            verbose=False
        )
        
        # 应该只有2个定式（过滤了2手的）
        results = result['joseki_list']
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertGreaterEqual(r['move_count'], 3)
    
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
            limit=50,
            verbose=False
        )
        
        # 应该从目录中找到2个定式
        results = result['joseki_list']
        self.assertEqual(len(results), 2)
    
    def test_discover_deduplication(self):
        """测试去重功能"""
        # 同一个定式出现在多个SGF中
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc])",
            "(;GM[1];B[pd];W[qf];B[nc])",  # 完全相同的定式
            "(;GM[1];B[pd];W[qf];B[nc])",  # 完全相同的定式
        ]
        
        result = self.db.discover(
            sgf_sources=sgf_list,
            first_n=50,
            min_moves=3,
            limit=50,
            verbose=False
        )
        
        # 应该只有1个唯一定式
        results = result['joseki_list']
        self.assertEqual(len(results), 1)
        # 但来源应该有3个
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
        
        result = self.db.discover(
            sgf_sources=[sgf],
            first_n=50,
            min_moves=2,
            limit=50,
            verbose=False
        )
        
        results = result['joseki_list']
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0]['sources']), 1)
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
            limit=50,
            verbose=False
        )
        
        # 验证返回格式是字典
        self.assertIn('stats', result)
        self.assertIn('joseki_list', result)
        
        results = result['joseki_list']
        item = results[0]
        # 验证所有必需字段
        self.assertIn('rank', item)
        self.assertIn('joseki_id', item)
        self.assertIn('is_new', item)
        self.assertIn('moves', item)
        self.assertIn('move_count', item)
        self.assertIn('frequency', item)
        self.assertIn('similarity', item)
        self.assertIn('sources', item)
        
        # 验证字段类型
        self.assertIsInstance(item['rank'], int)
        self.assertIsInstance(item['joseki_id'], str)
        self.assertIsInstance(item['is_new'], bool)
        self.assertIsInstance(item['moves'], list)
        self.assertIsInstance(item['move_count'], int)
        self.assertIsInstance(item['frequency'], int)
        self.assertIsInstance(item['similarity'], float)
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

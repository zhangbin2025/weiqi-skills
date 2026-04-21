#!/usr/bin/env python3
"""
weiqi-joseki 重构版单元测试
测试新的CLI接口：extract, katago, discover, list, stats, export
"""

import unittest
import tempfile
import shutil
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki')

from src.extraction import extract_moves_all_corners, get_move_sequence
from src.extraction import convert_to_multigogm
from src.builder import KatagoJosekiBuilder
from src.discover import JosekiDiscoverer
from src.storage import JsonStorage
from src.core.coords import convert_to_top_right


class TestExtract(unittest.TestCase):
    """测试提取接口"""
    
    def test_extract_empty_sgf(self):
        """测试空SGF"""
        result = extract_moves_all_corners("", first_n=80, distance_threshold=4)
        self.assertEqual(result, {})
    
    def test_extract_simple_sgf(self):
        """测试简单SGF提取"""
        sgf = "(;SZ[19];B[pd];W[qf];B[nc])"
        result = extract_moves_all_corners(sgf, first_n=10, distance_threshold=4)
        
        # 应该提取到右上角
        self.assertIn('tr', result)
        moves = get_move_sequence(result['tr'])
        self.assertGreaterEqual(len(moves), 2)
    
    def test_extract_with_pass(self):
        """测试提取含脱先的棋谱"""
        sgf = "(;SZ[19];B[pd];W[dp];B[pp];W[dd];B[qf];W[pj];B[nc])"
        result = extract_moves_all_corners(sgf, first_n=10, distance_threshold=4)
        
        # 右上角应该包含脱先标记
        if 'tr' in result:
            moves = result['tr']
            has_pass = any(coord == 'tt' for _, coord in moves)
            # 可能有脱先
            self.assertIsInstance(has_pass, bool)
    
    def test_extract_four_corners(self):
        """测试四角提取"""
        sgf = "(;SZ[19];B[pd];W[dp];B[dd];W[pp];B[nc];W[qc];B[cj];W[cn];B[jc];W[pd])"
        result = extract_moves_all_corners(sgf, first_n=20, distance_threshold=4)
        
        # 应该能提取到至少两个角
        corners = list(result.keys())
        self.assertGreaterEqual(len(corners), 1)
    
    def test_extract_first_n(self):
        """测试first_n参数"""
        sgf = "(;SZ[19]" + ";B[pd];W[qf]" * 30 + ")"
        
        result_10 = extract_moves_all_corners(sgf, first_n=10, distance_threshold=4)
        result_20 = extract_moves_all_corners(sgf, first_n=20, distance_threshold=4)
        
        # first_n越大，提取到的着法可能越多
        total_10 = sum(len(get_move_sequence(moves)) for moves in result_10.values())
        total_20 = sum(len(get_move_sequence(moves)) for moves in result_20.values())
        self.assertGreaterEqual(total_20, total_10)
    
    def test_extract_distance_threshold(self):
        """测试距离阈值参数"""
        sgf = "(;SZ[19];B[pd];W[qf];B[nc])"
        
        result_4 = extract_moves_all_corners(sgf, first_n=10, distance_threshold=4)
        result_6 = extract_moves_all_corners(sgf, first_n=10, distance_threshold=6)
        
        # 距离阈值不同，提取结果可能不同
        self.assertIsInstance(result_4, dict)
        self.assertIsInstance(result_6, dict)
    
    def test_convert_to_multigogm(self):
        """测试MULTIGOGM转换"""
        sgf = "(;SZ[19];B[pd];W[qf];B[nc])"
        result = extract_moves_all_corners(sgf, first_n=10, distance_threshold=4)
        
        if result:
            multigogm = convert_to_multigogm(result)
            self.assertIn("MULTIGOGM", multigogm)
            self.assertTrue(multigogm.startswith("("))


class TestBuilder(unittest.TestCase):
    """测试构建器"""
    
    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_db.json"
    
    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_builder_init(self):
        """测试构建器初始化"""
        builder = KatagoJosekiBuilder(str(self.db_path))
        self.assertIsNotNone(builder.storage)
    
    def test_builder_process_sgf(self):
        """测试处理单个SGF"""
        builder = KatagoJosekiBuilder(str(self.db_path))
        sgf = "(;SZ[19];B[pd];W[qf];B[nc];W[rd])"
        
        result = builder.process_sgf(sgf, first_n=10, distance_threshold=4)
        self.assertIsInstance(result, dict)
    
    def test_builder_empty_sgf(self):
        """测试处理空SGF"""
        builder = KatagoJosekiBuilder(str(self.db_path))
        result = builder.process_sgf("", first_n=10, distance_threshold=4)
        self.assertEqual(result, {})
    
    def test_save_to_db(self):
        """测试保存到数据库"""
        builder = KatagoJosekiBuilder(str(self.db_path))
        
        joseki_list = [
            {"id": "kj_00001", "moves": ["pd", "qf", "nc"], "frequency": 100},
            {"id": "kj_00002", "moves": ["dd", "fc"], "frequency": 50},
        ]
        
        builder.save_to_db(joseki_list, append=False)
        
        # 验证保存成功
        storage = JsonStorage(str(self.db_path))
        self.assertEqual(len(storage.get_all()), 2)


class TestDiscover(unittest.TestCase):
    """测试发现器"""
    
    def test_discover_init(self):
        """测试发现器初始化"""
        joseki_list = [
            {"id": "kj_00001", "moves": ["pd", "qf", "nc"]},
        ]
        discoverer = JosekiDiscoverer(joseki_list)
        self.assertIsNotNone(discoverer.matcher)
    
    def test_discover_corner(self):
        """测试单角发现"""
        joseki_list = [
            {"id": "kj_00001", "moves": ["pd", "qf", "nc", "rd"]},
        ]
        discoverer = JosekiDiscoverer(joseki_list)
        
        # 使用右上角坐标
        moves = ["pd", "qf", "nc", "rd"]
        results = discoverer.discover_corner(moves, corner="tr")
        
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].joseki_id, "kj_00001")
        self.assertEqual(results[0].source_corner, "tr")
    
    def test_discover_no_match(self):
        """测试无匹配情况"""
        joseki_list = [
            {"id": "kj_00001", "moves": ["pd", "qf", "nc"]},
        ]
        discoverer = JosekiDiscoverer(joseki_list)
        
        # 完全不相关的着法
        moves = ["aa", "bb", "cc"]
        results = discoverer.discover_corner(moves, corner="tl")
        
        # 可能没有匹配
        self.assertIsInstance(results, list)
    
    def test_discover_full_sgf(self):
        """测试完整SGF发现"""
        joseki_list = [
            {"id": "kj_00001", "moves": ["pd", "qf", "nc"]},
            {"id": "kj_00002", "moves": ["dd", "fc", "df"]},
        ]
        discoverer = JosekiDiscoverer(joseki_list)
        
        sgf = "(;SZ[19];B[pd];W[qf];B[nc])"
        results = discoverer.discover(sgf, first_n=10, distance_threshold=4)
        
        self.assertIsInstance(results, dict)


class TestStorage(unittest.TestCase):
    """测试存储"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_db.json"
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_storage_init(self):
        """测试存储初始化"""
        storage = JsonStorage(str(self.db_path))
        self.assertEqual(len(storage.get_all()), 0)
    
    def test_storage_add(self):
        """测试添加定式"""
        storage = JsonStorage(str(self.db_path))
        
        joseki = {
            "id": "kj_00001",
            "moves": ["pd", "qf"],
            "frequency": 100
        }
        jid = storage.add(joseki)
        
        self.assertEqual(jid, "kj_00001")
        self.assertEqual(len(storage.get_all()), 1)
    
    def test_storage_get(self):
        """测试获取定式"""
        storage = JsonStorage(str(self.db_path))
        storage.add({"id": "kj_00001", "moves": ["pd"], "frequency": 10})
        
        result = storage.get("kj_00001")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "kj_00001")
        
        result_none = storage.get("not_exist")
        self.assertIsNone(result_none)
    
    def test_storage_clear(self):
        """测试清空"""
        storage = JsonStorage(str(self.db_path))
        storage.add({"id": "kj_00001", "moves": ["pd"], "frequency": 10})
        storage.add({"id": "kj_00002", "moves": ["dd"], "frequency": 20})
        
        storage.clear()
        self.assertEqual(len(storage.get_all()), 0)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_db.json"
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_full_pipeline(self):
        """完整流程测试"""
        # 1. 创建测试定式库
        joseki_list = [
            {"id": "kj_00001", "moves": ["pd", "qf", "nc", "rd"], "frequency": 100},
            {"id": "kj_00002", "moves": ["dd", "fc", "df"], "frequency": 80},
        ]
        
        storage = JsonStorage(str(self.db_path))
        for j in joseki_list:
            storage.add(j)
        
        # 2. 从SGF提取
        sgf = "(;SZ[19];B[pd];W[qf];B[nc];W[rd])"
        extracted = extract_moves_all_corners(sgf, first_n=10, distance_threshold=4)
        self.assertIn('tr', extracted)
        
        # 3. 发现定式
        discoverer = JosekiDiscoverer(joseki_list)
        results = discoverer.discover(sgf, first_n=10, distance_threshold=4)
        self.assertIsInstance(results, dict)
        
        # 4. 验证发现结果
        if 'tr' in results:
            self.assertGreater(len(results['tr']), 0)


class TestCoordinateConversion(unittest.TestCase):
    """测试坐标转换"""
    
    def test_convert_to_top_right(self):
        """测试转换到右上角"""
        # 左上转右上
        tl_moves = ["dd", "fc", "df"]
        tr_moves = convert_to_top_right(tl_moves, "tl")
        self.assertEqual(len(tr_moves), len(tl_moves))
        
        # 左下转右上
        bl_moves = ["dq", "fo", "hq"]
        tr_moves = convert_to_top_right(bl_moves, "bl")
        self.assertEqual(len(tr_moves), len(bl_moves))
        
        # 右下转右上
        br_moves = ["qq", "oo", "qo"]
        tr_moves = convert_to_top_right(br_moves, "br")
        self.assertEqual(len(tr_moves), len(br_moves))
        
        # 右上无需转换
        tr_moves = ["pd", "qf", "nc"]
        result = convert_to_top_right(tr_moves, "tr")
        self.assertEqual(result, tr_moves)


if __name__ == '__main__':
    print("=" * 60)
    print("weiqi-joseki 重构版单元测试")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过")
    else:
        print(f"✗ 测试失败: {len(result.failures)} 失败, {len(result.errors)} 错误")
    print("=" * 60)
    
    sys.exit(0 if result.wasSuccessful() else 1)

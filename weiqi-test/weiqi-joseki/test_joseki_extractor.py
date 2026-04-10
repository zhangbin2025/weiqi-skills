#!/usr/bin/env python3
"""
定式提取模块单元测试
"""

import unittest
import sys
from pathlib import Path

# 添加 weiqi-joseki 项目路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki')

from scripts.joseki_extractor import (
    extract_joseki_from_sgf, process_corner_sequence,
    format_multigogm, parse_multigogm,
    detect_corner, convert_to_top_right,
    CoordinateSystem, COORDINATE_SYSTEMS
)


class TestCoordinateSystem(unittest.TestCase):
    """测试坐标系统"""
    
    def test_sgf_to_nums(self):
        """测试SGF坐标转数字"""
        self.assertEqual(CoordinateSystem.sgf_to_nums('aa'), (0, 0))
        self.assertEqual(CoordinateSystem.sgf_to_nums('pd'), (15, 3))
        self.assertEqual(CoordinateSystem.sgf_to_nums('ss'), (18, 18))
    
    def test_nums_to_sgf(self):
        """测试数字转SGF坐标"""
        self.assertEqual(CoordinateSystem.nums_to_sgf(0, 0), 'aa')
        self.assertEqual(CoordinateSystem.nums_to_sgf(15, 3), 'pd')
        self.assertEqual(CoordinateSystem.nums_to_sgf(18, 18), 'ss')
    
    def test_coordinate_systems_exist(self):
        """测试所有坐标系都存在"""
        expected = ['lurd', 'ludr', 'ldru', 'ldur', 'ruld', 'rudl', 'rdlu', 'rdul']
        for name in expected:
            self.assertIn(name, COORDINATE_SYSTEMS)
            self.assertIsInstance(COORDINATE_SYSTEMS[name], CoordinateSystem)


class TestDetectCorner(unittest.TestCase):
    """测试角位检测"""
    
    def test_detect_top_left(self):
        """检测左上"""
        moves = ['aa', 'bb', 'cc']
        self.assertEqual(detect_corner(moves), 'tl')
    
    def test_detect_top_right(self):
        """检测右上"""
        moves = ['qd', 'pd', 'nc']
        self.assertEqual(detect_corner(moves), 'tr')
    
    def test_detect_bottom_left(self):
        """检测左下"""
        moves = ['aq', 'bq', 'cq']
        self.assertEqual(detect_corner(moves), 'bl')
    
    def test_detect_bottom_right(self):
        """检测右下"""
        moves = ['qr', 'qq', 'qp']
        self.assertEqual(detect_corner(moves), 'br')
    
    def test_detect_mixed(self):
        """混合坐标返回数量最多的角"""
        moves = ['aa', 'bb', 'qd']  # 两个左上，一个右上
        result = detect_corner(moves)
        self.assertEqual(result, 'tl')
    
    def test_detect_empty(self):
        """空列表返回None"""
        self.assertIsNone(detect_corner([]))
        self.assertIsNone(detect_corner(['pass']))
    
    def test_detect_with_pass(self):
        """包含pass的检测"""
        moves = ['aa', 'pass', 'bb']
        self.assertEqual(detect_corner(moves), 'tl')


class TestConvertToTopRight(unittest.TestCase):
    """测试坐标转换到右上角"""
    
    def test_tr_no_change(self):
        """右上角无需转换"""
        moves = ['pd', 'qf', 'nc']
        result = convert_to_top_right(moves, 'tr')
        self.assertEqual(result, moves)
    
    def test_tl_to_tr(self):
        """左上转换到右上"""
        moves = ['dd', 'cf', 'db']
        result = convert_to_top_right(moves, 'tl')
        # 左上坐标应该被转换
        self.assertEqual(len(result), len(moves))
    
    def test_bl_to_tr(self):
        """左下转换到右上"""
        moves = ['dq', 'fo', 'hq']
        result = convert_to_top_right(moves, 'bl')
        self.assertEqual(len(result), len(moves))
    
    def test_br_to_tr(self):
        """右下转换到右上"""
        moves = ['qq', 'oo', 'qo']
        result = convert_to_top_right(moves, 'br')
        self.assertEqual(len(result), len(moves))
    
    def test_convert_with_pass(self):
        """转换保留pass"""
        moves = ['dd', 'pass', 'cf']
        result = convert_to_top_right(moves, 'tl')
        self.assertIn('pass', result)


class TestExtractJosekiFromSGF(unittest.TestCase):
    """测试从SGF提取定式"""
    
    def test_extract_all_corners(self):
        """提取所有四角"""
        sgf = "(;GM[1];B[pd];W[pp];B[dd];W[dp])"
        result = extract_joseki_from_sgf(sgf, first_n=50)
        # 应该包含MULTIGOGM标记
        self.assertIn("MULTIGOGM", result)
        self.assertTrue(result.startswith("("))
    
    def test_extract_single_corner(self):
        """提取单个角"""
        sgf = "(;GM[1];B[pd];W[pp])"
        # 提取右上角
        result = extract_joseki_from_sgf(sgf, corner='tr')
        self.assertIn("MULTIGOGM", result)
    
    def test_extract_with_first_n(self):
        """限制前N手"""
        sgf = "(;GM[1]" + ";B[pd];W[pp]" * 30 + ")"
        result = extract_joseki_from_sgf(sgf, first_n=10)
        # 应该成功解析
        self.assertIn("MULTIGOGM", result)
    
    def test_extract_empty_sgf(self):
        """空SGF返回空MULTIGOGM"""
        sgf = ""
        result = extract_joseki_from_sgf(sgf)
        self.assertIn("MULTIGOGM", result)
    
    def test_extract_with_pass(self):
        """提取包含脱先"""
        sgf = "(;GM[1];B[pd];W[];B[qf])"
        result = extract_joseki_from_sgf(sgf)
        # 应该成功解析
        self.assertIn("MULTIGOGM", result)


class TestProcessCornerSequence(unittest.TestCase):
    """测试角序列处理"""
    
    def test_process_normal_sequence(self):
        """处理正常序列"""
        moves = [('B', 'pd'), ('W', 'qf'), ('B', 'nc')]
        result = process_corner_sequence(moves, "右上", "tr")
        self.assertIsNotNone(result)
        comment, processed = result
        self.assertIn("右上", comment)
        self.assertEqual(len(processed), len(moves))
    
    def test_process_white_first(self):
        """白先转黑先"""
        moves = [('W', 'pd'), ('B', 'qf'), ('W', 'nc')]
        result = process_corner_sequence(moves, "右上", "tr")
        self.assertIsNotNone(result)
        comment, processed = result
        self.assertIn("白先→黑先", comment)
    
    def test_process_with_pass(self):
        """处理包含脱先"""
        moves = [('B', 'pd'), ('W', 'tt'), ('B', 'qf')]
        result = process_corner_sequence(moves, "右上", "tr")
        self.assertIsNotNone(result)
    
    def test_process_too_short(self):
        """序列太短返回None"""
        moves = [('B', 'pd')]
        result = process_corner_sequence(moves, "右上", "tr")
        self.assertIsNone(result)


class TestFormatAndParseMultigogm(unittest.TestCase):
    """测试MULTIGOGM格式化和解析"""
    
    def test_format_and_parse_roundtrip(self):
        """格式化和解析往返"""
        branches = [
            ("右上 黑先", [('B', 'pd'), ('W', 'qf')]),
            ("左上 黑先", [('B', 'dd'), ('W', 'cc')]),
        ]
        formatted = format_multigogm(branches)
        # 验证格式化结果
        self.assertIn("MULTIGOGM", formatted)
        self.assertIn("右上", formatted)
        self.assertIn("左上", formatted)
        
        # 解析并验证
        parsed = parse_multigogm(formatted)
        self.assertIn('tr', parsed)
        self.assertIn('tl', parsed)
    
    def test_format_empty_branches(self):
        """空分支格式化"""
        formatted = format_multigogm([])
        self.assertIn("MULTIGOGM", formatted)
    
    def test_parse_empty(self):
        """解析空字符串"""
        result = parse_multigogm("")
        self.assertEqual(result, {})


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_pipeline(self):
        """完整流程测试"""
        # 创建测试SGF
        sgf = "(;GM[1];B[pd];W[qf];B[nc];W[pb])"
        
        # 提取定式
        multigogm = extract_joseki_from_sgf(sgf)
        
        # 解析
        parsed = parse_multigogm(multigogm)
        
        # 验证
        self.assertIn('tr', parsed)
    
    def test_coordinate_conversion_integrity(self):
        """坐标转换一致性"""
        # 测试坐标转换是否可逆
        for coord_sys in COORDINATE_SYSTEMS.values():
            for col in range(19):
                for row in range(19):
                    sgf = CoordinateSystem.nums_to_sgf(col, row)
                    local = coord_sys._to_local_cache.get(sgf)
                    back_to_sgf = coord_sys._to_sgf_cache.get(local)
                    self.assertEqual(sgf, back_to_sgf)


if __name__ == '__main__':
    print("=" * 60)
    print("Joseki Extractor 单元测试")
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

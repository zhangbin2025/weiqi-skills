#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGF Parser 单元测试

从 weiqi-sgf 技能包提取的测试代码
"""

import unittest
import sys
from pathlib import Path

# 添加 weiqi-sgf 项目路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-sgf/scripts')

from sgf_parser import parse_sgf


class TestSGFParser(unittest.TestCase):
    """SGF 解析器单元测试"""
    
    def test_empty_sgf(self):
        """测试空 SGF"""
        result = parse_sgf("")
        self.assertIn("SGF内容为空", result['errors'])
        self.assertEqual(result['stats']['total_nodes'], 1)
        self.assertEqual(result['stats']['move_nodes'], 0)
    
    def test_root_only(self):
        """测试只有根节点"""
        sgf = "(;GM[1]FF[4]PB[黑棋]PW[白棋])"
        result = parse_sgf(sgf)
        
        self.assertEqual(result['game_info']['black'], '黑棋')
        self.assertEqual(result['game_info']['white'], '白棋')
        self.assertEqual(result['tree']['is_root'], True)
        self.assertEqual(result['tree']['move_number'], 0)
        self.assertEqual(result['tree']['color'], None)
        self.assertEqual(result['tree']['coord'], None)
        self.assertEqual(len(result['tree']['children']), 0)
        self.assertEqual(result['stats']['total_nodes'], 1)
        self.assertEqual(result['stats']['move_nodes'], 0)
        self.assertEqual(len(result['errors']), 0)
    
    def test_single_branch(self):
        """测试单分支（标准棋谱）"""
        sgf = "(;GM[1];B[pd];W[pp];B[dd])"
        result = parse_sgf(sgf)
        
        self.assertEqual(result['stats']['total_nodes'], 4)
        self.assertEqual(result['stats']['move_nodes'], 3)
        self.assertEqual(result['stats']['max_depth'], 3)
        self.assertEqual(result['stats']['branch_count'], 0)
        
        tree = result['tree']
        self.assertEqual(len(tree['children']), 1)
        
        first_move = tree['children'][0]
        self.assertEqual(first_move['is_root'], False)
        self.assertEqual(first_move['move_number'], 1)
        self.assertEqual(first_move['color'], 'B')
        self.assertEqual(first_move['coord'], 'pd')
        self.assertEqual(first_move['properties']['B'], 'pd')
        
        second_move = first_move['children'][0]
        self.assertEqual(second_move['move_number'], 2)
        self.assertEqual(second_move['color'], 'W')
        self.assertEqual(second_move['coord'], 'pp')
    
    def test_root_variations(self):
        """测试根节点多分支（无主分支）"""
        sgf = "(;GM[1](;B[pd])(;B[dd]))"
        result = parse_sgf(sgf)
        
        self.assertEqual(result['stats']['total_nodes'], 3)
        self.assertEqual(result['stats']['move_nodes'], 2)
        self.assertEqual(result['stats']['branch_count'], 1)
        
        tree = result['tree']
        self.assertEqual(len(tree['children']), 2)
        
        # 第一个分支
        self.assertEqual(tree['children'][0]['color'], 'B')
        self.assertEqual(tree['children'][0]['coord'], 'pd')
        
        # 第二个分支（变化）
        self.assertEqual(tree['children'][1]['color'], 'B')
        self.assertEqual(tree['children'][1]['coord'], 'dd')
    
    def test_nested_variations(self):
        """测试嵌套变化分支"""
        sgf = "(;GM[1];B[pd](;W[pp])(;W[dp](;B[dd])(;B[qd])))"
        result = parse_sgf(sgf)
        
        # 树结构: Root -> B[pd] -> (W[pp], W[dp] -> (B[dd], B[qd]))
        # B[pd] 有 2 个子，贡献 1 个 branch
        # W[dp] 有 2 个子，贡献 1 个 branch
        # 总计 2 个 branch
        self.assertEqual(result['stats']['total_nodes'], 6)
        self.assertEqual(result['stats']['move_nodes'], 5)
        self.assertEqual(result['stats']['branch_count'], 2)
        
        tree = result['tree']
        # 根 -> B[pd]
        b_node = tree['children'][0]
        self.assertEqual(b_node['color'], 'B')
        
        # B[pd] 有两个子: W[pp] 和 W[dp]
        self.assertEqual(len(b_node['children']), 2)
        self.assertEqual(b_node['children'][0]['coord'], 'pp')
        self.assertEqual(b_node['children'][1]['coord'], 'dp')
        
        # W[dp] 有两个子: B[dd] 和 B[qd]
        w_dp_node = b_node['children'][1]
        self.assertEqual(len(w_dp_node['children']), 2)
        self.assertEqual(w_dp_node['children'][0]['coord'], 'dd')
        self.assertEqual(w_dp_node['children'][1]['coord'], 'qd')
    
    def test_escape_chars(self):
        """测试转义字符"""
        sgf = r"(;GM[1]C[Comment \] test])"
        result = parse_sgf(sgf)
        
        self.assertEqual(result['tree']['properties']['C'], "Comment ] test")
        self.assertEqual(len(result['errors']), 0)
    
    def test_handicap(self):
        """测试让子棋"""
        sgf = "(;GM[1]SZ[19]HA[2]AB[pd][dp];W[pp])"
        result = parse_sgf(sgf)
        
        self.assertEqual(result['game_info']['handicap'], 2)
        self.assertEqual(len(result['game_info']['handicap_stones']), 2)
        self.assertEqual(result['game_info']['handicap_stones'][0], {'x': 15, 'y': 3})
        self.assertEqual(result['game_info']['handicap_stones'][1], {'x': 3, 'y': 15})
        
        # 让子位置应在根节点
        ab = result['tree']['properties']['AB']
        self.assertIsInstance(ab, list)
        self.assertEqual(len(ab), 2)
    
    def test_multi_value_property(self):
        """测试多值属性"""
        sgf = "(;GM[1]AB[aa][bb][cc])"
        result = parse_sgf(sgf)
        
        ab = result['tree']['properties']['AB']
        self.assertIsInstance(ab, list)
        self.assertEqual(len(ab), 3)
        self.assertEqual(ab[0], 'aa')
        self.assertEqual(ab[1], 'bb')
        self.assertEqual(ab[2], 'cc')
    
    def test_invalid_sgf(self):
        """测试无效 SGF（未闭合属性值）"""
        sgf = "(;GM[1];B[pd;W[pp)"  # B的属性值未闭合
        result = parse_sgf(sgf)
        
        # 应该有错误（属性值未闭合）
        has_error = any("未闭合" in err or "属性" in err for err in result['errors'])
        self.assertTrue(has_error or len(result['errors']) > 0)
    
    def test_extra_close_paren(self):
        """测试多余右括号"""
        sgf = "(;GM[1];B[pd]))"
        result = parse_sgf(sgf)
        
        # 应该有多余的右括号错误或解析错误
        has_paren_error = any("括号" in err for err in result['errors'])
        self.assertTrue(has_paren_error or len(result['errors']) > 0)
    
    def test_pass_move(self):
        """测试虚手（停着）"""
        sgf = "(;GM[1];B[pd];W[];B[dd])"
        result = parse_sgf(sgf)
        
        tree = result['tree']
        w_node = tree['children'][0]['children'][0]
        self.assertEqual(w_node['color'], 'W')
        self.assertIsNone(w_node['coord'])
    
    def test_complex_tree(self):
        """测试复杂树结构"""
        sgf = """(;GM[1]FF[4]PB[黑棋]PW[白棋]
            (;B[pd];W[pp])
            (;B[dd];W[dp]
                (;B[pd])
                (;B[pp];W[pd](;B[qf])(;B[pf]))
            )
            (;B[dp];W[dd])
        )"""
        result = parse_sgf(sgf)
        
        # 根有 3 个子，贡献 2 个 branch
        # 第二个分支下又有分支，总共应有 4 个 branch
        self.assertEqual(result['stats']['branch_count'], 4)
        
        # 验证 game_info
        self.assertEqual(result['game_info']['black'], '黑棋')
        self.assertEqual(result['game_info']['white'], '白棋')
        self.assertEqual(result['game_info']['board_size'], 19)
    
    def test_multigo_format(self):
        """测试 MultiGo 格式的复杂棋谱（用户提供的棋谱）"""
        sgf = """(;CA[gb2312]AP[MultiGo:4.4.4]MULTIGOGM[0]

(;B[pd]N[b1];W[qc];B[qd];W[pc];B[oc];W[ob];B[nb];W[nc];B[od];W[mb];B[pb];W[na];B[qb])
(;B[pd]N[b2];W[qf]
(;B[qe]N[b21];W[pf];B[nd];W[pj])
(;B[nc]N[b22];W[rd];B[qc];W[qi]))
(;B[qd]N[b3];W[oc];B[pc];W[od];B[qf];W[kc]))"""
        
        result = parse_sgf(sgf)
        
        # 验证基本结构
        self.assertEqual(result['stats']['total_nodes'], 30)
        self.assertEqual(result['stats']['move_nodes'], 29)
        self.assertEqual(result['stats']['max_depth'], 13)
        self.assertEqual(result['stats']['branch_count'], 3)
        
        # 验证根节点属性
        self.assertEqual(result['tree']['properties']['CA'], 'gb2312')
        self.assertEqual(result['tree']['properties']['AP'], 'MultiGo:4.4.4')
        
        # 验证根有 3 个直接子节点（三个分支）
        self.assertEqual(len(result['tree']['children']), 3)
        
        # 验证 b1 分支
        b1 = result['tree']['children'][0]
        self.assertEqual(b1['properties']['N'], 'b1')
        self.assertEqual(b1['coord'], 'pd')
        self.assertEqual(b1['move_number'], 1)
        
        # 验证 b2 分支及其子分支
        b2 = result['tree']['children'][1]
        self.assertEqual(b2['properties']['N'], 'b2')
        # B[pd] N=b2 -> W[qf] -> (B[qe] N=b21, B[nc] N=b22)
        self.assertEqual(len(b2['children']), 1)  # W[qf]
        w_qf = b2['children'][0]
        self.assertEqual(len(w_qf['children']), 2)  # b21, b22 子分支
        
        # 验证 b3 分支
        b3 = result['tree']['children'][2]
        self.assertEqual(b3['properties']['N'], 'b3')
        self.assertEqual(b3['coord'], 'qd')


if __name__ == '__main__':
    print("=" * 60)
    print("SGF Parser 单元测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSGFParser)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过")
    else:
        print("✗ 测试失败")
        # 输出失败详情
        for failure in result.failures + result.errors:
            print(f"\n失败: {failure[0]}")
            print(failure[1])
    print("=" * 60)

#!/usr/bin/env python3
"""
定式数据库单元测试
"""

import unittest
import json
import tempfile
import shutil
import sys
from pathlib import Path

# 添加 weiqi-joseki 项目路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki')

from scripts.joseki_db import JosekiDB, MatchResult, ConflictCheck


class TestJosekiDB(unittest.TestCase):
    """测试JosekiDB类"""
    
    def setUp(self):
        """创建临时数据库"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_db.json"
        self.db = JosekiDB(str(self.db_path))
    
    def tearDown(self):
        """清理临时数据库"""
        shutil.rmtree(self.temp_dir)
    
    # ========== CRUD测试 ==========
    
    def test_add_joseki(self):
        """添加定式"""
        joseki_id, conflict = self.db.add(
            name="测试定式",
            category_path="/测试",
            moves=["B[pd]", "W[qf]", "B[nc]"],
            tags=["test"],
            description="这是一个测试"
        )
        
        self.assertIsNotNone(joseki_id)
        self.assertTrue(joseki_id.startswith("joseki_"))
        self.assertIsNone(conflict)
    
    def test_add_with_conflict(self):
        """添加冲突定式"""
        # 先添加一个定式
        moves = ["B[pd]", "W[qf]", "B[nc]"]
        joseki_id1, _ = self.db.add(name="定式1", moves=moves)
        
        # 再添加相同的定式（应该冲突）
        joseki_id2, conflict = self.db.add(name="定式2", moves=moves)
        
        self.assertIsNone(joseki_id2)
        self.assertIsNotNone(conflict)
        self.assertTrue(conflict.has_conflict)
    
    def test_add_force(self):
        """强制添加冲突定式"""
        moves = ["B[pd]", "W[qf]", "B[nc]"]
        joseki_id1, _ = self.db.add(name="定式1", moves=moves)
        
        # 强制添加相同的定式
        joseki_id2, conflict = self.db.add(name="定式2", moves=moves, force=True)
        
        self.assertIsNotNone(joseki_id2)
    
    def test_get_joseki(self):
        """获取定式"""
        joseki_id, _ = self.db.add(name="测试", moves=["B[pd]", "W[qf]"])
        
        joseki = self.db.get(joseki_id)
        self.assertIsNotNone(joseki)
        self.assertEqual(joseki['name'], "测试")
        self.assertEqual(joseki['id'], joseki_id)
    
    def test_get_nonexistent(self):
        """获取不存在的定式"""
        joseki = self.db.get("joseki_999")
        self.assertIsNone(joseki)
    
    def test_remove_joseki(self):
        """删除定式"""
        joseki_id, _ = self.db.add(name="测试", moves=["B[pd]", "W[qf]"])
        
        result = self.db.remove(joseki_id)
        self.assertTrue(result)
        
        # 验证已删除
        self.assertIsNone(self.db.get(joseki_id))
    
    def test_remove_nonexistent(self):
        """删除不存在的定式"""
        result = self.db.remove("joseki_999")
        self.assertFalse(result)
    
    def test_list_all(self):
        """列出所有定式"""
        self.db.add(name="定式1", category_path="/A", moves=["B[pd]", "W[qf]"])
        self.db.add(name="定式2", category_path="/B", moves=["B[dd]", "W[cc]"])
        
        all_joseki = self.db.list_all()
        self.assertEqual(len(all_joseki), 2)
    
    def test_list_by_category(self):
        """按分类列出"""
        self.db.add(name="定式1", category_path="/A/1", moves=["B[pd]", "W[qf]"])
        self.db.add(name="定式2", category_path="/A/2", moves=["B[dd]", "W[cc]"])
        self.db.add(name="定式3", category_path="/B", moves=["B[qq]", "W[rr]"])
        
        cat_a = self.db.list_all(category="/A")
        self.assertEqual(len(cat_a), 2)
    
    def test_clear(self):
        """清空数据库"""
        self.db.add(name="定式1", moves=["B[pd]", "W[qf]"])
        self.db.add(name="定式2", moves=["B[dd]", "W[cc]"])
        
        count = self.db.clear()
        self.assertEqual(count, 2)
        self.assertEqual(len(self.db.list_all()), 0)
    
    # ========== 匹配测试 ==========
    
    def test_match_exact(self):
        """精确匹配"""
        moves = ["pd", "qf", "nc"]
        self.db.add(name="测试定式", moves=[f"B[{moves[0]}]", f"W[{moves[1]}]", f"B[{moves[2]}]"])
        
        results = self.db.match(moves)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].prefix_len, 3)  # 完全匹配，前缀长度=3
        self.assertEqual(results[0].total_moves, 3)  # 总手数=3
    
    def test_match_partial(self):
        """部分匹配 - 前缀匹配"""
        # 添加完整定式
        self.db.add(name="完整定式", moves=["B[pd]", "W[qf]", "B[nc]", "W[pb]"])
        
        # 匹配部分序列（3手，定式4手）
        results = self.db.match(["pd", "qf", "nc"])
        self.assertTrue(len(results) > 0)
        # 前缀匹配：前3手匹配
        self.assertEqual(results[0].prefix_len, 3)  # 匹配3手前缀
        self.assertEqual(results[0].total_moves, 4)  # 定式共4手
    
    def test_match_with_pass(self):
        """匹配包含脱先(tt)的序列"""
        self.db.add(name="含脱先定式", moves=["B[pd]", "W[tt]", "B[qf]", "W[nc]"])
        
        # 包含tt的输入应该能匹配
        results = self.db.match(["pd", "tt", "qf"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].prefix_len, 3)  # 包括tt在内，匹配3手
        self.assertEqual(results[0].total_moves, 4)  # 定式共4手
    
    def test_match_top_right(self):
        """匹配右上角定式"""
        self.db.add(name="右上定式", moves=["B[pd]", "W[qf]", "B[nc]"])
        
        results = self.db.match_top_right(["pd", "qf", "nc"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].prefix_len, 3)  # 完全匹配
        self.assertEqual(results[0].total_moves, 3)
    
    # ========== 8向生成测试 ==========
    
    def test_generate_8way_all(self):
        """生成全部8个方向"""
        joseki_id, _ = self.db.add(name="测试", moves=["B[pd]", "W[qf]"])
        
        sgf = self.db.generate_8way_sgf(joseki_id)
        self.assertIsNotNone(sgf)
        self.assertIn("MULTIGOGM", sgf)
    
    def test_generate_8way_single_direction(self):
        """生成单个方向"""
        joseki_id, _ = self.db.add(name="测试", moves=["B[pd]", "W[qf]"])
        
        sgf = self.db.generate_8way_sgf(joseki_id, directions=['ruld'])
        self.assertIsNotNone(sgf)
        self.assertIn("ruld", sgf)
    
    def test_generate_8way_multiple_directions(self):
        """生成多个方向"""
        joseki_id, _ = self.db.add(name="测试", moves=["B[pd]", "W[qf]"])
        
        sgf = self.db.generate_8way_sgf(joseki_id, directions=['ruld', 'rudl'])
        self.assertIsNotNone(sgf)
    
    def test_generate_8way_nonexistent(self):
        """生成不存在定式的8向"""
        sgf = self.db.generate_8way_sgf("joseki_999")
        self.assertIsNone(sgf)
    
    # ========== 导出测试 ==========
    
    def test_export_empty_db(self):
        """导出空数据库"""
        sgf = self.db.export_to_sgf()
        self.assertIn("MULTIGOGM", sgf)
        self.assertIn("导出 0个定式", sgf)
    
    def test_export_single_joseki(self):
        """导出单个定式"""
        self.db.add(name="测试定式", category_path="/测试", moves=["B[pd]", "W[qf]"])
        
        sgf = self.db.export_to_sgf()
        self.assertIn("测试定式", sgf)
        self.assertIn("pd", sgf)
        self.assertIn("qf", sgf)
    
    def test_export_by_category(self):
        """按分类导出"""
        self.db.add(name="定式A", category_path="/A", moves=["B[pd]", "W[qf]"])
        self.db.add(name="定式B", category_path="/B", moves=["B[dd]", "W[cc]"])
        
        sgf = self.db.export_to_sgf(category="/A")
        self.assertIn("定式A", sgf)
        self.assertNotIn("定式B", sgf)
    
    def test_export_by_min_moves(self):
        """按最少手数导出"""
        self.db.add(name="短定式", moves=["B[pd]", "W[qf]"])  # 2手
        self.db.add(name="长定式", moves=["B[pd]", "W[qf]", "B[nc]", "W[pb]"])  # 4手
        
        sgf = self.db.export_to_sgf(min_moves=3)
        self.assertNotIn("短定式", sgf)
        self.assertIn("长定式", sgf)
    
    def test_export_by_max_moves(self):
        """按最多手数导出"""
        self.db.add(name="短定式", moves=["B[pd]", "W[qf]"])  # 2手
        self.db.add(name="长定式", moves=["B[pd]", "W[qf]", "B[nc]", "W[pb]"])  # 4手
        
        sgf = self.db.export_to_sgf(max_moves=2)
        self.assertIn("短定式", sgf)
        self.assertNotIn("长定式", sgf)
    
    def test_export_by_tags(self):
        """按标签导出"""
        self.db.add(name="定式A", moves=["B[pd]", "W[qf]"], tags=["ai"])
        self.db.add(name="定式B", moves=["B[dd]", "W[cc]"], tags=["classic"])
        
        sgf = self.db.export_to_sgf(tags=["ai"])
        self.assertIn("定式A", sgf)
        self.assertNotIn("定式B", sgf)
    
    def test_export_by_ids(self):
        """按ID导出"""
        joseki_id, _ = self.db.add(name="定式A", moves=["B[pd]", "W[qf]"])
        self.db.add(name="定式B", moves=["B[dd]", "W[cc]"])
        
        sgf = self.db.export_to_sgf(ids=[joseki_id])
        self.assertIn("定式A", sgf)
        self.assertNotIn("定式B", sgf)
    
    def test_export_to_file(self):
        """导出到文件"""
        self.db.add(name="测试定式", moves=["B[pd]", "W[qf]"])
        
        output_path = Path(self.temp_dir) / "output.sgf"
        sgf = self.db.export_to_sgf(output_path=str(output_path))
        
        self.assertTrue(output_path.exists())
        content = output_path.read_text(encoding='utf-8')
        self.assertIn("测试定式", content)
    
    def test_export_combined_filters(self):
        """组合过滤条件导出"""
        self.db.add(name="定式A", category_path="/A", moves=["B[pd]", "W[qf]", "B[nc]"], tags=["ai"])
        self.db.add(name="定式B", category_path="/A", moves=["B[dd]", "W[cc]"], tags=["ai"])
        self.db.add(name="定式C", category_path="/B", moves=["B[qq]", "W[rr]", "B[ss]"], tags=["classic"])
        
        sgf = self.db.export_to_sgf(category="/A", min_moves=3, tags=["ai"])
        self.assertIn("定式A", sgf)
        self.assertNotIn("定式B", sgf)
        self.assertNotIn("定式C", sgf)
    
    # ========== 导入测试 ==========
    
    def test_import_from_sgfs(self):
        """从SGF列表导入"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc])",
            "(;GM[1];B[pd];W[qf];B[nc])",  # 重复
            "(;GM[1];B[dd];W[cc])",
        ]

        added, skipped, candidates = self.db.import_from_sgfs(
            sgf_sources=sgf_list,
            min_count=1,
            min_moves=2
        )

        self.assertGreater(added, 0)
        self.assertEqual(len(candidates), 2)  # 两个不同的定式

    def test_import_from_sgfs_with_new_params(self):
        """测试新参数（category, name_prefix, verbose）"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc])",
            "(;GM[1];B[pd];W[qf];B[nc])",  # 重复
        ]

        added, skipped, candidates = self.db.import_from_sgfs(
            sgf_sources=sgf_list,
            min_count=1,
            min_moves=2,
            category="/测试分类",
            name_prefix="测试前缀",
            verbose=False
        )

        self.assertGreater(added, 0)
        # 验证定式使用了正确的分类和名称
        joseki_list = self.db.list_all(category="/测试分类")
        self.assertEqual(len(joseki_list), added)
        for j in joseki_list:
            self.assertTrue(j['name'].startswith("测试前缀"))

    def test_import_from_sgfs_katago_mode(self):
        """测试KataGo导入模式（category=/katago）"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc])",
            "(;GM[1];B[pd];W[qf];B[nc])",  # 重复
            "(;GM[1];B[pd];W[qf];B[nc])",  # 重复
        ]

        added, skipped, candidates = self.db.import_from_sgfs(
            sgf_sources=sgf_list,
            min_count=1,
            min_moves=2,
            category="/katago",
            verbose=False
        )

        self.assertGreater(added, 0)
        # 验证KataGo模式的数据结构
        joseki_list = self.db.list_all(category="/katago")
        self.assertEqual(len(joseki_list), added)

        for j in self.db.joseki_list:
            if j.get('category_path') == '/katago':
                # 验证KataGo模式的特殊字段
                self.assertEqual(j.get('category_path'), '/katago')
                self.assertIn('frequency', j)
                self.assertIn('probability', j)
                self.assertIn('move_count', j)
                # name应该为空
                self.assertEqual(j.get('name', ''), '')
                # 验证数据类型
                self.assertIsInstance(j['frequency'], int)
                self.assertIsInstance(j['probability'], float)
                self.assertIsInstance(j['move_count'], int)
                # 验证probability范围
                self.assertGreaterEqual(j['probability'], 0.0)
                self.assertLessEqual(j['probability'], 1.0)
                # 验证move_count与实际moves长度一致
                self.assertEqual(j['move_count'], len(j.get('moves', [])))

    def test_import_from_sgfs_default_first_n(self):
        """测试first_n默认值改为80"""
        # 检查函数签名中的默认值
        import inspect
        sig = inspect.signature(self.db.import_from_sgfs)
        first_n_param = sig.parameters.get('first_n')
        self.assertIsNotNone(first_n_param)
        self.assertEqual(first_n_param.default, 80)
    
    def test_import_with_min_count(self):
        """导入时限制最少次数"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf])",  # 出现1次
            "(;GM[1];B[pd];W[qf])",  # 出现2次
            "(;GM[1];B[dd];W[cc])",  # 出现1次
        ]

        added, skipped, candidates = self.db.import_from_sgfs(
            sgf_sources=sgf_list,
            min_count=2,  # 至少出现2次
            min_moves=2,
            verbose=False
        )

        # 只有出现2次的定式会被导入
        self.assertEqual(added, 1)
    
    def test_import_with_min_moves(self):
        """导入时限制最少手数"""
        sgf_list = [
            "(;GM[1];B[pd])",  # 1手，不够
            "(;GM[1];B[pd];W[qf];B[nc])",  # 3手
        ]

        added, skipped, candidates = self.db.import_from_sgfs(
            sgf_sources=sgf_list,
            min_count=1,
            min_moves=2,
            verbose=False
        )

        # 只有3手的定式会被考虑
        self.assertEqual(len(candidates), 1)
    
    def test_import_dry_run(self):
        """试运行模式"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc])",
        ]

        added, skipped, candidates = self.db.import_from_sgfs(
            sgf_sources=sgf_list,
            min_count=1,
            min_moves=2,  # 指定最少2手
            dry_run=True,
            verbose=False
        )

        self.assertEqual(added, 0)  # 没有真正导入
        self.assertGreater(len(candidates), 0)  # 但有候选
    
    # ========== 统计测试 ==========
    
    def test_stats_empty(self):
        """空数据库统计"""
        stats = self.db.stats()
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['by_category'], {})
    
    def test_stats_with_data(self):
        """有数据时的统计"""
        self.db.add(name="定式1", category_path="/A", moves=["B[pd]", "W[qf]"])
        self.db.add(name="定式2", category_path="/A", moves=["B[dd]", "W[cc]"])
        self.db.add(name="定式3", category_path="/B", moves=["B[qq]", "W[rr]"])
        
        stats = self.db.stats()
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['by_category']['A'], 2)
        self.assertEqual(stats['by_category']['B'], 1)
    
    # ========== 工具方法测试 ==========
    
    def test_normalize_moves(self):
        """标准化着法"""
        moves = ["B[pd]", "W[qf]", "B[nc]"]
        result = JosekiDB.normalize_moves(moves)
        self.assertEqual(result, ["pd", "qf", "nc"])
    
    def test_normalize_moves_with_pass(self):
        """标准化包含pass的着法"""
        moves = ["B[pd]", "W[]", "B[qf]"]
        
        # ignore_pass=True（默认）
        result = JosekiDB.normalize_moves(moves, ignore_pass=True)
        self.assertEqual(result, ["pd", "qf"])
        
        # ignore_pass=False
        result = JosekiDB.normalize_moves(moves, ignore_pass=False)
        self.assertEqual(result, ["pd", "", "qf"])
    
    # ========== list_all 返回新字段测试 ==========
    
    def test_list_all_returns_frequency_and_probability(self):
        """验证 list_all 返回新字段 frequency 和 probability"""
        # 添加一个普通定式（无frequency/probability）
        self.db.add(name="普通定式", category_path="/测试", moves=["B[pd]", "W[qf]"])
        
        # 添加一个KataGo模式的定式（有frequency/probability）
        joseki_data = {
            "id": "joseki_002",
            "category_path": "/katago",
            "moves": ["dd", "cc"],
            "frequency": 100,
            "probability": 0.85,
            "move_count": 2,
            "created_at": "2024-01-01T00:00:00"
        }
        self.db.joseki_list.append(joseki_data)
        self.db._save()
        
        # 获取列表
        joseki_list = self.db.list_all()
        
        # 验证普通定式
        normal_joseki = next((j for j in joseki_list if j['id'] == 'joseki_001'), None)
        self.assertIsNotNone(normal_joseki)
        self.assertIn('frequency', normal_joseki)
        self.assertIn('probability', normal_joseki)
        self.assertIsNone(normal_joseki['frequency'])
        self.assertIsNone(normal_joseki['probability'])
        
        # 验证KataGo定式
        katago_joseki = next((j for j in joseki_list if j['id'] == 'joseki_002'), None)
        self.assertIsNotNone(katago_joseki)
        self.assertEqual(katago_joseki['frequency'], 100)
        self.assertEqual(katago_joseki['probability'], 0.85)
    
    # ========== import_from_sgfs 拆分函数测试 ==========
    
    def test_extract_joseki_from_sources(self):
        """测试步骤1: _extract_joseki_from_sources"""
        sgf_list = [
            "(;GM[1];B[pd];W[qf];B[nc])",
            "(;GM[1];B[pd];W[qf];B[nc])",  # 重复
            "(;GM[1];B[dd];W[cc])",
        ]
        
        count_map, total_sources, total_sgf_files, total_extracted, unique_count = \
            self.db._extract_joseki_from_sources(sgf_list, first_n=80, verbose=False)
        
        self.assertEqual(total_sources, 3)
        self.assertEqual(total_sgf_files, 3)  # 3个SGF字符串，每个作为一个SGF文件
        self.assertGreater(total_extracted, 0)
        self.assertGreater(unique_count, 0)
        # 验证count_map结构
        self.assertIsInstance(count_map, dict)
        self.assertGreater(len(count_map), 0)
    
    def test_accumulate_prefix_counts(self):
        """测试步骤2: _accumulate_prefix_counts"""
        # 构造测试数据
        count_map = {
            "pd qf": 2,
            "pd qf nc": 1,
            "dd cc": 1
        }
        
        result = self.db._accumulate_prefix_counts(count_map, verbose=False)
        
        # 前缀累加后，"pd qf"应该包含"pd qf nc"的计数
        self.assertEqual(result["pd qf"], 3)  # 2 + 1
        self.assertEqual(result["pd qf nc"], 1)  # 不变
        self.assertEqual(result["dd cc"], 1)  # 不变
    
    def test_filter_candidates(self):
        """测试步骤3: _filter_candidates"""
        count_map = {
            "pd qf": 10,
            "pd qf nc": 5,
            "dd": 1,  # 手数不够，应该被过滤
            "cc dd ee": 3
        }
        total_sgf_count = 100  # 实际的SGF文件数量
        
        candidates = self.db._filter_candidates(
            count_map, total_sgf_count, 
            min_count=2, min_moves=2, min_rate=0.0, verbose=False
        )
        
        # 验证返回格式
        self.assertIsInstance(candidates, list)
        self.assertIsInstance(candidates[0], tuple)
        self.assertEqual(len(candidates[0]), 2)  # (prefix, count)
        
        # 验证按频率降序排序
        counts = [c[1] for c in candidates]
        self.assertEqual(counts, sorted(counts, reverse=True))
        
        # 验证过滤效果："dd"只有1手，应该被过滤
        prefixes = [c[0] for c in candidates]
        self.assertNotIn("dd", prefixes)
    
    def test_build_conflict_hash_sets(self):
        """测试步骤4: _build_conflict_hash_sets"""
        # 添加测试定式
        self.db.add(name="测试1", moves=["B[pd]", "W[qf]"])
        self.db.add(name="测试2", moves=["B[dd]", "W[cc]"])
        
        ruld_hashes, rudl_hashes = self.db._build_conflict_hash_sets(self.db.joseki_list)
        
        # 验证返回类型
        self.assertIsInstance(ruld_hashes, set)
        self.assertIsInstance(rudl_hashes, set)
        
        # 验证包含预期的hash
        self.assertEqual(len(ruld_hashes), 2)  # 两个定式
        self.assertEqual(len(rudl_hashes), 2)  # 两个定式的rudl转换
    
    def test_convert_to_rudl(self):
        """测试辅助函数 _convert_to_rudl"""
        # ruld 方向的坐标
        ruld_moves = ["pd", "qf", "nc"]
        
        rudl_moves = self.db._convert_to_rudl(ruld_moves)
        
        # 验证转换后的坐标不同
        self.assertEqual(len(rudl_moves), len(ruld_moves))
        self.assertNotEqual(rudl_moves, ruld_moves)
        
        # 验证空值/pass处理
        moves_with_pass = ["pd", "", "qf"]
        result = self.db._convert_to_rudl(moves_with_pass)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[1], "")  # pass保持为空
    
    def test_batch_add_joseki_performance(self):
        """测试批量入库性能和正确性"""
        candidates = [
            ("pd qf", 10),
            ("dd cc", 8),
            ("qq rr", 5)
        ]
        total_sgf_count = 100  # 实际的SGF文件数量
        
        ruld_hashes, rudl_hashes = self.db._build_conflict_hash_sets([])
        
        added, skipped, _ = self.db._batch_add_joseki(
            candidates, total_sgf_count, "/katago", "测试",
            ruld_hashes, rudl_hashes, verbose=False
        )
        
        # 验证所有候选都被添加
        self.assertEqual(added, 3)
        self.assertEqual(skipped, 0)
        
        # 验证只调用了一次_save（通过检查数据是否正确保存）
        self.assertEqual(len(self.db.joseki_list), 3)
        
        # 验证数据结构
        for j in self.db.joseki_list:
            self.assertIn('frequency', j)
            self.assertIn('probability', j)
            self.assertIsInstance(j['frequency'], int)
            self.assertIsInstance(j['probability'], float)
    
    def test_batch_add_joseki_conflict_detection(self):
        """验证 hash 冲突检测正确性"""
        # 先添加一个定式
        self.db.add(name="已有定式", moves=["B[pd]", "W[qf]"])
        
        # 准备候选，包含相同定式
        candidates = [
            ("pd qf", 10),  # 应该冲突
            ("dd cc", 8),   # 应该不冲突
        ]
        total_sgf_count = 100  # 实际的SGF文件数量
        
        # 重新加载以清空缓存
        self.db.joseki_list = self.db._load().get("joseki_list", [])
        
        ruld_hashes, rudl_hashes = self.db._build_conflict_hash_sets(self.db.joseki_list)
        
        added, skipped, _ = self.db._batch_add_joseki(
            candidates, total_sgf_count, "/katago", "测试",
            ruld_hashes, rudl_hashes, verbose=False
        )
        
        # 验证冲突检测
        self.assertEqual(added, 1)   # 只有 dd cc 被添加
        self.assertEqual(skipped, 1) # pd qf 因为冲突被跳过


class TestConflictCheck(unittest.TestCase):
    """测试冲突检测"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_db.json"
        self.db = JosekiDB(str(self.db_path))
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_check_conflict_same(self):
        """检查完全相同的定式"""
        moves = ["B[pd]", "W[qf]", "B[nc]"]
        self.db.add(name="定式1", moves=moves)
        
        conflict = self.db.check_conflict(moves)
        self.assertTrue(conflict.has_conflict)
        self.assertEqual(len(conflict.similar_joseki), 1)
    
    def test_check_conflict_different(self):
        """检查不同的定式"""
        self.db.add(name="定式1", moves=["B[pd]", "W[qf]"])
        
        conflict = self.db.check_conflict(["B[dd]", "W[cc]"])
        self.assertFalse(conflict.has_conflict)


if __name__ == '__main__':
    print("=" * 60)
    print("JosekiDB 单元测试")
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

#!/usr/bin/env python3
"""
AutoState状态管理测试
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki/src')

from auto import AutoState, get_adaptive_cms_config


class TestAdaptiveCMSConfig:
    """测试自适应CMS配置"""
    
    def test_small_scale(self):
        """小规模配置"""
        config = get_adaptive_cms_config(50_000)
        assert config["width"] == 1_048_576
        assert config["depth"] == 4
    
    def test_medium_scale(self):
        """中规模配置"""
        config = get_adaptive_cms_config(500_000)
        assert config["width"] == 4_194_304
        assert config["depth"] == 4
    
    def test_large_scale(self):
        """大规模配置"""
        config = get_adaptive_cms_config(2_000_000)
        assert config["width"] == 16_777_216
        assert config["depth"] == 4


class TestAutoStateInit:
    """测试初始化"""
    
    def test_default_directory(self):
        """测试默认目录"""
        state = AutoState()
        assert state.auto_dir == Path.home() / ".weiqi-joseki" / "auto"
    
    def test_custom_directory(self):
        """测试自定义目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            assert state.auto_dir == Path(tmpdir)
    
    def test_not_initialized_by_default(self):
        """测试默认未初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            assert not state.is_initialized()
    
    def test_init_config(self):
        """测试配置初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            config = state.init_config(
                estimated_games=100_000,
                first_n=80,
                distance_threshold=4,
                min_freq=5,
                global_top_k=10_000,
                rebuild_threshold_days=7
            )
            
            assert state.is_initialized()
            assert config["cms_width"] == 4_194_304  # 中规模
            assert config["cms_depth"] == 4
            assert config["first_n"] == 80
            assert config["global_top_k"] == 10_000
            assert config["rebuild_threshold_days"] == 7


class TestAutoStateProgress:
    """测试进度追踪"""
    
    def test_mark_downloaded(self):
        """测试标记下载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            state.mark_downloaded("2026-04-20")
            state.mark_downloaded("2026-04-21")
            
            assert "2026-04-20" in state.progress["downloaded"]
            assert "2026-04-21" in state.progress["downloaded"]
            assert state.progress["downloaded"] == ["2026-04-20", "2026-04-21"]  # 已排序
    
    def test_mark_extracted(self):
        """测试标记提取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            state.mark_extracted("2026-04-20")
            assert "2026-04-20" in state.progress["extracted"]
    
    def test_mark_cms_updated(self):
        """测试标记CMS更新"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            state.mark_cms_updated("2026-04-20")
            assert state.progress["cms_updated_to"] == "2026-04-20"
    
    def test_mark_rebuild(self):
        """测试标记重建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            state.mark_rebuild(joseki_count=5000, sequence_count=20000)
            
            assert state.progress["last_rebuild"] is not None
            assert state.stats["current_joseki"] == 5000
            assert state.stats["total_sequences"] == 20000


class TestAutoStateQueries:
    """测试查询方法"""
    
    def test_get_pending_downloads(self):
        """测试获取待下载日期"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            # 模拟已下载
            state.mark_downloaded("2026-04-20")
            state.mark_downloaded("2026-04-21")
            
            available = ["2026-04-20", "2026-04-21", "2026-04-22", "2026-04-23"]
            pending = state.get_pending_downloads(available)
            
            assert pending == ["2026-04-22", "2026-04-23"]
    
    def test_get_pending_extractions(self):
        """测试获取待提取日期"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            state.mark_downloaded("2026-04-20")
            state.mark_downloaded("2026-04-21")
            state.mark_extracted("2026-04-20")
            
            pending = state.get_pending_extractions()
            assert pending == ["2026-04-21"]
    
    def test_get_pending_cms_dates(self):
        """测试获取待CMS日期"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            # 已提取但未CMS
            state.mark_extracted("2026-04-20")
            state.mark_extracted("2026-04-21")
            state.mark_cms_updated("2026-04-20")
            
            pending = state.get_pending_cms_dates()
            assert pending == ["2026-04-21"]


class TestShouldRebuild:
    """测试重建判断逻辑"""
    
    def test_first_run_should_rebuild(self):
        """首次运行需要重建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            assert state.should_rebuild() == True  # last_rebuild为None
    
    def test_no_new_data_no_rebuild(self):
        """没有新数据不需要重建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            # 模拟刚重建完，没有新数据
            state.mark_rebuild()
            state.mark_cms_updated(state.progress["last_rebuild"])
            
            assert state.should_rebuild() == False
    
    def test_threshold_not_met_no_rebuild(self):
        """未达到阈值不重建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config(rebuild_threshold_days=7)
            
            today = datetime.now().strftime("%Y-%m-%d")
            three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            
            state._data["progress"]["last_rebuild"] = three_days_ago
            state._data["progress"]["cms_updated_to"] = today
            state._save()
            
            assert state.should_rebuild() == False  # 只差3天，不够7天
    
    def test_threshold_met_should_rebuild(self):
        """达到阈值需要重建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config(rebuild_threshold_days=7)
            
            ten_days_ago = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            today = datetime.now().strftime("%Y-%m-%d")
            
            state._data["progress"]["last_rebuild"] = ten_days_ago
            state._data["progress"]["cms_updated_to"] = today
            state._save()
            
            assert state.should_rebuild() == True  # 差10天，超过7天阈值


class TestAutoStatePersistence:
    """测试状态持久化"""
    
    def test_state_saved_to_file(self):
        """测试状态保存到文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config(estimated_games=100_000)
            state.mark_downloaded("2026-04-20")
            
            # 重新加载
            state2 = AutoState(tmpdir)
            assert state2.is_initialized()
            assert "2026-04-20" in state2.progress["downloaded"]
    
    def test_reset(self):
        """测试重置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            state.mark_downloaded("2026-04-20")
            
            state.reset()
            
            assert not state.is_initialized()
            assert state.progress["downloaded"] == []
            assert not (Path(tmpdir) / "state.json").exists()


if __name__ == "__main__":
    # 运行所有测试
    classes = [
        TestAdaptiveCMSConfig,
        TestAutoStateInit,
        TestAutoStateProgress,
        TestAutoStateQueries,
        TestShouldRebuild,
        TestAutoStatePersistence
    ]
    
    for cls in classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in methods:
            method = getattr(instance, method_name)
            try:
                method()
                print(f"✓ {cls.__name__}.{method_name}")
            except Exception as e:
                print(f"✗ {cls.__name__}.{method_name}: {e}")
                raise
    
    print("\n✅ All tests passed!")

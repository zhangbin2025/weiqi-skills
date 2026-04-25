#!/usr/bin/env python3
"""
AutoState状态管理测试（简化版）

测试简化的AutoState，只保留config，不跟踪进度。
"""

import sys
import tempfile
from pathlib import Path

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


class TestAutoStateConfig:
    """测试配置访问"""
    
    def test_config_property(self):
        """测试config属性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config(estimated_games=50_000)
            
            assert state.config["first_n"] == 80
            assert state.config["min_freq"] == 10  # 新默认值


class TestAutoStatePersistence:
    """测试状态持久化"""
    
    def test_state_saved_to_file(self):
        """测试状态保存到文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config(estimated_games=100_000)
            
            # 重新加载
            state2 = AutoState(tmpdir)
            assert state2.is_initialized()
            assert state2.config["first_n"] == 80
    
    def test_reset(self):
        """测试重置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            state.reset()
            
            assert not state.is_initialized()
            assert not (Path(tmpdir) / "state.json").exists()


class TestNewDefaultValues:
    """测试新的默认配置值"""
    
    def test_new_defaults(self):
        """测试新的默认值"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            config = state.init_config()
            
            # 新的默认值
            assert config["cms_width"] == 16_777_216  # 200万棋谱对应16M width
            assert config["cms_depth"] == 4
            assert config["min_freq"] == 10
            assert config["global_top_k"] == 100_000
            assert config["rebuild_threshold_days"] == 0  # 立即重建


if __name__ == "__main__":
    # 运行所有测试
    classes = [
        TestAdaptiveCMSConfig,
        TestAutoStateInit,
        TestAutoStateConfig,
        TestAutoStatePersistence,
        TestNewDefaultValues
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

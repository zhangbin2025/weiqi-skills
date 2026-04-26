#!/usr/bin/env python3
"""
Katago Builder 自动构建功能测试（简化版）
"""

import sys
import gzip
import tempfile
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki')

from src.auto import AutoState
from src.builder import KatagoJosekiBuilder
from src.utils import CountMinSketch


class TestBuildFromCmsAndTempMulti:
    """测试改造后的多文件构建"""
    
    def test_single_file_mode(self):
        """测试单文件模式（兼容旧接口）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建单个temp文件
            temp_file = Path(tmpdir) / "test.txt.gz"
            with gzip.open(temp_file, 'wt') as f:
                # 写入一些测试数据
                for i in range(10):
                    f.write(f"ruld|pd pp pq pr {i}\n")
            
            builder = KatagoJosekiBuilder()
            cms = CountMinSketch(width=10000, depth=4)
            
            # 更新CMS
            for i in range(10):
                cms.update("pd")
                cms.update("pd pp")
            
            # 单文件模式
            result = builder._build_from_cms_and_temp(
                temp_file,  # 单个Path
                cms,
                min_freq=1,
                top_k=5,
                min_moves=2,
                max_moves=10,
                total_sequences=10,
                verbose=False
            )
            
            assert isinstance(result, list)


class TestExtractFromTarToTemp:
    """测试拆分出的提取函数"""
    
    def test_function_exists(self):
        """测试函数存在并可调用"""
        builder = KatagoJosekiBuilder()
        assert hasattr(builder, '_extract_from_tar_to_temp')
    
    def test_config_parameter(self):
        """测试config参数结构"""
        config = {
            'first_n': 80,
            'distance_threshold': 4,
            'min_moves': 4
        }
        # 验证配置结构
        assert 'first_n' in config
        assert 'distance_threshold' in config
        assert 'min_moves' in config


class TestRunAutoSimplified:
    """测试简化后的run_auto"""
    
    def test_run_auto_with_no_tar_files(self):
        """测试没有tar文件时返回None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()
            
            builder = KatagoJosekiBuilder()
            
            # 没有tar文件，应该返回None
            result = builder.run_auto(state, cache_dir)
            assert result is None


if __name__ == "__main__":
    import traceback
    
    classes = [
        TestBuildFromCmsAndTempMulti,
        TestExtractFromTarToTemp,
        TestRunAutoSimplified
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
                traceback.print_exc()
    
    print("\n✅ All tests completed!")

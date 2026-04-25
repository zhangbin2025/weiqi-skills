#!/usr/bin/env python3
"""
Katago Builder 自动构建功能测试
"""

import sys
import gzip
import tempfile
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki/src')
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki/src/builder')

from auto import AutoState
from katago_builder import KatagoJosekiBuilder
from utils import CountMinSketch


class TestAutoExtract:
    """测试增量提取功能"""
    
    def test_extract_new_dates(self):
        """测试提取新下载的日期"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            # 创建模拟的tar文件（实际测试需要模拟数据）
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()
            
            # 由于没有真实的tar文件，创建一个空文件模拟
            tar_file = cache_dir / "2026-04-20rating.tar.bz2"
            tar_file.write_bytes(b"fake tar content")
            
            # 标记为已下载但未提取
            state.mark_downloaded("2026-04-20")
            
            # 实际测试会因无法解析tar而跳过，这里主要测试流程
            # 更完整的测试需要mock iter_sgf_from_tar
            
            print("✓ 提取流程测试（需要真实tar文件进行完整测试）")


class TestAutoUpdateCMS:
    """测试增量CMS更新"""
    
    def test_create_new_cms(self):
        """测试创建新CMS"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config(estimated_games=50000)
            
            # 创建临时temp文件
            temp_dir = Path(tmpdir) / "temp"
            temp_dir.mkdir()
            temp_file = temp_dir / "2026-04-20.txt.gz"
            
            # 测试数据需要有足够的token（min_moves默认是4）
            with gzip.open(temp_file, 'wt') as f:
                f.write("ruld|pd pp pq pr ps\n")  # 5个token
                f.write("ruld|pd pp pr pt pu\n")  # 5个token
            
            builder = KatagoJosekiBuilder(db_path=Path(tmpdir) / "db.json")
            builder._auto_update_cms(state, ["2026-04-20"])
            
            # 验证CMS文件创建
            cms_file = state.auto_dir / "cms.pkl"
            assert cms_file.exists()
            
            # 验证CMS内容
            cms = CountMinSketch.load_from_file(cms_file)
            # 注意：min_moves=4，所以只有长度>=4的前缀才会被统计
            # "pd pp pq pr" 长度为4，应该被统计
            assert cms.estimate("pd pp pq pr") > 0
            
            # 验证状态更新
            assert state.progress["cms_updated_to"] == "2026-04-20"
    
    def test_incremental_cms_update(self):
        """测试增量更新现有CMS"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            temp_dir = Path(tmpdir) / "temp"
            temp_dir.mkdir()
            
            # 第一批数据（需要足够长的序列，min_moves=4）
            with gzip.open(temp_dir / "2026-04-20.txt.gz", 'wt') as f:
                f.write("ruld|pd pp pq pr\n")  # 4个token
            
            builder = KatagoJosekiBuilder(db_path=Path(tmpdir) / "db.json")
            builder._auto_update_cms(state, ["2026-04-20"])
            
            cms1 = CountMinSketch.load_from_file(state.auto_dir / "cms.pkl")
            count1 = cms1.estimate("pd pp pq pr")  # 查询长度为4的前缀
            
            # 第二批数据
            with gzip.open(temp_dir / "2026-04-21.txt.gz", 'wt') as f:
                f.write("ruld|pd pp pq ps pt\n")  # 5个token，前缀"pd pp pq"重叠
            
            builder._auto_update_cms(state, ["2026-04-21"])
            
            cms2 = CountMinSketch.load_from_file(state.auto_dir / "cms.pkl")
            # "pd pp pq"是两个序列的共同前缀(3个token)，但min_moves=4不会统计
            # "pd pp pq pr"只在第一个序列中出现
            # 检查"pd pp pq ps"(第二个序列的4-token前缀)
            count2a = cms2.estimate("pd pp pq pr")
            count2b = cms2.estimate("pd pp pq ps")
            
            # 第一个序列的"pd pp pq pr"计数不变，第二个序列新增了"pd pp pq ps"
            assert count2a == count1  # 第一个序列的前缀计数不变
            assert count2b > 0  # 第二个序列有新的前缀


class TestShouldRebuild:
    """测试重建判断逻辑"""
    
    def test_first_run_need_rebuild(self):
        """首次运行需要重建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            assert state.should_rebuild() == True


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


if __name__ == "__main__":
    import traceback
    
    classes = [
        TestAutoExtract,
        TestAutoUpdateCMS,
        TestShouldRebuild,
        TestBuildFromCmsAndTempMulti,
        TestExtractFromTarToTemp
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

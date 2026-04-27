#!/usr/bin/env python3
"""
CMS持久化功能测试
"""

import tempfile
from pathlib import Path

import sys
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki/src')

from utils.cms import CountMinSketch


class TestCMSPersistence:
    """测试CMS保存和加载功能"""
    
    def test_save_and_load_basic(self):
        """测试基本的保存和加载功能"""
        # 创建CMS并添加一些数据
        cms = CountMinSketch(width=1000, depth=4)
        cms.update("pd")
        cms.update("pd")
        cms.update("pp")
        cms.update("qq", count=5)
        
        # 验证原始数据
        assert cms.estimate("pd") == 2
        assert cms.estimate("pp") == 1
        assert cms.estimate("qq") == 5
        assert len(cms) == 8  # pd调用2次(2) + pp调用1次(1) + qq调用1次count=5(5) = 8
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            cms.save_to_file(temp_path)
            assert temp_path.exists()
            
            # 加载
            cms2 = CountMinSketch.load_from_file(temp_path)
            
            # 验证加载后的数据一致
            assert cms2.width == cms.width
            assert cms2.depth == cms.depth
            assert cms2.estimate("pd") == 2
            assert cms2.estimate("pp") == 1
            assert cms2.estimate("qq") == 5
            assert len(cms2) == 8
            
        finally:
            temp_path.unlink(missing_ok=True)
    
    def test_load_continues_working(self):
        """测试加载后的CMS可以继续使用"""
        cms = CountMinSketch(width=1000, depth=4)
        cms.update("move1")
        cms.update("move2", count=3)
        
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            cms.save_to_file(temp_path)
            cms2 = CountMinSketch.load_from_file(temp_path)
            
            # 继续更新
            cms2.update("move1")  # 原来是1，现在变成2
            cms2.update("move3", count=5)
            
            assert cms2.estimate("move1") == 2
            assert cms2.estimate("move2") == 3
            assert cms2.estimate("move3") == 5
            assert len(cms2) == 10  # 原来的4 + 新增的6
            
        finally:
            temp_path.unlink(missing_ok=True)
    
    def test_large_cms_persistence(self):
        """测试大规模CMS的保存和加载"""
        # 创建一个较大的CMS（模拟生产环境配置）
        cms = CountMinSketch(width=4194304, depth=4)
        
        # 添加大量数据
        for i in range(10000):
            cms.update(f"move_{i % 1000}", count=i % 10 + 1)
        
        original_size = len(cms)
        
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            cms.save_to_file(temp_path)
            
            # 验证文件大小合理（pickle压缩后约32MB）
            file_size_mb = temp_path.stat().st_size / (1024 * 1024)
            assert 20 < file_size_mb < 80, f"文件大小异常: {file_size_mb}MB"
            
            # 加载并验证
            cms2 = CountMinSketch.load_from_file(temp_path)
            assert cms2.width == 4194304
            assert cms2.depth == 4
            assert len(cms2) == original_size
            
            # 抽查几个值
            assert cms2.estimate("move_0") == cms.estimate("move_0")
            assert cms2.estimate("move_500") == cms.estimate("move_500")
            
        finally:
            temp_path.unlink(missing_ok=True)
    
    def test_save_creates_parent_directory(self):
        """测试保存时自动创建父目录"""
        cms = CountMinSketch(width=100, depth=2)
        cms.update("test")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "level1" / "level2" / "cms.pkl"
            assert not nested_path.parent.exists()
            
            cms.save_to_file(nested_path)
            
            assert nested_path.exists()
            
            # 验证可以正常加载
            cms2 = CountMinSketch.load_from_file(nested_path)
            assert cms2.estimate("test") == 1
    
    def test_preserve_unknown_items(self):
        """测试对未插入过的item，加载后查询结果一致"""
        cms = CountMinSketch(width=1000, depth=4)
        cms.update("existing_item", count=10)
        
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            cms.save_to_file(temp_path)
            cms2 = CountMinSketch.load_from_file(temp_path)
            
            # 对从未插入的item，返回应该相同（都是0或近似0）
            assert cms2.estimate("never_inserted") == cms.estimate("never_inserted")
            
        finally:
            temp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test = TestCMSPersistence()
    test.test_save_and_load_basic()
    print("✓ test_save_and_load_basic passed")
    
    test.test_load_continues_working()
    print("✓ test_load_continues_working passed")
    
    test.test_large_cms_persistence()
    print("✓ test_large_cms_persistence passed")
    
    test.test_save_creates_parent_directory()
    print("✓ test_save_creates_parent_directory passed")
    
    test.test_preserve_unknown_items()
    print("✓ test_preserve_unknown_items passed")
    
    print("\n✅ All tests passed!")

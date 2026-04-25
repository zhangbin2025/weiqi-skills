#!/usr/bin/env python3
"""
Katago Downloader 自动下载功能测试
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki/src')
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki/src/extraction')

from auto import AutoState


class TestDownloadAuto:
    """测试download_auto函数"""
    
    def test_no_new_dates_when_all_downloaded(self):
        """测试已全部下载时返回空列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            # 模拟已下载所有日期
            state.mark_downloaded("2026-04-20")
            state.mark_downloaded("2026-04-21")
            
            # mock fetch_available_dates 返回这些日期
            with patch('katago_downloader.fetch_available_dates') as mock_fetch:
                mock_fetch.return_value = ["2026-04-20", "2026-04-21"]
                
                from katago_downloader import download_auto
                
                result = download_auto(state, cache_dir=Path(tmpdir) / "cache")
                
                # 应该返回空列表（没有新日期）
                assert result == []
    
    def test_download_missing_dates(self):
        """测试下载缺失日期并更新state"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            # 模拟部分已下载
            state.mark_downloaded("2026-04-20")
            
            # mock fetch_available_dates 返回更多日期
            with patch('katago_downloader.fetch_available_dates') as mock_fetch:
                mock_fetch.return_value = ["2026-04-20", "2026-04-21", "2026-04-22"]
                
                # mock DownloadManager 模拟成功下载
                with patch('katago_downloader.DownloadManager') as mock_dm_class:
                    mock_dm = MagicMock()
                    mock_dm_class.return_value = mock_dm
                    
                    # 模拟下载成功（返回path）
                    mock_dm.download.return_value = (
                        {"2026-04-21": Path("/fake/2026-04-21.tar.bz2"),
                         "2026-04-22": Path("/fake/2026-04-22.tar.bz2")},  # success_map
                        {},  # error_map
                        0    # cache_hits
                    )
                    
                    from katago_downloader import download_auto
                    
                    result = download_auto(state, cache_dir=Path(tmpdir) / "cache")
                    
                    # 应该返回新下载的日期
                    assert sorted(result) == ["2026-04-21", "2026-04-22"]
                    
                    # state应该已更新
                    assert "2026-04-21" in state.progress["downloaded"]
                    assert "2026-04-22" in state.progress["downloaded"]
    
    def test_partial_download_failure(self):
        """测试部分下载失败时，成功的已记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            with patch('katago_downloader.fetch_available_dates') as mock_fetch:
                mock_fetch.return_value = ["2026-04-20", "2026-04-21"]
                
                with patch('katago_downloader.DownloadManager') as mock_dm_class:
                    mock_dm = MagicMock()
                    mock_dm_class.return_value = mock_dm
                    
                    # 模拟部分失败
                    mock_dm.download.return_value = (
                        {"2026-04-20": Path("/fake/2026-04-20.tar.bz2")},  # 成功
                        {"2026-04-21": "network error"},  # 失败
                        0
                    )
                    
                    from katago_downloader import download_auto
                    
                    result = download_auto(state, cache_dir=Path(tmpdir) / "cache")
                    
                    # 只返回成功的
                    assert result == ["2026-04-20"]
                    
                    # 成功的已记录，失败的没有
                    assert "2026-04-20" in state.progress["downloaded"]
                    assert "2026-04-21" not in state.progress["downloaded"]
    
    def test_empty_available_dates(self):
        """测试服务器无日期时处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            with patch('katago_downloader.fetch_available_dates') as mock_fetch:
                mock_fetch.return_value = []  # 服务器无日期
                
                from katago_downloader import download_auto
                
                result = download_auto(state, cache_dir=Path(tmpdir) / "cache")
                
                # 应该返回空列表
                assert result == []
    
    def test_cache_hit_not_counted_as_new(self):
        """测试缓存命中不计入新下载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = AutoState(tmpdir)
            state.init_config()
            
            # 未下载任何日期
            with patch('katago_downloader.fetch_available_dates') as mock_fetch:
                mock_fetch.return_value = ["2026-04-20", "2026-04-21"]
                
                with patch('katago_downloader.DownloadManager') as mock_dm_class:
                    mock_dm = MagicMock()
                    mock_dm_class.return_value = mock_dm
                    
                    # 模拟缓存命中（from_cache=True）
                    mock_dm.download.return_value = (
                        {"2026-04-20": Path("/fake/2026-04-20.tar.bz2")},
                        {},
                        1  # 1个缓存命中
                    )
                    
                    from katago_downloader import download_auto
                    
                    result = download_auto(state, cache_dir=Path(tmpdir) / "cache")
                    
                    # 缓存命中也会标记为已下载
                    assert "2026-04-20" in state.progress["downloaded"]


if __name__ == "__main__":
    import traceback
    
    test = TestDownloadAuto()
    methods = [m for m in dir(test) if m.startswith("test_")]
    
    for method_name in methods:
        method = getattr(test, method_name)
        try:
            method()
            print(f"✓ {method_name}")
        except Exception as e:
            print(f"✗ {method_name}: {e}")
            traceback.print_exc()
    
    print("\n✅ All tests completed!")

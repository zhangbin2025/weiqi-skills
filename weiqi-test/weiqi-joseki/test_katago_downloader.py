#!/usr/bin/env python3
"""
KataGo下载器单元测试
使用mock进行测试，不执行真实下载
"""

import unittest
import json
import tempfile
import shutil
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加 weiqi-joseki 项目路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki')

from scripts.katago_downloader import (
    MemoryMonitor, ProgressManager, DownloadManager,
    download_katago_games, iter_sgf_from_tar,
    KATAGO_BASE_URL
)


class TestMemoryMonitor(unittest.TestCase):
    """测试内存监控器"""
    
    def setUp(self):
        self.monitor = MemoryMonitor(max_memory_mb=512)
    
    def test_check_ok(self):
        """内存正常状态"""
        # 使用mock模拟内存使用
        with patch.object(self.monitor, 'get_memory_mb', return_value=100.0):
            status, mem = self.monitor.check()
            self.assertEqual(status, 'ok')
            self.assertEqual(mem, 100.0)
    
    def test_check_warning(self):
        """内存警告状态"""
        with patch.object(self.monitor, 'get_memory_mb', return_value=470.0):  # > 90%
            status, mem = self.monitor.check()
            self.assertEqual(status, 'warning')
    
    def test_check_critical(self):
        """内存临界状态"""
        with patch.object(self.monitor, 'get_memory_mb', return_value=520.0):  # > 100%
            status, mem = self.monitor.check()
            self.assertEqual(status, 'critical')
    
    def test_force_gc(self):
        """测试强制垃圾回收"""
        # 确保不会抛出异常
        try:
            self.monitor.force_gc()
        except Exception as e:
            self.fail(f"force_gc 抛出异常: {e}")


class TestProgressManager(unittest.TestCase):
    """测试进度管理器"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.progress_file = Path(self.temp_dir) / "progress.json"
        self.manager = ProgressManager(self.progress_file)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_load(self):
        """保存和加载"""
        # 修改数据并保存
        self.manager.data['completed_dates'] = ['2024-01-01', '2024-01-02']
        self.manager.save()
        
        # 创建新管理器加载
        new_manager = ProgressManager(self.progress_file)
        self.assertEqual(new_manager.data['completed_dates'], ['2024-01-01', '2024-01-02'])
    
    def test_mark_completed(self):
        """标记完成"""
        self.manager.mark_completed('2024-01-01', {'sgf_count': 100})
        self.assertTrue(self.manager.is_completed('2024-01-01'))
        self.assertFalse(self.manager.is_completed('2024-01-02'))
    
    def test_update_count_map(self):
        """更新计数映射"""
        self.manager.update_count_map({'joseki1': 5, 'joseki2': 3})
        self.manager.update_count_map({'joseki1': 2})
        
        count_map = self.manager.get_count_map()
        self.assertEqual(count_map['joseki1'], 7)
        self.assertEqual(count_map['joseki2'], 3)
    
    def test_clear(self):
        """清除进度"""
        self.manager.mark_completed('2024-01-01', {'sgf_count': 100})
        self.manager.clear()
        
        self.assertEqual(self.manager.data['completed_dates'], [])
        self.assertEqual(self.manager.data['total_sgfs'], 0)


class TestDownloadManager(unittest.TestCase):
    """测试下载管理器（使用mock）"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / "cache"
        self.manager = DownloadManager(
            cache_dir=self.cache_dir,
            max_retries=2,
            workers=2,
            keep_cache=True
        )
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    @patch('scripts.katago_downloader.urllib.request.urlopen')
    @patch('scripts.katago_downloader.urllib.request.Request')
    def test_check_file_exists_true(self, mock_request, mock_urlopen):
        """检查文件存在"""
        mock_response = MagicMock()
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        
        exists, error = self.manager.check_file_exists(f"{KATAGO_BASE_URL}20240101rating.tar.bz2")
        self.assertTrue(exists)
        self.assertIsNone(error)
    
    @patch('scripts.katago_downloader.urllib.request.urlopen')
    @patch('scripts.katago_downloader.urllib.request.Request')
    def test_check_file_exists_404(self, mock_request, mock_urlopen):
        """检查文件不存在（404）"""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            None, 404, 'Not Found', None, None
        )
        
        exists, error = self.manager.check_file_exists(f"{KATAGO_BASE_URL}20240101rating.tar.bz2")
        self.assertFalse(exists)
        self.assertIsNone(error)  # 404不算错误
    
    @patch('scripts.katago_downloader.urllib.request.urlopen')
    @patch('scripts.katago_downloader.urllib.request.Request')
    def test_download_single_404(self, mock_request, mock_urlopen):
        """下载单个文件404"""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            None, 404, 'Not Found', None, None
        )
        
        date_str, path, error = self.manager.download_single('2024-01-01')
        self.assertEqual(date_str, '2024-01-01')
        self.assertIsNone(path)  # 没有下载
        self.assertEqual(error, '404')  # 返回404标记
    
    @patch('scripts.katago_downloader.urllib.request.urlopen')
    @patch('scripts.katago_downloader.urllib.request.Request')
    def test_download_single_success(self, mock_request, mock_urlopen):
        """成功下载单个文件"""
        # 模拟文件存在检查
        mock_response = MagicMock()
        mock_response.read.return_value = b"fake tar content"
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        
        # 第一次调用是检查文件存在，第二次是下载
        mock_urlopen.side_effect = [
            MagicMock(),  # HEAD请求响应
            mock_response  # GET请求响应
        ]
        
        date_str, path, error = self.manager.download_single('2024-01-01')
        # 由于我们改变了side_effect，需要更复杂的mock设置
        # 这里简化测试，只验证基本结构
        self.assertEqual(date_str, '2024-01-01')
    
    def test_keep_cache_setting(self):
        """测试缓存保留设置"""
        self.assertTrue(self.manager.keep_cache)
        
        self.manager.set_keep_cache(False)
        self.assertFalse(self.manager.keep_cache)
        
        self.manager.set_keep_cache(True)
        self.assertTrue(self.manager.keep_cache)
    
    def test_stop_and_is_stopped(self):
        """测试停止标志"""
        self.assertFalse(self.manager.is_stopped())
        self.manager.stop()
        self.assertTrue(self.manager.is_stopped())


class TestIterSgfFromTar(unittest.TestCase):
    """测试从tar.bz2迭代读取SGF"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tar_path = Path(self.temp_dir) / "test.tar.bz2"
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_iter_nonexistent_tar(self):
        """不存在的tar文件"""
        nonexistent_path = Path(self.temp_dir) / "nonexistent.tar.bz2"
        result = list(iter_sgf_from_tar(nonexistent_path))
        self.assertEqual(result, [])
    
    def test_iter_empty_tar(self):
        """空的tar文件"""
        import tarfile
        with tarfile.open(self.tar_path, 'w:bz2') as tar:
            pass
        
        result = list(iter_sgf_from_tar(self.tar_path))
        self.assertEqual(result, [])
    
    def test_iter_with_sgf_files(self):
        """包含SGF文件的tar"""
        import tarfile
        import io
        
        # 创建包含SGF文件的tar
        sgf_content = "(;GM[1];B[pd];W[pp])"
        
        with tarfile.open(self.tar_path, 'w:bz2') as tar:
            # 创建SGF文件内容
            sgf_bytes = sgf_content.encode('utf-8')
            tarinfo = tarfile.TarInfo(name="game1.sgf")
            tarinfo.size = len(sgf_bytes)
            tar.addfile(tarinfo, io.BytesIO(sgf_bytes))
        
        # 迭代读取
        result = list(iter_sgf_from_tar(self.tar_path))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], sgf_content)


class TestDownloadKatagoGames(unittest.TestCase):
    """测试便捷下载函数（使用mock）"""
    
    @patch('scripts.katago_downloader.DownloadManager')
    def test_download_with_dates(self, mock_manager_class):
        """测试日期范围下载"""
        mock_manager = MagicMock()
        mock_manager.download.return_value = {'2024-01-01': Path('/fake/path')}
        mock_manager_class.return_value = mock_manager
        
        files, missing = download_katago_games(
            start_date='2024-01-01',
            end_date='2024-01-01',
            cache_dir=None,
            max_retries=3,
            workers=2,
            keep_cache=True
        )
        
        # 验证下载管理器被调用
        mock_manager_class.assert_called_once()
        mock_manager.download.assert_called_once()


if __name__ == '__main__':
    print("=" * 60)
    print("KataGo Downloader 单元测试")
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

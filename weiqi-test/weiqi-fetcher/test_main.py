"""
测试主程序功能
"""

import pytest
import sys
import os
from io import StringIO
from unittest.mock import patch, MagicMock


class TestFetcherRegistry:
    """测试Fetcher注册表功能"""
    
    def test_get_fetcher_for_url_valid(self):
        """测试根据URL获取fetcher - 有效URL"""
        from sources import get_fetcher_for_url
        
        # OGS URL
        url = 'https://online-go.com/game/12345'
        fetcher = get_fetcher_for_url(url)
        assert fetcher is not None
        assert fetcher.name == 'ogs'
    
    def test_get_fetcher_for_url_invalid(self):
        """测试根据URL获取fetcher - 无效URL"""
        from sources import get_fetcher_for_url
        
        # 不支持的URL
        url = 'https://example.com/game/123'
        fetcher = get_fetcher_for_url(url)
        assert fetcher is None
    
    def test_get_fetcher_by_name_valid(self):
        """测试根据名称获取fetcher - 有效名称"""
        from sources import get_fetcher_by_name
        
        fetcher = get_fetcher_by_name('ogs')
        assert fetcher is not None
        assert fetcher.name == 'ogs'
        
        fetcher = get_fetcher_by_name('foxwq')
        assert fetcher is not None
        assert fetcher.name == 'foxwq'
    
    def test_get_fetcher_by_name_invalid(self):
        """测试根据名称获取fetcher - 无效名称"""
        from sources import get_fetcher_by_name
        
        fetcher = get_fetcher_by_name('nonexistent')
        assert fetcher is None
    
    def test_list_fetchers(self):
        """测试列出所有fetcher"""
        from sources import list_fetchers
        
        fetchers = list_fetchers()
        assert len(fetchers) >= 12  # 至少12个fetcher
        
        # 检查返回格式
        for name, display_name, examples in fetchers:
            assert isinstance(name, str)
            assert isinstance(display_name, str)
            assert isinstance(examples, list)
            assert len(name) > 0
            assert len(display_name) > 0
        
        # 检查是否包含预期的fetcher
        names = [name for name, _, _ in fetchers]
        assert 'ogs' in names
        assert 'foxwq' in names
        assert 'weiqi101' in names


class TestMainModule:
    """测试主程序模块"""
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_list_sources(self, mock_stdout):
        """测试列出所有源的功能"""
        from main import list_sources
        
        list_sources()
        
        output = mock_stdout.getvalue()
        assert '支持的棋谱来源' in output
        assert '[ogs]' in output
        assert '[foxwq]' in output
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_print_banner(self, mock_stdout):
        """测试打印banner"""
        from main import print_banner
        
        print_banner()
        
        output = mock_stdout.getvalue()
        assert '🎯 围棋分享棋谱下载器' in output
        assert '=' in output  # 分隔线
    
    def test_print_result_success(self):
        """测试打印成功结果"""
        from main import print_result
        from sources import FetchResult
        
        result = FetchResult(
            success=True,
            source='ogs',
            url='https://online-go.com/game/123',
            sgf_content='(;GM[1]FF[4]SZ[19])',
            output_path='/tmp/ogs_123.sgf',
            metadata={
                'black_name': 'Black',
                'white_name': 'White',
                'black_rank': '3d',
                'white_rank': '3d',
                'rules': 'japanese',
                'komi': 6.5,
                'moves_count': 100,
                'result': 'B+R',
                'date': '2024-01-15',
            },
            timing={'extract_id': 0.001, 'api_request': 0.5}
        )
        
        # 捕获输出
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_result(result)
            output = mock_stdout.getvalue()
        
        # 验证输出内容
        assert '✅ 下载成功' in output
        assert 'OGS' in output or 'ogs' in output
        assert 'Black' in output
        assert 'White' in output
        assert '3d' in output
        assert '/tmp/ogs_123.sgf' in output
        assert '性能统计' in output
    
    def test_print_result_failure(self):
        """测试打印失败结果"""
        from main import print_result
        from sources import FetchResult
        
        result = FetchResult(
            success=False,
            source='ogs',
            url='https://online-go.com/game/123',
            sgf_content=None,
            output_path=None,
            error='网络连接失败',
            metadata={},
            timing={}
        )
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_result(result)
            output = mock_stdout.getvalue()
        
        assert '❌ 下载失败' in output
        assert '网络连接失败' in output


class TestFetcherURLCoverage:
    """测试所有平台的URL覆盖"""
    
    def test_all_platforms_have_url_patterns(self):
        """测试所有平台都有URL匹配模式"""
        from sources.base import _fetchers
        
        for name, fetcher_class in _fetchers.items():
            assert len(fetcher_class.url_patterns) > 0, \
                f"{name} 没有URL匹配模式"
            assert fetcher_class.display_name != '基础源', \
                f"{name} 没有设置display_name"
    
    def test_url_patterns_are_valid_regex(self):
        """测试所有URL模式都是有效的正则表达式"""
        from sources.base import _fetchers
        import re
        
        for name, fetcher_class in _fetchers.items():
            for pattern in fetcher_class.url_patterns:
                try:
                    re.compile(pattern)
                except re.error as e:
                    pytest.fail(f"{name} 的正则表达式无效: {pattern}, 错误: {e}")
    
    def test_url_examples_match_patterns(self):
        """测试URL示例都能匹配对应的模式（跳过占位符示例）"""
        from sources.base import _fetchers
        
        for name, fetcher_class in _fetchers.items():
            for example in fetcher_class.url_examples:
                # 跳过包含占位符的示例
                if ('{' in example and '}' in example) or '...' in example:
                    continue
                assert fetcher_class.can_handle(example), \
                    f"{name} 的示例URL无法匹配: {example}"


class TestFetcherUniqueNames:
    """测试Fetcher名称唯一性"""
    
    def test_all_fetcher_names_unique(self):
        """测试所有fetcher名称都是唯一的"""
        from sources.base import _fetchers
        
        names = list(_fetchers.keys())
        assert len(names) == len(set(names)), "fetcher名称有重复"
    
    def test_all_fetcher_display_names_not_empty(self):
        """测试所有fetcher都有非空的显示名称"""
        from sources.base import _fetchers
        
        for name, fetcher_class in _fetchers.items():
            assert fetcher_class.display_name, f"{name} 没有display_name"
            assert len(fetcher_class.display_name) > 0

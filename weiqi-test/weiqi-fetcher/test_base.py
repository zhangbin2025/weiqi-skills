"""
测试基类功能
"""

import pytest
import re
import os
import tempfile
import shutil


class TestFetchResult:
    """测试 FetchResult 数据类"""
    
    def test_fetch_result_default_values(self):
        """测试 FetchResult 默认值"""
        from sources import FetchResult
        
        result = FetchResult(
            success=True,
            source='test',
            url='https://test.com',
            sgf_content='test',
            output_path='/tmp/test.sgf',
            metadata={'key': 'value'}
        )
        
        assert result.success is True
        assert result.source == 'test'
        assert result.url == 'https://test.com'
        assert result.sgf_content == 'test'
        assert result.output_path == '/tmp/test.sgf'
        assert result.metadata == {'key': 'value'}
        assert result.error is None
        assert result.timing is not None  # 应该有默认值
        assert isinstance(result.timing, dict)
    
    def test_fetch_result_with_timing(self):
        """测试带性能统计的 FetchResult"""
        from sources import FetchResult
        
        timing = {'extract_id': 0.001, 'api_request': 0.5, 'total': 0.501}
        result = FetchResult(
            success=True,
            source='ogs',
            url='https://online-go.com/game/123',
            sgf_content='(;GM[1]FF[4]SZ[19])',
            output_path='/tmp/ogs_123.sgf',
            metadata={'game_id': '123'},
            timing=timing
        )
        
        assert result.timing['extract_id'] == 0.001
        assert result.timing['api_request'] == 0.5
    
    def test_fetch_result_failure_case(self):
        """测试失败的 FetchResult"""
        from sources import FetchResult
        
        result = FetchResult(
            success=False,
            source='test',
            url='https://test.com/bad',
            sgf_content=None,
            output_path=None,
            error='网络错误',
            metadata={}
        )
        
        assert result.success is False
        assert result.error == '网络错误'
        assert result.sgf_content is None


class TestBaseSourceFetcher:
    """测试 BaseSourceFetcher 基类方法"""
    
    def test_coord_to_sgf_conversion(self):
        """测试坐标转换为SGF格式"""
        from sources import BaseSourceFetcher
        
        # (0,0) 在19路棋盘上应该是左上角 -> SGF中的 aa (左下角)
        # SGF 坐标: a=第1列(左), s=第19列(右)
        #          a=第1行(下), s=第19行(上)
        # OGS: (0,0) = 左上 = 第19行,第1列 -> SGF: a,s
        result = BaseSourceFetcher.coord_to_sgf(0, 0, 19)
        assert result == 'as', f"期望 'as'，但得到 '{result}'"
        
        # (18,18) 在19路棋盘上应该是右下角 -> SGF中的 ss
        result = BaseSourceFetcher.coord_to_sgf(18, 18, 19)
        assert result == 'sa', f"期望 'sa'，但得到 '{result}'"
        
        # (3,3) = 第16行,第4列 -> SGF: d,p
        result = BaseSourceFetcher.coord_to_sgf(3, 3, 19)
        assert result == 'dp', f"期望 'dp'，但得到 '{result}'"
    
    def test_coord_to_sgf_different_board_sizes(self):
        """测试不同棋盘尺寸的坐标转换"""
        from sources import BaseSourceFetcher
        
        # 9路棋盘
        # (0,0) = 左上 = 第9行,第1列 -> SGF: a,i
        result = BaseSourceFetcher.coord_to_sgf(0, 0, 9)
        assert result == 'ai'
        
        # (8,8) = 右下 = 第1行,第9列 -> SGF: i,a
        result = BaseSourceFetcher.coord_to_sgf(8, 8, 9)
        assert result == 'ia'
        
        # 13路棋盘
        result = BaseSourceFetcher.coord_to_sgf(0, 0, 13)
        assert result == 'am'
    
    def test_format_ogs_rank(self):
        """测试OGS段位格式化"""
        from sources import BaseSourceFetcher
        
        # 30+ 为段位 (30 = 1d)
        assert BaseSourceFetcher.format_ogs_rank(30) == '1d'
        assert BaseSourceFetcher.format_ogs_rank(35) == '6d'
        assert BaseSourceFetcher.format_ogs_rank(29) == '1k'
        assert BaseSourceFetcher.format_ogs_rank(25) == '5k'
        assert BaseSourceFetcher.format_ogs_rank(20) == '10k'
        
        # 边界情况 - 0 或 falsy 值返回空字符串
        assert BaseSourceFetcher.format_ogs_rank(0) == ''
        assert BaseSourceFetcher.format_ogs_rank(None) == ''
    
    def test_get_handicap_stones_19x19(self):
        """测试19路标准让子坐标"""
        from sources import BaseSourceFetcher
        
        # 4子让子
        stones = BaseSourceFetcher.get_handicap_stones(4, 19)
        assert len(stones) == 4
        # 标准4子让子位置（0-based）
        assert stones[0] == (15, 3)   # 右上
        assert stones[1] == (3, 15)   # 左下
        assert stones[2] == (15, 15)  # 右下
        assert stones[3] == (3, 3)    # 左上
        
        # 9子让子
        stones = BaseSourceFetcher.get_handicap_stones(9, 19)
        assert len(stones) == 9
        # 天元应该是第9个
        assert stones[8] == (9, 9)
    
    def test_get_handicap_stones_9x9(self):
        """测试9路让子坐标"""
        from sources import BaseSourceFetcher
        
        stones = BaseSourceFetcher.get_handicap_stones(4, 9)
        assert len(stones) == 4
        
        # 9路星位在 (2,2), (6,2), (2,6), (6,6) for 4子
        # t=2 for board_size < 13
        assert stones[0] == (2, 2)
        assert stones[1] == (6, 2)
        assert stones[2] == (2, 6)
        assert stones[3] == (6, 6)
    
    def test_get_default_output_path(self):
        """测试默认输出路径生成"""
        from sources import BaseSourceFetcher
        
        # 创建一个模拟的 fetcher 类（实现抽象方法）
        class TestFetcher(BaseSourceFetcher):
            name = 'test'
            display_name = '测试源'
            url_patterns = []
            
            def fetch(self, url: str, output_path: str = None):
                return None  # 模拟实现
        
        fetcher = TestFetcher()
        path = fetcher.get_default_output_path('12345')
        
        # 验证路径格式
        assert 'test_12345.sgf' in path
        assert '/tmp/weiqi_fetch/' in path
        assert os.path.dirname(path).endswith('/test')
        
        # 清理
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


class TestURLPatternMatching:
    """测试URL模式匹配"""
    
    def test_ogs_url_patterns(self, all_fetcher_classes):
        """测试OGS URL识别"""
        from sources import fetch_ogs
        
        valid_urls = [
            'https://online-go.com/game/12345',
            'https://online-go.com/game/view/67890',
        ]
        
        for url in valid_urls:
            assert fetch_ogs.OgsFetcher.can_handle(url), f"应该能处理: {url}"
            extracted = fetch_ogs.OgsFetcher.extract_id(url)
            assert extracted is not None, f"应该能提取ID: {url}"
        
        # 无效URL
        invalid_urls = [
            'https://example.com/game/123',
            'https://foxwq.com/game/123',
        ]
        
        for url in invalid_urls:
            assert not fetch_ogs.OgsFetcher.can_handle(url), f"不应该处理: {url}"
    
    def test_foxwq_url_patterns(self):
        """测试野狐围棋URL识别"""
        from sources import fetch_fox
        
        valid_urls = [
            'https://h5.foxwq.com/yehunewshare/?chessid=1234567890',
            'https://www.foxwq.com/share?chessid=9876543210',
            'https://foxwq.com/game?chessid=555',
        ]
        
        for url in valid_urls:
            assert fetch_fox.FoxwqFetcher.can_handle(url), f"应该能处理: {url}"
        
        # 测试ID提取
        url = 'https://h5.foxwq.com/yehunewshare/?chessid=12345'
        assert fetch_fox.FoxwqFetcher.extract_id(url) == '12345'
    
    def test_101weiqi_url_patterns(self):
        """测试101围棋网URL识别"""
        from sources import fetch_101
        
        # 101weiqi使用数字ID
        url = 'https://www.101weiqi.com/play/p/12345/'
        assert fetch_101.Weiqi101Fetcher.can_handle(url)
        assert fetch_101.Weiqi101Fetcher.extract_id(url) == '12345'
    
    def test_yike_url_patterns(self):
        """测试弈客围棋URL识别"""
        from sources import fetch_yike
        
        url = 'https://home.yikeweiqi.com/mobile.html#/golive/room/12345/abc'
        assert fetch_yike.YikeWeiqiFetcher.can_handle(url)
    
    def test_yuanluobo_url_patterns(self):
        """测试元萝卜围棋URL识别"""
        from sources import fetch_yuanluobo
        
        url = 'https://jupiter.yuanluobo.com/robot-public/all-in-app/go/review?session_id=test123'
        assert fetch_yuanluobo.YuanluoboFetcher.can_handle(url)
        assert fetch_yuanluobo.YuanluoboFetcher.extract_id(url) == 'test123'
    
    def test_all_fetchers_registered(self, fetcher_registry):
        """测试所有fetcher已注册"""
        # 应该至少有12个fetcher
        assert len(fetcher_registry) >= 12, f"注册数量不足: {len(fetcher_registry)}"
        
        expected_names = [
            'ogs', 'foxwq', 'weiqi101', 'yikeweiqi', 'yuanluobo',
            'golaxy', 'izis', 'yike_shaoer', 'eweiqi', 'txwq',
            'xinboduiyi', 'dzqzd'
        ]
        
        registered_names = [name for name, _, _ in fetcher_registry]
        
        for name in expected_names:
            assert name in registered_names, f"缺少 fetcher: {name}"

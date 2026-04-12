"""
集成测试 - 测试完整流程
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# 标记需要网络访问的测试
requires_network = pytest.mark.skipif(
    os.environ.get('SKIP_NETWORK_TESTS', 'false').lower() == 'true',
    reason='SKIP_NETWORK_TESTS 设置为 true'
)


class TestIntegration:
    """集成测试"""
    
    def test_fetcher_end_to_end_mock(self):
        """测试端到端流程（使用mock）"""
        from sources import get_fetcher_for_url, FetchResult
        from sources import fetch_ogs
        
        # 模拟一个成功的fetch
        mock_result = FetchResult(
            success=True,
            source='ogs',
            url='https://online-go.com/game/12345',
            sgf_content='(;GM[1]FF[4]SZ[19]PB[黑棋]PW[白棋])',
            output_path='/tmp/test_12345.sgf',
            metadata={
                'game_id': '12345',
                'black_name': '黑棋',
                'white_name': '白棋',
                'moves_count': 100,
            },
            timing={'total': 0.5}
        )
        
        # 直接测试 FetchResult 创建和属性访问
        assert mock_result.success is True
        assert mock_result.source == 'ogs'
        assert mock_result.metadata['moves_count'] == 100
        
        # 测试 get_fetcher_for_url 能返回正确的 fetcher
        fetcher = get_fetcher_for_url('https://online-go.com/game/12345')
        assert fetcher is not None
        assert isinstance(fetcher, fetch_ogs.OgsFetcher)
    
    def test_all_fetchers_can_be_instantiated(self):
        """测试所有fetcher都能被实例化"""
        from sources.base import _fetchers
        
        for name, fetcher_class in _fetchers.items():
            try:
                fetcher = fetcher_class()
                assert fetcher is not None
                assert hasattr(fetcher, 'name')
                assert hasattr(fetcher, 'fetch')
            except Exception as e:
                pytest.fail(f"无法实例化 {name}: {e}")
    
    def test_fetcher_with_invalid_url(self):
        """测试fetcher处理无效URL"""
        from sources import get_fetcher_for_url
        
        # 完全不支持的URL
        url = 'https://unknown-site.com/game/123'
        fetcher = get_fetcher_for_url(url)
        assert fetcher is None
    
    def test_fetch_result_serialization(self):
        """测试FetchResult的可序列化性"""
        import json
        from sources import FetchResult
        
        result = FetchResult(
            success=True,
            source='ogs',
            url='https://test.com/game/123',
            sgf_content='(;GM[1]FF[4]SZ[19])',
            output_path='/tmp/test.sgf',
            metadata={'key': 'value', 'number': 123},
            timing={'extract_id': 0.001}
        )
        
        # 转换为字典
        data = {
            'success': result.success,
            'source': result.source,
            'url': result.url,
            'sgf_content': result.sgf_content,
            'output_path': result.output_path,
            'metadata': result.metadata,
            'error': result.error,
            'timing': result.timing,
        }
        
        # JSON序列化
        json_str = json.dumps(data)
        assert json_str is not None
        
        # 反序列化
        restored = json.loads(json_str)
        assert restored['success'] is True
        assert restored['source'] == 'ogs'
        assert restored['metadata']['key'] == 'value'


class TestErrorHandling:
    """测试错误处理"""
    
    def test_fetch_with_network_error(self):
        """测试网络错误处理"""
        from sources import fetch_ogs
        from unittest.mock import patch
        
        fetcher = fetch_ogs.OgsFetcher()
        
        # 模拟网络错误
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception('Connection refused')
            
            result = fetcher.fetch('https://online-go.com/game/12345')
            assert result.success is False
            assert 'Connection refused' in result.error or 'API请求失败' in result.error
    
    def test_fetch_with_invalid_id(self):
        """测试无效ID处理"""
        from sources import fetch_ogs
        
        fetcher = fetch_ogs.OgsFetcher()
        
        # 无法提取ID的URL
        result = fetcher.fetch('https://online-go.com/invalid')
        assert result.success is False
        assert result.error is not None
        assert '无法从URL提取游戏ID' in result.error
    
    def test_fetch_with_api_error_response(self):
        """测试API错误响应处理"""
        from sources import fetch_ogs
        from unittest.mock import patch, MagicMock
        
        fetcher = fetch_ogs.OgsFetcher()
        
        # 模拟API返回错误
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception('404 Not Found')
        
        with patch('requests.get', return_value=mock_response):
            result = fetcher.fetch('https://online-go.com/game/12345')
            assert result.success is False
            assert '404' in result.error or 'API请求失败' in result.error


class TestPlatformSpecificLogic:
    """测试平台特定逻辑"""
    
    def test_ogs_rules_mapping(self):
        """测试OGS规则映射"""
        from sources import fetch_ogs
        
        fetcher = fetch_ogs.OgsFetcher()
        
        game_data = {
            'moves': [],
            'width': 19,
            'height': 19,
            'komi': 6.5,
            'handicap': 0,
            'rules': 'chinese',
        }
        
        metadata = {
            'black_name': 'B',
            'white_name': 'W',
            'komi': 7.5,
            'result': '?',
            'handicap': 0,
            'rules': 'chinese',
            'width': 19,
            'height': 19,
            'black_rank': '',
            'white_rank': '',
            'date': '',
        }
        
        sgf = fetcher._generate_sgf(game_data, metadata)
        assert 'RU[CN]' in sgf  # chinese -> CN
        
        # 测试其他规则
        for rules, expected in [
            ('japanese', 'RU[JP]'),
            ('korean', 'RU[KO]'),
            ('aga', 'RU[AGA]'),
            ('ing', 'RU[ING]'),
        ]:
            game_data['rules'] = rules
            metadata['rules'] = rules
            sgf = fetcher._generate_sgf(game_data, metadata)
            assert expected in sgf, f"规则 {rules} 应该映射为 {expected}"
    
    def test_ogs_pass_move(self):
        """测试OGS虚手(passen)处理"""
        from sources import fetch_ogs
        
        fetcher = fetch_ogs.OgsFetcher()
        
        game_data = {
            'moves': [[3, 3], [-1, -1], [15, 15]],  # 包含虚手
            'width': 19,
            'height': 19,
            'komi': 6.5,
            'handicap': 0,
            'rules': 'japanese',
        }
        
        metadata = {
            'black_name': 'B',
            'white_name': 'W',
            'komi': 6.5,
            'result': '?',
            'handicap': 0,
            'rules': 'japanese',
            'width': 19,
            'height': 19,
            'black_rank': '',
            'white_rank': '',
            'date': '',
        }
        
        sgf = fetcher._generate_sgf(game_data, metadata)
        assert ';B[dp]' in sgf  # (3,3) -> dp
        assert ';W[]' in sgf    # 虚手
        assert ';B[pd]' in sgf  # (15,15) -> pd

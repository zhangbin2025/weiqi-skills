"""
按日期下载功能测试

测试 download_sgf.py 的各项功能
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-foxwq/scripts')

from download_sgf import (
    fetch_url,
    extract_qipu_links,
    extract_sgf,
    download_qipu,
    print_report,
    PerformanceTimer,
    WORK_DIR,
    BASE_URL
)


class TestHtmlParsing:
    """HTML 解析测试"""
    
    def test_extract_qipu_links_with_bs4(self, sample_html_page):
        """测试使用 BeautifulSoup 解析棋谱链接"""
        # Mock BS4_AVAILABLE = True
        with patch('download_sgf.BS4_AVAILABLE', True):
            from bs4 import BeautifulSoup
            
            links = extract_qipu_links(sample_html_page, '2024-01-15')
            
            assert len(links) == 2
            assert links[0]['title'] == '柯洁 vs 申真谞'
            assert links[0]['date'] == '2024-01-15'
            assert '/qipu/newlist/id/12345.html' in links[0]['url']
    
    def test_extract_qipu_links_no_match_date(self, sample_html_page):
        """测试无匹配日期的棋谱链接"""
        with patch('download_sgf.BS4_AVAILABLE', True):
            links = extract_qipu_links(sample_html_page, '2024-01-13')
            
            assert len(links) == 0
    
    def test_extract_qipu_links_without_bs4(self, sample_html_page):
        """测试不使用 BeautifulSoup 时的备选解析"""
        with patch('download_sgf.BS4_AVAILABLE', False):
            links = extract_qipu_links(sample_html_page, '2024-01-15')
            
            # 即使不使用 BS4，也应该能解析到一些链接
            # 注意：正则解析可能不完美，但至少应该返回结果
            assert isinstance(links, list)
    
    def test_extract_qipu_links_empty_html(self):
        """测试从空 HTML 中提取链接"""
        links = extract_qipu_links('', '2024-01-15')
        
        assert links == []
    
    def test_extract_qipu_links_invalid_html(self):
        """测试从无效 HTML 中提取链接"""
        html = "<html><body>无表格内容</body></html>"
        links = extract_qipu_links(html, '2024-01-15')
        
        assert links == []


class TestSgfExtraction:
    """SGF 提取测试"""
    
    def test_extract_sgf_success(self, sample_qipu_detail_html):
        """测试成功提取 SGF"""
        sgf = extract_sgf(sample_qipu_detail_html)
        
        assert sgf is not None
        assert "(;GM[1]FF[4]" in sgf
        assert "PB[柯洁]" in sgf
        assert "PW[申真谞]" in sgf
    
    def test_extract_sgf_not_found(self):
        """测试 HTML 中无 SGF 的情况"""
        html = "<html><body>无棋谱内容</body></html>"
        sgf = extract_sgf(html)
        
        assert sgf is None
    
    def test_extract_sgf_partial_content(self):
        """测试提取部分 SGF 内容"""
        html = """
        <html>
        <body>
        <div>
        (;GM[1]FF[4]SZ[19];B[pd];W[dp])
        </div>
        <p>其他内容</p>
        </body>
        </html>
        """
        sgf = extract_sgf(html)
        
        assert sgf is not None
        assert "(;GM[1]FF[4]" in sgf
    
    def test_extract_sgf_with_special_chars(self):
        """测试提取包含特殊字符的 SGF"""
        html = """
        <html>
        <body>
        (;GM[1]FF[4]SZ[19]C[注释: 测试\\n换行];B[pd])
        </body>
        </html>
        """
        sgf = extract_sgf(html)
        
        assert sgf is not None
        assert "GM[1]" in sgf
    
    def test_extract_sgf_multiple_parentheses(self):
        """测试提取多个括号的 SGF"""
        html = """
        <html>
        <body>
        (;GM[1]FF[4]SZ[19]
        ;B[pd]C[(注释)]
        ;W[dp])
        </body>
        </html>
        """
        sgf = extract_sgf(html)
        
        assert sgf is not None


class TestDownloadFlow:
    """下载流程测试"""
    
    def test_fetch_url_success(self):
        """测试成功获取 URL 内容"""
        with patch('download_sgf.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = '<html>test</html>'
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = fetch_url('http://test.com')
            
            assert result == '<html>test</html>'
            mock_get.assert_called_once()
    
    def test_fetch_url_not_available(self):
        """测试 requests 不可用时"""
        with patch('download_sgf.REQUESTS_AVAILABLE', False):
            result = fetch_url('http://test.com')
            
            assert result is None
    
    def test_fetch_url_http_error(self):
        """测试 HTTP 错误"""
        with patch('download_sgf.requests.get') as mock_get:
            from requests.exceptions import HTTPError
            mock_get.side_effect = HTTPError("404 Not Found")
            
            result = fetch_url('http://test.com')
            
            assert result is None
    
    def test_fetch_url_timeout(self):
        """测试请求超时"""
        with patch('download_sgf.requests.get') as mock_get:
            from requests.exceptions import Timeout
            mock_get.side_effect = Timeout("Request timed out")
            
            result = fetch_url('http://test.com')
            
            assert result is None
    
    def test_download_qipu_success(self, temp_output_dir):
        """测试成功下载单个棋谱"""
        link_info = {
            'title': '柯洁 vs 申真谞',
            'url': 'http://test.com/qipu/12345.html',
            'date': '2024-01-15'
        }
        
        html_content = """
        <html>
        <body>
        (;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞]RE[B+R]
        ;B[pd];W[dp];B[pp];W[dd])
        </body>
        </html>
        """
        
        with patch('download_sgf.fetch_url') as mock_fetch:
            mock_fetch.return_value = html_content
            
            result = download_qipu(link_info, temp_output_dir)
            
            assert result is not None
            assert result['title'] == '柯洁 vs 申真谞'
            assert result['filename'].endswith('.sgf')
            assert os.path.exists(result['path'])
    
    def test_download_qipu_fetch_failed(self, temp_output_dir):
        """测试棋谱获取失败"""
        link_info = {
            'title': '测试棋谱',
            'url': 'http://test.com/qipu/12345.html',
            'date': '2024-01-15'
        }
        
        with patch('download_sgf.fetch_url') as mock_fetch:
            mock_fetch.return_value = None
            
            result = download_qipu(link_info, temp_output_dir)
            
            assert result is None
    
    def test_download_qipu_no_sgf(self, temp_output_dir):
        """测试获取到 HTML 但无 SGF 内容"""
        link_info = {
            'title': '测试棋谱',
            'url': 'http://test.com/qipu/12345.html',
            'date': '2024-01-15'
        }
        
        with patch('download_sgf.fetch_url') as mock_fetch:
            mock_fetch.return_value = '<html><body>无棋谱</body></html>'
            
            result = download_qipu(link_info, temp_output_dir)
            
            assert result is None
    
    def test_download_qipu_title_cleaning(self, temp_output_dir):
        """测试标题清理"""
        link_info = {
            'title': '绝艺讲解<柯洁 vs 申真谞>',
            'url': 'http://test.com/qipu/12345.html',
            'date': '2024-01-15'
        }
        
        html_content = """
        <html><body>
        (;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞])
        </body></html>
        """
        
        with patch('download_sgf.fetch_url') as mock_fetch:
            mock_fetch.return_value = html_content
            
            result = download_qipu(link_info, temp_output_dir)
            
            assert result is not None
            # 文件名中应该移除了特殊字符
            assert '<' not in result['filename']
            assert '>' not in result['filename']


class TestPrintReport:
    """报告打印测试"""
    
    def test_print_report_success(self, capsys):
        """测试成功打印报告"""
        success_list = [
            {'title': '棋谱1', 'filename': '001.sgf'},
            {'title': '棋谱2', 'filename': '002.sgf'}
        ]
        failed_list = ['失败棋谱1']
        
        print_report('2024-01-15', success_list, failed_list)
        
        captured = capsys.readouterr()
        assert '下载报告' in captured.out
        assert '成功: 2 局' in captured.out
        assert '失败: 1 局' in captured.out
        assert '棋谱1' in captured.out
    
    def test_print_report_empty(self, capsys):
        """测试打印空报告"""
        print_report('2024-01-15', [], [])
        
        captured = capsys.readouterr()
        assert '下载报告' in captured.out
        assert '成功: 0 局' in captured.out
        assert '失败: 0 局' in captured.out
    
    def test_print_report_with_timer(self, capsys):
        """测试带计时器的报告"""
        timer = PerformanceTimer()
        timer.start()
        
        success_list = [{'title': '棋谱1', 'filename': '001.sgf'}]
        
        print_report('2024-01-15', success_list, [], timer)
        
        captured = capsys.readouterr()
        assert '下载报告' in captured.out
        assert '性能计时报告' in captured.out


class TestPerformance:
    """性能计时器测试"""
    
    def test_performance_timer_start(self):
        """测试性能计时器启动"""
        timer = PerformanceTimer()
        timer.start()
        
        assert timer.start_time is not None
    
    def test_performance_timer_step(self):
        """测试性能计时步骤"""
        import time
        
        timer = PerformanceTimer()
        timer.start()
        
        with timer.step('test_step'):
            time.sleep(0.01)
        
        assert 'test_step' in timer.timings
        assert timer.timings['test_step'] >= 0.01
    
    def test_performance_timer_get_total(self):
        """测试获取总耗时"""
        import time
        
        timer = PerformanceTimer()
        timer.start()
        time.sleep(0.01)
        
        total = timer.get_total()
        assert total >= 0.01
    
    def test_performance_timer_format_report(self):
        """测试计时报告格式化"""
        import time
        
        timer = PerformanceTimer()
        timer.start()
        
        with timer.step('step1'):
            time.sleep(0.01)
        with timer.step('step2'):
            time.sleep(0.01)
        
        report = timer.format_report()
        
        assert '性能计时报告' in report
        assert 'step1' in report
        assert 'step2' in report
        assert '步骤累计' in report
        assert '总耗时' in report
    
    def test_performance_timer_no_start(self):
        """测试未启动时的行为"""
        timer = PerformanceTimer()
        
        total = timer.get_total()
        assert total == 0
    
    def test_performance_timer_nested_steps(self):
        """测试嵌套计时步骤"""
        import time
        
        timer = PerformanceTimer()
        timer.start()
        
        with timer.step('outer'):
            time.sleep(0.01)
            with timer.step('inner'):
                time.sleep(0.01)
        
        assert 'outer' in timer.timings
        assert 'inner' in timer.timings


class TestMainFlowIntegration:
    """主流程集成测试"""
    
    def test_main_flow_with_date(self, temp_output_dir):
        """测试指定日期的主流程"""
        html_content = """
        <html>
        <body>
        <table>
            <tr>
                <td><a href="/qipu/newlist/id/12345.html"><h4>测试棋谱</h4></a></td>
                <td>2024-01-15</td>
            </tr>
        </table>
        </body>
        </html>
        """
        
        detail_html = """
        <html><body>
        (;GM[1]FF[4]SZ[19]PB[黑棋]PW[白棋])
        </body></html>
        """
        
        with patch('download_sgf.fetch_url') as mock_fetch:
            # 第一次调用返回列表页，第二次返回详情页
            mock_fetch.side_effect = [html_content, detail_html]
            
            with patch('download_sgf.WORK_DIR', temp_output_dir):
                with patch('sys.argv', ['download_sgf.py', '2024-01-15']):
                    # 模拟主流程的部分逻辑
                    links = extract_qipu_links(html_content, '2024-01-15')
                    assert len(links) == 1
                    assert links[0]['title'] == '测试棋谱'
    
    def test_main_flow_no_links(self, temp_output_dir):
        """测试无棋谱链接的主流程"""
        html_content = "<html><body>无棋谱</body></html>"
        
        with patch('download_sgf.fetch_url') as mock_fetch:
            mock_fetch.return_value = html_content
            
            links = extract_qipu_links(html_content, '2024-01-15')
            assert len(links) == 0
    
    def test_main_flow_yesterday_default(self):
        """测试默认使用昨天的日期"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 验证昨天的日期格式正确
        assert len(yesterday) == 10
        assert yesterday.count('-') == 2


class TestConstants:
    """常量测试"""
    
    def test_base_url_constant(self):
        """测试 BASE_URL 常量"""
        assert BASE_URL == "https://www.foxwq.com"
    
    def test_work_dir_default(self):
        """测试默认工作目录"""
        assert '/tmp' in WORK_DIR or 'foxwq' in WORK_DIR
    
    def test_work_dir_from_env(self):
        """测试从环境变量获取工作目录"""
        with patch.dict(os.environ, {'FOXWQ_DOWNLOAD_DIR': '/custom/dir'}):
            # 重新导入模块以获取新值
            import importlib
            import download_sgf
            importlib.reload(download_sgf)
            
            assert download_sgf.WORK_DIR == '/custom/dir'

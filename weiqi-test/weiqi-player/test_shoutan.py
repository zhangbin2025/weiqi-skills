#!/usr/bin/env python3
"""
weiqi-player 手谈查询测试

测试范围:
- PerformanceTimer 性能计时器
- parse_shoutan_basic HTML解析
- format_player_info_single_line 格式化
- query_shoutan 查询流程（mock）
"""

import sys
import base64
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "weiqi-player" / "scripts"))

import pytest
from query_shoutan import (
    PerformanceTimer,
    parse_shoutan_basic,
    format_player_info_single_line,
    query_shoutan,
)


# ===== Fixtures =====

@pytest.fixture
def sample_shoutan_html():
    """示例手谈查询返回的 HTML"""
    return """
    <html>
    <script>
    var DataTxt = '<PkList><Xs 编号="12345" 等级分="2500.0" 省份="江苏省" 地区="南京市" 对局次数="100" 参赛次数="50" 注册日期="2020-01-01" 注册等级分="2000.0" 全国排名="123" 省份排名="10" 地区排名="2" 称谓="6.2d"/><Xs 编号="67890" 等级分="2100.0" 省份="浙江省" 地区="杭州市" 对局次数="80" 参赛次数="40" 注册日期="2019-06-01" 注册等级分="1800.0" 全国排名="456" 省份排名="20" 地区排名="5" 称谓="3.1d"/></PkList>';
    var RediTxt = '<Redi Ns="Sp" Jk="选手查询" Yh="987654321"/>';
    </script>
    </html>
    """


@pytest.fixture
def sample_shoutan_html_single():
    """单选手的 HTML"""
    return """
    <html>
    <script>
    var DataTxt = '<PkList><Xs 编号="11111" 等级分="2800.0" 省份="北京市" 地区="海淀区" 对局次数="200" 参赛次数="100" 注册日期="2018-01-01" 注册等级分="2200.0" 全国排名="1" 省份排名="1" 地区排名="1" 称谓="9.9d"/></PkList>';
    var RediTxt = '<Redi Ns="Sp" Jk="选手查询" Yh="111222333"/>';
    </script>
    </html>
    """


@pytest.fixture
def sample_shoutan_empty():
    """空结果的 HTML"""
    return """
    <html>
    <script>
    var DataTxt = '<PkList></PkList>';
    </script>
    </html>
    """


# ===== PerformanceTimer Tests =====

class TestPerformanceTimer:
    """性能计时器测试"""

    def test_timer_initialization(self):
        """测试计时器初始化"""
        timer = PerformanceTimer()
        assert timer.start_time is None
        assert len(timer.timings) == 0

    def test_timer_start(self):
        """测试开始计时"""
        timer = PerformanceTimer()
        timer.start()
        assert timer.start_time is not None
        assert timer.start_time <= time.time()

    def test_timer_step_context_manager(self):
        """测试步骤计时上下文管理器"""
        timer = PerformanceTimer()
        timer.start()
        
        with timer.step("测试步骤"):
            time.sleep(0.01)
        
        assert "测试步骤" in timer.timings
        assert timer.timings["测试步骤"] >= 0.01

    def test_timer_multiple_steps(self):
        """测试多个步骤计时"""
        timer = PerformanceTimer()
        timer.start()
        
        with timer.step("步骤1"):
            time.sleep(0.01)
        with timer.step("步骤2"):
            time.sleep(0.01)
        
        assert len(timer.timings) == 2
        assert "步骤1" in timer.timings
        assert "步骤2" in timer.timings

    def test_timer_format_report(self):
        """测试报告格式化"""
        timer = PerformanceTimer()
        timer.start()
        
        with timer.step("步骤A"):
            time.sleep(0.01)
        with timer.step("步骤B"):
            time.sleep(0.01)
        
        report = timer.format_report()
        assert "性能计时报告" in report
        assert "步骤A" in report
        assert "步骤B" in report
        assert "总耗时" in report

    def test_timer_get_total(self):
        """测试获取总耗时"""
        timer = PerformanceTimer()
        timer.start()
        time.sleep(0.01)
        
        total = timer.get_total()
        assert total >= 0.01


# ===== Parse Shoutan Tests =====

class TestParseShoutanBasic:
    """解析手谈 HTML 测试"""

    def test_parse_single_player(self, sample_shoutan_html_single):
        """测试解析单个选手"""
        players = parse_shoutan_basic(sample_shoutan_html_single, "测试棋手")
        
        assert len(players) == 1
        player = players[0]
        
        assert player["姓名"] == "测试棋手"
        assert player["编号"] == "11111"
        assert player["等级分"] == "2800.0"
        assert player["省份"] == "北京市"
        assert player["地区"] == "海淀区"
        assert player["对局次数"] == "200"
        assert player["参赛次数"] == "100"
        assert player["注册日期"] == "2018-01-01"
        assert player["注册等级分"] == "2200.0"
        assert player["全国排名"] == "1"
        assert player["省份排名"] == "1"
        assert player["地区排名"] == "1"
        assert player["称谓"] == "9.9d"
        assert player["Yh"] == "111222333"

    def test_parse_multiple_players(self, sample_shoutan_html):
        """测试解析多个同名选手"""
        players = parse_shoutan_basic(sample_shoutan_html, "同名测试")
        
        assert len(players) == 2
        
        # 第一个选手
        assert players[0]["编号"] == "12345"
        assert players[0]["地区"] == "南京市"
        
        # 第二个选手
        assert players[1]["编号"] == "67890"
        assert players[1]["地区"] == "杭州市"
        
        # 两个选手应该有相同的 Yh
        assert players[0]["Yh"] == players[1]["Yh"] == "987654321"

    def test_parse_empty_result(self, sample_shoutan_empty):
        """测试解析空结果"""
        players = parse_shoutan_basic(sample_shoutan_empty, "不存在")
        assert len(players) == 0

    def test_parse_malformed_html(self):
        """测试解析格式错误的 HTML"""
        html = "<html>无数据</html>"
        players = parse_shoutan_basic(html, "测试")
        assert len(players) == 0


# ===== Format Tests =====

class TestFormatPlayerInfo:
    """格式化输出测试"""

    def test_format_full_info(self):
        """测试完整信息格式化"""
        player = {
            "姓名": "张三",
            "地区": "北京",
            "称谓": "6.2d",
            "等级分": "2500.0",
            "全国排名": "123",
            "对局次数": "100",
        }
        result = format_player_info_single_line(player)
        
        assert "**张三**" in result
        assert "(北京)" in result
        assert "段位: 6.2d" in result
        assert "等级分: 2500.0" in result
        assert "全国排名: 123" in result
        assert "对局: 100局" in result

    def test_format_partial_info(self):
        """测试部分信息格式化"""
        player = {
            "姓名": "李四",
            "地区": "上海",
            "称谓": "3.1d",
            "等级分": None,
            "全国排名": "456",
            "对局次数": None,
        }
        result = format_player_info_single_line(player)
        
        assert "**李四**" in result
        assert "(上海)" in result
        assert "段位: 3.1d" in result
        assert "等级分:" not in result  # None 值不应显示
        assert "全国排名: 456" in result
        assert "对局:" not in result  # None 值不应显示

    def test_format_minimal_info(self):
        """测试最少信息格式化"""
        player = {
            "姓名": "王五",
            "地区": "广州",
        }
        result = format_player_info_single_line(player)
        
        assert "**王五**" in result
        assert "(广州)" in result


# ===== Query Integration Tests =====

class TestQueryShoutan:
    """查询功能集成测试（使用 mock）"""

    @patch('query_shoutan.fetch_url')
    def test_query_success(self, mock_fetch, sample_shoutan_html_single):
        """测试成功查询"""
        mock_fetch.return_value = sample_shoutan_html_single
        
        timer = PerformanceTimer()
        timer.start()
        
        players = query_shoutan("测试棋手", timer)
        
        assert len(players) == 1
        assert players[0]["姓名"] == "测试棋手"
        assert "构造查询参数" in timer.timings
        assert "HTTP请求" in timer.timings
        assert "解析HTML" in timer.timings

    @patch('query_shoutan.fetch_url')
    def test_query_multiple_namesakes(self, mock_fetch, sample_shoutan_html):
        """测试查询多个同名选手"""
        mock_fetch.return_value = sample_shoutan_html
        
        timer = PerformanceTimer()
        timer.start()
        
        players = query_shoutan("同名棋手", timer)
        
        assert len(players) == 2
        assert players[0]["地区"] == "南京市"
        assert players[1]["地区"] == "杭州市"

    @patch('query_shoutan.fetch_url')
    def test_query_empty_result(self, mock_fetch, sample_shoutan_empty):
        """测试查询无结果"""
        mock_fetch.return_value = sample_shoutan_empty
        
        timer = PerformanceTimer()
        timer.start()
        
        players = query_shoutan("不存在的棋手", timer)
        
        assert len(players) == 0

    @patch('query_shoutan.fetch_url')
    def test_query_network_error(self, mock_fetch):
        """测试网络错误处理"""
        mock_fetch.side_effect = Exception("网络超时")
        
        timer = PerformanceTimer()
        timer.start()
        
        players = query_shoutan("测试棋手", timer)
        
        assert len(players) == 0

    @patch('query_shoutan.fetch_url')
    def test_query_url_encoding(self, mock_fetch, sample_shoutan_html_single):
        """测试 URL 编码正确性"""
        mock_fetch.return_value = sample_shoutan_html_single
        
        timer = PerformanceTimer()
        timer.start()
        
        query_shoutan("测试姓名", timer)
        
        # 检查 fetch_url 被调用的参数
        call_args = mock_fetch.call_args
        url = call_args[0][0]
        
        # URL 应该包含 base64 编码的参数
        assert "v.dzqzd.com" in url
        assert "?r=" in url
        
        # 解码验证
        encoded = url.split("?r=")[1]
        decoded = base64.b64decode(encoded).decode('utf-8')
        assert "测试姓名" in decoded
        assert 'Jk="选手查询"' in decoded


# ===== Utility Tests =====

class TestUtilityFunctions:
    """工具函数测试"""

    def test_base64_encoding_chinese(self):
        """测试中文字符的 base64 编码"""
        xml = '<Redi Ns="Sp" Jk="选手查询" 姓名="柯洁"/>'
        encoded = base64.b64encode(xml.encode('utf-8')).decode('utf-8')
        decoded = base64.b64decode(encoded).decode('utf-8')
        
        assert decoded == xml
        assert "柯洁" in decoded

    def test_url_construction(self):
        """测试 URL 构造"""
        xml = '<Redi Ns="Sp" Jk="选手查询" 姓名="测试"/>'
        encoded = base64.b64encode(xml.encode('utf-8')).decode('utf-8')
        url = f"https://v.dzqzd.com/SpBody.aspx?r={encoded}"
        
        assert url.startswith("https://v.dzqzd.com/SpBody.aspx?r=")
        assert encoded in url

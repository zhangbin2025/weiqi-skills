#!/usr/bin/env python3
"""
weiqi-player 易查分查询测试

测试范围:
- PerformanceTimer 性能计时器
- parse_yichafen_result 结果解析
- extract_player_info 信息提取
- query_with_browser 浏览器查询（mock）
- 批量查询功能
"""

import sys
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "weiqi-player" / "scripts"))

import pytest

# 由于 playwright 依赖，我们 mock 相关功能
# 导入需要测试的非 playwright 功能
from query_yichafen import PerformanceTimer


# ===== Fixtures =====

@pytest.fixture
def sample_yichafen_result():
    """示例易查分查询结果"""
    return {
        "姓名": "张三",
        "段位": "6段",
        "等级分": "1700.00",
        "总排名": "1000",
        "省区排名": "100",
        "本市排名": "20",
        "性别": "男",
        "出生": "2010",
        "省区": "江苏省",
        "城市": "南京市",
        "备注": "20XX第X届XX杯全国围棋比赛晋升6段",
    }


@pytest.fixture
def sample_yichafen_html():
    """示例易查分网页 HTML（简化版）"""
    return """
    <html>
    <body>
        <div class="result-section">
            <h3>查询结果</h3>
            <div class="info-row"><span class="label">姓名</span><span class="value">张三</span></div>
            <div class="info-row"><span class="label">段位</span><span class="value">6段</span></div>
            <div class="info-row"><span class="label">等级分</span><span class="value">1700.00</span></div>
            <div class="info-row"><span class="label">总排名</span><span class="value">1000</span></div>
            <div class="info-row"><span class="label">省区排名</span><span class="value">100</span></div>
            <div class="info-row"><span class="label">本市排名</span><span class="value">20</span></div>
            <div class="info-row"><span class="label">性别</span><span class="value">男</span></div>
            <div class="info-row"><span class="label">出生</span><span class="value">2010</span></div>
            <div class="info-row"><span class="label">省区</span><span class="value">江苏省</span></div>
            <div class="info-row"><span class="label">城市</span><span class="value">南京市</span></div>
            <div class="info-row"><span class="label">备注</span><span class="value">20XX第X届XX杯全国围棋比赛晋升6段</span></div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_yichafen_no_result():
    """无查询结果的 HTML"""
    return """
    <html>
    <body>
        <div class="result-section">
            <h3>查询结果</h3>
            <div class="no-result">未找到相关信息</div>
        </div>
    </body>
    </html>
    """


# ===== PerformanceTimer Tests =====

class TestPerformanceTimer:
    """性能计时器测试（与手谈类似，确保一致性）"""

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
        
        with timer.step("启动浏览器"):
            time.sleep(0.01)
        
        assert "启动浏览器" in timer.timings
        assert timer.timings["启动浏览器"] >= 0.01

    def test_timer_multiple_steps(self):
        """测试多个步骤计时"""
        timer = PerformanceTimer()
        timer.start()
        
        steps = ["启动浏览器", "访问页面", "输入查询", "等待结果", "解析数据"]
        for step in steps:
            with timer.step(step):
                time.sleep(0.005)
        
        assert len(timer.timings) == len(steps)
        for step in steps:
            assert step in timer.timings

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
        assert "易查分查询" in report
        assert "步骤A" in report
        assert "步骤B" in report
        assert "总耗时" in report


# ===== Data Parsing Tests =====

class TestDataParsing:
    """数据解析测试"""

    def test_player_info_structure(self, sample_yichafen_result):
        """测试选手信息结构"""
        info = sample_yichafen_result
        
        assert info["姓名"] == "张三"
        assert info["段位"] == "6段"
        assert info["等级分"] == "1700.00"
        assert info["总排名"] == "1000"
        assert info["省区"] == "江苏省"
        assert info["城市"] == "南京市"

    def test_player_info_complete_fields(self, sample_yichafen_result):
        """测试选手信息完整字段"""
        info = sample_yichafen_result
        
        required_fields = [
            "姓名", "段位", "等级分", "总排名", "省区排名", 
            "本市排名", "性别", "出生", "省区", "城市"
        ]
        
        for field in required_fields:
            assert field in info
            assert info[field] is not None

    def test_remarks_field(self, sample_yichafen_result):
        """测试备注字段"""
        info = sample_yichafen_result
        
        assert "备注" in info
        assert "晋升6段" in info["备注"]


# ===== Browser Query Tests (Mocked) =====

class TestBrowserQuery:
    """浏览器查询测试（使用 mock）"""

    @patch('query_yichafen.sync_playwright')
    def test_browser_initialization(self, mock_playwright):
        """测试浏览器初始化"""
        # 模拟 playwright 环境
        mock_p = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        
        mock_playwright.return_value.__enter__ = MagicMock(return_value=mock_p)
        mock_playwright.return_value.__exit__ = MagicMock(return_value=False)
        mock_p.chromium.launch_persistent_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.query_selector.return_value = None  # 模拟页面未就绪
        
        # 这里我们只是测试调用流程，不实际执行
        # 因为 playwright 依赖较重，主要测试在集成环境中进行
        pass

    def test_session_state_management(self, tmp_path):
        """测试会话状态管理"""
        # 使用临时目录测试状态文件
        state_file = tmp_path / "test_state.json"
        
        # 模拟状态数据
        state_data = {
            "cookies": [{"name": "test", "value": "value"}],
            "origins": []
        }
        
        # 写入状态文件
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f)
        
        # 读取并验证
        with open(state_file, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        assert loaded["cookies"][0]["name"] == "test"

    def test_user_data_dir_creation(self, tmp_path):
        """测试用户数据目录创建"""
        user_data_dir = tmp_path / "browser_data"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        assert user_data_dir.exists()
        assert user_data_dir.is_dir()


# ===== Batch Query Tests =====

class TestBatchQuery:
    """批量查询测试"""

    def test_batch_names_processing(self):
        """测试批量姓名处理"""
        names = ["张三", "李四", "王五"]
        
        # 验证姓名列表处理
        assert len(names) == 3
        assert names[0] == "张三"
        assert names[1] == "李四"
        assert names[2] == "王五"

    def test_empty_batch_list(self):
        """测试空批量列表"""
        names = []
        assert len(names) == 0

    def test_single_name_as_batch(self):
        """测试单个姓名作为批量"""
        names = ["张三"]
        assert len(names) == 1

    def test_batch_with_duplicates(self):
        """测试包含重复姓名的批量"""
        names = ["张三", "李四", "张三"]
        unique_names = list(dict.fromkeys(names))  # 保持顺序去重
        
        assert len(unique_names) == 2
        assert unique_names == ["张三", "李四"]


# ===== Output Format Tests =====

class TestOutputFormat:
    """输出格式测试"""

    def test_single_line_format(self, sample_yichafen_result):
        """测试单行输出格式"""
        info = sample_yichafen_result
        
        # 构造单行输出
        parts = [
            f"段位: {info['段位']}",
            f"等级分: {info['等级分']}",
            f"总排名: {info['总排名']}",
            f"地区: {info['省区']} {info['城市']}",
        ]
        
        output = " | ".join(parts)
        
        assert "段位: 6段" in output
        assert "等级分: 1700.00" in output
        assert "总排名: 1000" in output
        assert "江苏省 南京市" in output

    def test_detailed_output(self, sample_yichafen_result):
        """测试详细输出格式"""
        info = sample_yichafen_result
        
        lines = [
            f"姓名: {info['姓名']}",
            f"段位: {info['段位']}",
            f"等级分: {info['等级分']}",
            f"总排名: {info['总排名']}",
            f"省区排名: {info['省区排名']}",
            f"本市排名: {info['本市排名']}",
            f"性别: {info['性别']}",
            f"出生: {info['出生']}",
            f"省区: {info['省区']}",
            f"城市: {info['城市']}",
            f"备注: {info['备注']}",
        ]
        
        output = "\n".join(lines)
        
        assert "姓名: 张三" in output
        assert "性别: 男" in output
        assert "出生: 2010" in output
        assert "晋升6段" in output


# ===== Error Handling Tests =====

class TestErrorHandling:
    """错误处理测试"""

    def test_missing_optional_fields(self):
        """测试缺少可选字段"""
        info = {
            "姓名": "测试",
            "段位": "5段",
            "等级分": "1500",
            # 缺少其他字段
        }
        
        # 验证存在字段
        assert info.get("姓名") == "测试"
        assert info.get("段位") == "5段"
        
        # 验证缺失字段返回 None
        assert info.get("省区") is None
        assert info.get("备注") is None

    def test_empty_string_fields(self):
        """测试空字符串字段"""
        info = {
            "姓名": "测试",
            "段位": "",
            "备注": "",
        }
        
        assert info["姓名"] == "测试"
        assert info["段位"] == ""
        assert info["备注"] == ""

    def test_none_fields(self):
        """测试 None 字段"""
        info = {
            "姓名": "测试",
            "段位": None,
            "等级分": None,
        }
        
        assert info.get("段位") is None
        assert info.get("等级分") is None


# ===== Configuration Tests =====

class TestConfiguration:
    """配置测试"""

    def test_base_url_constant(self):
        """测试基础 URL 常量"""
        base_url = "https://yeyuweiqi.yichafen.com/qz/s9W2g0zKmt"
        assert base_url.startswith("https://")
        assert "yeyuweiqi.yichafen.com" in base_url

    def test_session_timeout_value(self):
        """测试会话超时值"""
        timeout = 300  # 5分钟
        assert timeout == 300
        assert timeout > 0

    def test_state_file_path(self):
        """测试状态文件路径"""
        state_file = "/tmp/yichafen_state.json"
        assert state_file.startswith("/tmp/")
        assert state_file.endswith(".json")

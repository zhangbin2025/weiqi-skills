#!/usr/bin/env python3
"""
weiqi-player 易查分查询测试

测试范围:
- query_player 查询功能
- parse_player_info 结果解析
- create_session 会话创建
- 输出格式
- 错误处理
"""

import sys
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "weiqi-player" / "scripts"))

import pytest


# ===== Fixtures =====

@pytest.fixture
def sample_yichafen_result():
    """示例易查分查询结果（符合 query_player 返回格式）"""
    return {
        "found": True,
        "name": "田翔宇",
        "info": {
            "name": "田翔宇",
            "level": "6段",
            "rating": "2037.70",
            "rank_total": "777",
            "rank_province": "56",
            "rank_city": "14",
            "gender": "男",
            "birth_year": "2012",
            "province": "广东",
            "city": "深圳",
            "note": '2025第三届"深圳杯"业余围棋公开赛青少年甲组第一名晋升6段'
        },
        "elapsed": 0.35
    }


@pytest.fixture
def sample_yichafen_html():
    """示例易查分网页 HTML"""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div id="wrapper">
            <div id="result_content">
                <div id="result_data_table">
                    <div style="text-align:center;padding:10px;margin-bottom:10px;background:#0166CC;color:#FFFFFF;">
                        <div style="font-size:36px;">田翔宇</div>
                    </div>
                    <div style="text-align:center;padding:10px;margin-bottom:10px;background:#0166CC;color:#FFFFFF;">
                        <div style="font-size:36px;">6段</div>
                    </div>
                    <div style="text-align:center;padding:10px;margin-bottom:10px;background:#0166CC;color:#FFFFFF;">
                        <div style="font-size:14px;">等级分</div>
                        <div style="font-size:36px;">2037.70</div>
                    </div>
                    <table class="table table-bordered">
                        <tr>
                            <td class="left_cell"><span>总排名</span></td>
                            <td class="right_cell">777</td>
                        </tr>
                        <tr>
                            <td class="left_cell"><span>省区排名</span></td>
                            <td class="right_cell">56</td>
                        </tr>
                        <tr>
                            <td class="left_cell"><span>本市排名</span></td>
                            <td class="right_cell">14</td>
                        </tr>
                        <tr>
                            <td class="left_cell"><span>性别</span></td>
                            <td class="right_cell">男</td>
                        </tr>
                        <tr>
                            <td class="left_cell"><span>出生</span></td>
                            <td class="right_cell">2012</td>
                        </tr>
                        <tr>
                            <td class="left_cell"><span>省区</span></td>
                            <td class="right_cell">广东</td>
                        </tr>
                        <tr>
                            <td class="left_cell"><span>城市</span></td>
                            <td class="right_cell">深圳</td>
                        </tr>
                        <tr>
                            <td class="left_cell"><span>备注</span></td>
                            <td class="right_cell">2025第三届"深圳杯"业余围棋公开赛青少年甲组第一名晋升6段</td>
                        </tr>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_yichafen_no_result():
    """无查询结果的 HTML"""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="system-message">
            <h1>:(</h1>
            <p class="error">未找到相关信息</p>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_verify_success():
    """查询成功的响应"""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="system-message">
            <h1>:)</h1>
            <p class="success">查询成功</p>
            <p class="jump">
                页面自动 <a id="href" href="/public/queryresult/from_device/mobile.html">跳转</a>
            </p>
        </div>
    </body>
    </html>
    """


# ===== Import Tests =====

class TestImports:
    """导入测试"""

    def test_import_query_yichafen(self):
        """测试导入 query_yichafen 模块"""
        from query_yichafen import query_player, parse_player_info, create_session
        assert callable(query_player)
        assert callable(parse_player_info)
        assert callable(create_session)

    def test_module_constants(self):
        """测试模块常量"""
        from query_yichafen import BASE_URL, VERIFY_URL, RESULT_URL
        assert BASE_URL.startswith("https://")
        assert "yichafen.com" in BASE_URL


# ===== Session Tests =====

class TestCreateSession:
    """会话创建测试"""

    @patch('query_yichafen.requests.Session')
    def test_create_session_returns_session(self, mock_session_class):
        """测试创建会话返回 Session 对象"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value.status_code = 200
        
        from query_yichafen import create_session
        session, headers = create_session()
        
        assert session is mock_session
        assert 'User-Agent' in headers
        mock_session.get.assert_called_once()

    @patch('query_yichafen.requests.Session')
    def test_session_visits_base_url(self, mock_session_class):
        """测试会话访问主页"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.return_value.status_code = 200
        
        from query_yichafen import create_session, BASE_URL
        session, headers = create_session()
        
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert BASE_URL in str(call_args)


# ===== Data Parsing Tests =====

class TestParsePlayerInfo:
    """数据解析测试"""

    def test_parse_player_info(self, sample_yichafen_html):
        """测试解析选手信息"""
        from query_yichafen import parse_player_info
        
        info = parse_player_info(sample_yichafen_html)
        
        assert info is not None
        assert info['name'] == '田翔宇'
        assert info['level'] == '6段'
        assert info['rating'] == '2037.70'
        assert info['rank_total'] == '777'
        assert info['rank_province'] == '56'
        assert info['rank_city'] == '14'
        assert info['gender'] == '男'
        assert info['birth_year'] == '2012'
        assert info['province'] == '广东'
        assert info['city'] == '深圳'

    def test_parse_player_info_no_result(self, sample_yichafen_no_result):
        """测试解析无结果页面"""
        from query_yichafen import parse_player_info
        
        info = parse_player_info(sample_yichafen_no_result)
        
        assert info is None

    def test_parse_player_info_missing_fields(self):
        """测试解析缺少字段的页面"""
        html = """
        <html>
        <body>
            <div style="font-size:36px;">测试选手</div>
        </body>
        </html>
        """
        
        from query_yichafen import parse_player_info
        info = parse_player_info(html)
        
        # 只有姓名，没有其他信息
        assert info is not None
        assert info['name'] == '测试选手'


# ===== Query Player Tests =====



# ===== Output Format Tests =====

class TestOutputFormat:
    """输出格式测试"""

    def test_json_output_format(self, sample_yichafen_result):
        """测试 JSON 输出格式"""
        from query_yichafen import format_output
        
        output = format_output(sample_yichafen_result, json_output=True)
        data = json.loads(output)
        
        # 验证字段存在
        assert 'found' in data
        assert 'name' in data
        assert 'level' in data
        assert 'rating' in data
        assert 'total_rank' in data
        assert 'province_rank' in data
        assert 'city_rank' in data
        
        # 验证数据类型
        assert isinstance(data['found'], bool)
        assert isinstance(data['rating'], float)
        assert isinstance(data['total_rank'], int)

    def test_text_output_format(self, sample_yichafen_result):
        """测试文本输出格式"""
        from query_yichafen import format_output
        
        output = format_output(sample_yichafen_result, json_output=False)
        
        assert '田翔宇' in output
        assert '6段' in output
        assert '777' in output

    def test_error_output_format(self):
        """测试错误输出格式"""
        from query_yichafen import format_output
        
        result = {
            'found': False,
            'name': '测试',
            'error': '未找到'
        }
        
        output = format_output(result, json_output=False)
        assert '❌' in output
        assert '未找到' in output


# ===== Field Name Compatibility Tests =====

class TestFieldNameCompatibility:
    """字段名兼容性测试"""

    def test_json_field_names(self, sample_yichafen_result):
        """测试 JSON 字段名（确保与后端 API 兼容）"""
        # 后端 API 期望的字段名
        expected_fields = [
            'found', 'name', 'level', 'rating',
            'total_rank', 'province_rank', 'city_rank',
            'gender', 'birth_year', 'province', 'city',
            'notes', 'query_time'
        ]
        
        from query_yichafen import format_output
        output = format_output(sample_yichafen_result, json_output=True)
        data = json.loads(output)
        
        for field in expected_fields:
            assert field in data, f"缺少字段: {field}"

    def test_field_types(self, sample_yichafen_result):
        """测试字段类型"""
        from query_yichafen import format_output
        output = format_output(sample_yichafen_result, json_output=True)
        data = json.loads(output)
        
        assert isinstance(data['found'], bool)
        assert isinstance(data['name'], str)
        assert isinstance(data['level'], str)
        assert isinstance(data['rating'], (int, float))
        assert isinstance(data['total_rank'], int)
        assert isinstance(data['province_rank'], int)
        assert isinstance(data['city_rank'], int)
        assert isinstance(data['query_time'], (int, float))


# ===== Error Handling Tests =====

class TestErrorHandling:
    """错误处理测试"""

    def test_missing_optional_fields(self):
        """测试缺少可选字段"""
        info = {
            'name': '测试',
            'level': '5段',
            # 缺少其他字段
        }
        
        assert info.get('name') == '测试'
        assert info.get('rating') is None

    def test_empty_result(self):
        """测试空结果"""
        from query_yichafen import parse_player_info
        
        html = "<html><body></body></html>"
        info = parse_player_info(html)
        
        assert info is None

    def test_malformed_html(self):
        """测试格式错误的 HTML"""
        from query_yichafen import parse_player_info
        
        html = "这不是有效的HTML"
        info = parse_player_info(html)
        
        # 应该返回 None 或空信息，不应该抛出异常
        assert info is None or isinstance(info, dict)


# ===== Configuration Tests =====

class TestConfiguration:
    """配置测试"""

    def test_base_url_constant(self):
        """测试基础 URL 常量"""
        from query_yichafen import BASE_URL
        assert BASE_URL.startswith("https://")
        assert "yichafen.com" in BASE_URL

    def test_verify_url_constant(self):
        """测试验证 URL 常量"""
        from query_yichafen import VERIFY_URL
        assert VERIFY_URL.startswith("https://")
        assert "verifycondition" in VERIFY_URL

    def test_result_url_constant(self):
        """测试结果 URL 常量"""
        from query_yichafen import RESULT_URL
        assert RESULT_URL.startswith("https://")
        assert "queryresult" in RESULT_URL


# ===== Integration Tests =====

class TestIntegration:
    """集成测试（需要网络）"""

    @pytest.mark.integration
    def test_real_query(self):
        """测试真实查询（需要网络连接）"""
        from query_yichafen import query_player
        
        # 使用真实存在的选手
        result = query_player('田翔宇')
        
        assert result['found'] is True
        assert result['name'] == '田翔宇'
        assert 'level' in result.get('info', {})
        assert 'rating' in result.get('info', {})

    @pytest.mark.integration
    def test_real_query_not_found(self):
        """测试查询不存在的选手（需要网络连接）"""
        from query_yichafen import query_player
        
        result = query_player('这是一个不存在的名字xyz123')
        
        # 可能找到同名，也可能没找到
        assert 'found' in result
        assert 'name' in result

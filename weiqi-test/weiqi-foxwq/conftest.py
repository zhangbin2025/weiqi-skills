"""
weiqi-foxwq 测试套件配置和通用 Fixtures

提供测试数据、Mock fixtures 和辅助函数
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import tempfile

# 添加脚本路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-foxwq/scripts')

# 测试数据目录
FIXTURES_DIR = Path(__file__).parent / 'fixtures'


# ===== 基础 Fixtures =====

@pytest.fixture
def sample_share_url():
    """有效的分享链接示例"""
    return "https://h5.foxwq.com/yehunewshare/?chessid=12345678&uid=12345&createtime=20240101120000"


@pytest.fixture
def sample_share_url_with_roomid():
    """带 roomid 的分享链接"""
    return "https://h5.foxwq.com/yehunewshare/?roomid=87654321&chessid=12345678&uid=12345"


@pytest.fixture
def invalid_share_url():
    """无效的分享链接"""
    return "https://h5.foxwq.com/invalid/url"


@pytest.fixture
def sample_chessid():
    """测试用 Chess ID"""
    return "12345678"


@pytest.fixture
def sample_uid():
    """测试用 UID"""
    return "12345"


@pytest.fixture
def sample_nickname():
    """测试用昵称"""
    return "星阵谈兵"


# ===== API Mock Fixtures =====

@pytest.fixture
def mock_api_response():
    """模拟 API 成功响应"""
    return {
        "result": 0,
        "chess": "(;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞]BR[9段]WR[9段]RE[B+R];B[pd];W[dp];B[pp];W[dd];B[pj])",
        "resultstr": "success"
    }


@pytest.fixture
def mock_api_error_response():
    """模拟 API 错误响应"""
    return {
        "result": -1,
        "resultstr": "Chess not found"
    }


@pytest.fixture
def mock_game_info_response():
    """模拟对局信息响应"""
    return {
        "result": 0,
        "chesslist": {
            "blacknick": "柯洁",
            "whitenick": "申真谞",
            "blackdan": 109,
            "whitedan": 109,
            "result": "B+R",
            "gamestarttime": "2024-01-01 12:00:00",
            "movenum": 250
        }
    }


@pytest.fixture
def mock_user_info_response():
    """模拟用户信息查询响应"""
    return {
        "result": 0,
        "uid": 12345678,
        "username": "星阵谈兵",
        "englishname": "Xingzhen",
        "dan": 109,
        "totalwin": 1000,
        "totallost": 500,
        "totalequal": 10
    }


@pytest.fixture
def mock_user_not_found_response():
    """模拟用户不存在响应"""
    return {
        "result": -1,
        "resultstr": "User not found"
    }


@pytest.fixture
def mock_chess_list_response():
    """模拟棋谱列表响应"""
    return {
        "result": 0,
        "chesslist": [
            {
                "chessid": "100001",
                "blacknick": "柯洁",
                "whitenick": "申真谞",
                "blackdan": 109,
                "whitedan": 109,
                "starttime": "2024-01-15 14:30:00",
                "movenum": 250,
                "winner": 1,
                "point": 3,
                "reason": 1
            },
            {
                "chessid": "100002",
                "blacknick": "李轩豪",
                "whitenick": "辜梓豪",
                "blackdan": 109,
                "whitedan": 109,
                "starttime": "2024-01-14 16:00:00",
                "movenum": 180,
                "winner": 2,
                "point": 0,
                "reason": 4
            }
        ]
    }


@pytest.fixture
def mock_empty_chess_list_response():
    """模拟空棋谱列表响应"""
    return {
        "result": 0,
        "chesslist": []
    }


@pytest.fixture
def mock_chess_list_pagination_response():
    """模拟分页棋谱列表响应"""
    return {
        "result": 0,
        "chesslist": [
            {
                "chessid": f"100{i:03d}",
                "blacknick": f"黑棋{i}",
                "whitenick": f"白棋{i}",
                "blackdan": 20 + i,
                "whitedan": 20 + i,
                "starttime": f"2024-01-{i:02d} 12:00:00",
                "movenum": 200,
                "winner": 1,
                "point": 0,
                "reason": 1
            }
            for i in range(1, 21)
        ]
    }


# ===== WebSocket Mock Fixtures =====

@pytest.fixture
def mock_websocket_binary_data():
    """模拟 WebSocket 二进制数据（包含着法信息）"""
    # 模拟包含 08 xx 10 yy 模式的二进制数据
    data = bytearray()
    # 添加一些随机头部数据
    data.extend(b'\x00\x01\x02\x03\x04\x05')
    # 添加着法 (08 03 10 03 = D3, 08 10 10 04 = K4)
    data.extend([0x08, 0x03, 0x10, 0x03])  # D3
    data.extend([0x08, 0x10, 0x10, 0x04])  # K4
    data.extend([0x08, 0x0f, 0x10, 0x0f])  # O15
    return bytes(data)


@pytest.fixture
def mock_jueyi_live_binary_data():
    """模拟绝艺解说直播二进制数据"""
    # 绝艺直播数据特征：
    # 1. 包含 "jueyi" 字符串
    # 2. 包含主分支标记 10 cb 01
    # 3. 着法格式：08 xx 10 yy 18 color
    data = bytearray()
    # 添加一些随机头部数据
    data.extend(b'\x00\x01\x02\x03')
    # 添加 jueyi 标识
    data.extend(b'jueyi')
    # 添加主分支标记和第一手 (B[pd] = 08 0f 10 03 18 01)
    data.extend([0x10, 0xcb, 0x01])  # 主分支标记
    data.extend([0x1a, 0x12])  # 头部
    data.extend([0x08, 0x0f, 0x10, 0x03, 0x18, 0x01])  # B[pd]
    data.extend('jueyi[62.0%]'.encode('utf-8'))  # 绝艺评论
    # 第二手 (W[dc] = 08 03 10 02 18 02)
    data.extend([0x10, 0xcb, 0x01])
    data.extend([0x1a, 0x12])
    data.extend([0x08, 0x03, 0x10, 0x02, 0x18, 0x02])  # W[dc]
    data.extend('jueyi[61.0%]'.encode('utf-8'))
    # 第三手 (B[dp] = 08 03 10 0f 18 01)
    data.extend([0x10, 0xcb, 0x01])
    data.extend([0x1a, 0x12])
    data.extend([0x08, 0x03, 0x10, 0x0f, 0x18, 0x01])  # B[dp]
    return bytes(data)


@pytest.fixture
def mock_jueyi_live_with_comments():
    """模拟包含完整绝艺评论的直播数据"""
    data = bytearray()
    data.extend(b'jueyi')
    # 多手棋谱数据
    moves = [
        (0x0f, 0x03, 0x01, 'jueyi[62.0% - 3.75]'),  # B[pd]
        (0x03, 0x02, 0x02, 'jueyi[61.0% - 3.75]'),  # W[dc]
        (0x03, 0x0f, 0x01, 'jueyi[39.5% - 3.75]'),  # B[dp]
        (0x0f, 0x10, 0x02, 'jueyi[61.0% | +1.5]'),  # W[pq]
        (0x02, 0x04, 0x01, 'jueyi[39.0% | -1.5]'),  # B[ce]
    ]
    for x, y, color, comment in moves:
        data.extend([0x10, 0xcb, 0x01])
        data.extend([0x1a, 0x12])
        data.extend([0x08, x, 0x10, y, 0x18, color])
        data.extend(comment.encode('utf-8'))
    return bytes(data)


@pytest.fixture
def mock_websocket_handicap_data():
    """模拟包含让子信息的 WebSocket 二进制数据"""
    # GameRule 模式: 08 13 10 01 18 xx
    # boardsize=19(0x13), playingType=1, handicap=4
    data = bytearray()
    data.extend(b'\x00\x01\x02')
    data.extend([0x08, 0x13, 0x10, 0x01, 0x18, 0x04])  # handicap = 4
    data.extend(b'\x08\x03\x10\x03')  # D3
    data.extend(b'\x08\x10\x10\x04')  # K4
    return bytes(data)


@pytest.fixture
def mock_websocket_with_names():
    """模拟包含玩家名字的 WebSocket 二进制数据"""
    data = bytearray()
    data.extend(b'\x9a\x01')  # 名字前缀
    data.append(len("柯洁"))
    data.extend("柯洁".encode('utf-8'))
    data.extend(b'\x9a\x01')
    data.append(len("申真谞"))
    data.extend("申真谞".encode('utf-8'))
    data.extend([0x08, 0x03, 0x10, 0x03])
    return bytes(data)


# ===== HTML Mock Fixtures =====

@pytest.fixture
def sample_html_page():
    """模拟野狐列表页 HTML"""
    return """
    <html>
    <body>
    <table>
        <tr>
            <td><a href="/qipu/newlist/id/12345.html"><h4>柯洁 vs 申真谞</h4></a></td>
            <td>2024-01-15</td>
        </tr>
        <tr>
            <td><a href="/qipu/newlist/id/12346.html"><h4>李轩豪 vs 辜梓豪</h4></a></td>
            <td>2024-01-15</td>
        </tr>
        <tr>
            <td><a href="/qipu/newlist/id/12347.html"><h4>朴廷桓 vs 卞相壹</h4></a></td>
            <td>2024-01-14</td>
        </tr>
    </table>
    </body>
    </html>
    """


@pytest.fixture
def sample_qipu_detail_html():
    """模拟棋谱详情页 HTML（包含 SGF）"""
    return """
    <html>
    <body>
    <div class="qipu-content">
    (;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞]RE[B+R]
    ;B[pd];W[dp];B[pp];W[dd];B[pj])
    </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_sgf_content():
    """示例 SGF 内容"""
    return "(;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞]BR[9段]WR[9段]RE[B+R];B[pd];W[dp];B[pp];W[dd])"


@pytest.fixture
def sample_handicap_sgf():
    """让子棋 SGF 内容"""
    return "(;GM[1]FF[4]SZ[19]PB[黑棋]PW[白棋]HA[4]AB[dd][pd][dp][pp];W[qf])"


# ===== Mock 辅助函数 =====

@pytest.fixture
def mock_requests_get():
    """模拟 requests.get 的 fixture"""
    with patch('requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def mock_urllib_request():
    """模拟 urllib.request 的 fixture"""
    with patch('urllib.request.urlopen') as mock_urlopen:
        yield mock_urlopen


@pytest.fixture
def mock_playwright():
    """模拟 Playwright 的 fixture"""
    mock_page = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_playwright_instance = MagicMock()
    
    mock_playwright_instance.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    
    with patch('download_share.async_playwright') as mock_async_playwright:
        mock_async_playwright.return_value.__aenter__ = Mock(return_value=mock_playwright_instance)
        mock_async_playwright.return_value.__aexit__ = Mock(return_value=None)
        yield {
            'page': mock_page,
            'browser': mock_browser,
            'context': mock_context,
            'playwright': mock_playwright_instance
        }


# ===== 性能测试 Fixtures =====

@pytest.fixture
def temp_output_dir():
    """临时输出目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_timer():
    """模拟性能计时器"""
    from download_share import PerformanceTimer
    timer = PerformanceTimer()
    timer.start()
    return timer


# ===== 数据加载辅助函数 =====

def load_fixture(filename: str) -> dict:
    """从 fixtures 目录加载 JSON 文件"""
    filepath = FIXTURES_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def load_fixture_text(filename: str) -> str:
    """从 fixtures 目录加载文本文件"""
    filepath = FIXTURES_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

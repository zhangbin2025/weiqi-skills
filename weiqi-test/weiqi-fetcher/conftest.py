"""
weiqi-fetcher 测试配置
"""

import pytest
import sys
import os

# 添加 fetcher 脚本路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-fetcher/scripts')

# 导入测试对象
from sources import (
    BaseSourceFetcher,
    FetchResult,
    get_fetcher_for_url,
    get_fetcher_by_name,
    list_fetchers,
)

# 获取所有 fetcher 类的辅助函数
def get_all_fetcher_classes():
    """获取所有已注册的 fetcher 类"""
    from sources.base import _fetchers
    return list(_fetchers.values())


# ========== 测试用的模拟数据 ==========

# 有效的URL示例（用于测试URL识别）
VALID_URLS = {
    'ogs': [
        'https://online-go.com/game/12345',
        'https://online-go.com/game/view/67890',
    ],
    'foxwq': [
        'https://h5.foxwq.com/yehunewshare/?chessid=1234567890',
        'https://www.foxwq.com/share?chessid=9876543210',
    ],
    '101weiqi': [
        'https://www.101weiqi.com/play/p/abc123/',
    ],
    'yike': [
        'https://home.yikeweiqi.com/mobile.html#/golive/room/12345/abc',
    ],
    'yuanluobo': [
        'https://jupiter.yuanluobo.com/robot-public/all-in-app/go/review?session_id=test123',
    ],
    '1919': [
        'https://m.19x19.com/app/dark/zh/sgf/sgf123',
    ],
    'izis': [
        'http://app.izis.cn/web/#/live_detail?gameId=12345&type=2',
    ],
    'yike_shaoer': [
        'https://shaoer.yikeweiqi.com/statichtml/game_analysis_mobile.html?p=test123',
    ],
    'eweiqi': [
        'http://mobile.eweiqi.com/index_ZHCN.html?LNK=1&GNO=12345',
    ],
    'txwq': [
        'https://h5.txwq.qq.com/txwqshare/index.html?chessid=12345',
    ],
    'xinboduiyi': [
        'https://weiqi.xinboduiyi.com/golive/index.html#/?gamekey=test123',
    ],
    'dzqzd': [
        'https://v.dzqzd.com/Kifu/chessmanualdetail?kifuId=12345',
    ],
}

# 无效的URL
INVALID_URLS = [
    'https://example.com/game/123',
    'https://google.com',
    'not_a_url',
    '',
]


# ========== Fixtures ==========

@pytest.fixture
def fetcher_registry():
    """获取所有已注册的 fetcher"""
    return list_fetchers()


@pytest.fixture
def all_fetcher_classes():
    """获取所有 fetcher 类（用于测试URL识别）"""
    return get_all_fetcher_classes()


@pytest.fixture
def sample_sgf():
    """示例SGF棋谱内容"""
    return """(;GM[1]FF[4]CA[UTF-8]SZ[19]
PB[黑棋]PW[白棋]BR[3d]WR[3d]
KM[6.5]RE[B+R]
;B[pd];W[dp];B[pp];W[dd];B[pj])"""


@pytest.fixture
def sample_fetch_result_success():
    """成功的 FetchResult 示例"""
    return FetchResult(
        success=True,
        source='test',
        url='https://test.com/game/123',
        sgf_content='(;GM[1]FF[4]SZ[19])',
        output_path='/tmp/test.sgf',
        metadata={
            'game_id': '123',
            'black_name': 'Black',
            'white_name': 'White',
        },
        timing={'extract_id': 0.001, 'api_request': 0.5}
    )


@pytest.fixture
def sample_fetch_result_failure():
    """失败的 FetchResult 示例"""
    return FetchResult(
        success=False,
        source='test',
        url='https://test.com/game/123',
        sgf_content=None,
        output_path=None,
        error='测试错误信息',
        timing={'extract_id': 0.001}
    )


# ========== 自定义 Marks ==========

# 标记需要网络访问的测试
requires_network = pytest.mark.skipif(
    os.environ.get('SKIP_NETWORK_TESTS', 'false').lower() == 'true',
    reason='SKIP_NETWORK_TESTS 设置为 true，跳过网络测试'
)

# 标记需要 Playwright 的测试
try:
    import playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

requires_playwright = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason='Playwright 未安装，跳过浏览器自动化测试'
)

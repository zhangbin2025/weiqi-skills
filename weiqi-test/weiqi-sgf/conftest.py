"""
weiqi-sgf 前端自动化测试配置

使用 Playwright 进行浏览器自动化测试
兼容模式：无 Playwright 时跳过前端测试
"""

import pytest
import tempfile
import os
import sys

# 检查 Playwright 是否可用
try:
    import pytest_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# 测试用的 SGF 数据

SIMPLE_SGF = """(;GM[1]FF[4]SZ[19]PB[黑棋]PW[白棋];B[pd];W[dp];B[pp];W[dd];B[pj];W[nc];B[pf];W[kc])"""

VARIATIONS_SGF = """(;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞]EV[第28届LG杯决赛];B[pd]C[jueyi黑62%]
  (;W[dp]C[jueyi黑58%];B[pp];W[dd])
  (;W[dd]C[jueyi黑65%]N[小雪崩];B[dp];W[cc])
  (;W[pp]C[jueyi黑38%]N[超高目];B[dp]))"""

HANDICAP_SGF = """(;GM[1]FF[4]SZ[19]PB[黑棋]PW[白棋]HA[4]AB[dd][pd][dp][pp];W[qf])"""

EMPTY_SGF = """(;GM[1]FF[4]SZ[19]PB[黑棋]PW[白棋])"""


def generate_replay_html(sgf_content, game_name="测试对局"):
    """
    生成用于测试的 replay.html 内容
    模拟 weiqi-sgf/scripts/replay.py 的输出
    """
    sys.path.insert(0, '/root/.openclaw/workspace/weiqi-sgf/scripts')
    from sgf_parser import parse_sgf
    import json
    import html as html_module
    
    result = parse_sgf(sgf_content)
    tree = result["tree"]
    game_info = result["game_info"]
    board_size = game_info.get("SZ", 19)
    
    # 处理让子
    handicap_stones = []
    handicap = game_info.get("HA", 0)
    if handicap and "AB" in game_info:
        for coord in game_info["AB"]:
            if len(coord) >= 2:
                x = ord(coord[0]) - 97
                y = ord(coord[1]) - 97
                handicap_stones.append({"x": x, "y": y})
    
    # 读取模板
    template_path = '/root/.openclaw/workspace/weiqi-sgf/scripts/templates/replay.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 替换变量
    pb = game_info.get("PB", "黑棋")
    pw = game_info.get("PW", "白棋")
    ev = game_info.get("EV", "")
    
    tree_json = json.dumps(tree, ensure_ascii=False)
    tree_json_escaped = html_module.escape(tree_json)
    
    output = template
    output = output.replace('{{GAME_NAME}}', html_module.escape(game_name))
    output = output.replace('{{GAME_TITLE}}', html_module.escape(game_name))
    output = output.replace('{{GAME_INFO}}', html_module.escape(f"{pb} vs {pw}" + (f" | {ev}" if ev else "")))
    output = output.replace('{{BLACK_NAME}}', html_module.escape(pb))
    output = output.replace('{{WHITE_NAME}}', html_module.escape(pw))
    output = output.replace('{{TREE_JSON}}', tree_json_escaped)
    output = output.replace('{{BOARD_SIZE}}', str(board_size))
    output = output.replace('{{HANDICAP_STONES}}', json.dumps(handicap_stones))
    output = output.replace('{{DOWNLOAD_FILENAME}}', 'test.sgf')
    
    return output


@pytest.fixture
def simple_sgf():
    """简单棋谱（无变化图）"""
    return SIMPLE_SGF


@pytest.fixture
def variations_sgf():
    """带变化图的棋谱"""
    return VARIATIONS_SGF


@pytest.fixture
def handicap_sgf():
    """让子棋谱"""
    return HANDICAP_SGF


@pytest.fixture
def empty_sgf():
    """空棋谱"""
    return EMPTY_SGF


@pytest.fixture
def page_factory():
    """
    创建一个工厂函数，用于生成带有指定 SGF 内容的测试页面
    
    使用方式：
        page = page_factory(sgf_content, "对局名称")
    """
    def _create_page(sgf_content, game_name="测试对局"):
        html_content = generate_replay_html(sgf_content, game_name)
        
        # 创建临时 HTML 文件
        fd, path = tempfile.mkstemp(suffix='.html', prefix='weiqi_test_')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return path
        except:
            os.unlink(path)
            raise
    
    return _create_page


# 全局配置 - 只在 Playwright 可用时加载
if PLAYWRIGHT_AVAILABLE:
    pytest_plugins = ['pytest_playwright']
    
    def pytest_configure(config):
        """配置 pytest-playwright"""
        config.option.browser = ["chromium"]
        config.option.headless = True
        
    @pytest.fixture(scope="session")
    def browser_context_args(browser_context_args):
        """配置浏览器上下文"""
        return {
            **browser_context_args,
            "viewport": {"width": 1280, "height": 720},
        }
else:
    # 无 Playwright 时的配置
    def pytest_configure(config):
        """配置 pytest"""
        pass
    
    def pytest_collection_modifyitems(config, items):
        """修改测试项：跳过所有前端测试"""
        skip_mark = pytest.mark.skip(reason="Playwright 未安装，跳过前端测试")
        for item in items:
            # 如果测试函数使用 page fixture，标记为跳过
            if "page" in item.fixturenames:
                item.add_marker(skip_mark)

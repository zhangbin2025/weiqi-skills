"""
weiqi-test 顶层 pytest 配置

注意：pytest_plugins 必须定义在顶层 conftest.py 中
"""

import pytest

# 注册自定义标记
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires network)"
    )

# 检查 Playwright 是否可用
try:
    import pytest_playwright
    PLAYWRIGHT_AVAILABLE = True
    pytest_plugins = ['pytest_playwright']
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

"""
weiqi-player 测试配置
"""

import pytest

# 注册自定义标记
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires network)"
    )

#!/usr/bin/env python3
"""
CLI命令测试 - 验证--mode auto参数
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki')

# 先测试参数解析
from src.cli.commands import main


def test_cli_parser():
    """测试CLI参数解析"""
    
    # 测试1: 默认模式是custom
    with patch('sys.argv', ['weiqi-joseki', 'katago', '--start-date', '2026-04-01', '--end-date', '2026-04-10']):
        with patch('src.cli.commands._cmd_katago_custom') as mock_custom:
            mock_custom.return_value = 0
            try:
                main()
            except SystemExit:
                pass
            assert mock_custom.called, "默认应该调用custom模式"
    
    print("✓ test_cli_parser: 参数解析正确")


def test_auto_mode():
    """测试auto模式调用"""
    
    with patch('sys.argv', ['weiqi-joseki', 'katago', '--mode', 'auto']):
        with patch('src.cli.commands._cmd_katago_auto') as mock_auto:
            mock_auto.return_value = 0
            try:
                main()
            except SystemExit:
                pass
            assert mock_auto.called, "--mode auto 应该调用auto模式"
    
    print("✓ test_auto_mode: auto模式调用正确")


def test_help_output():
    """测试帮助输出包含新参数"""
    import io
    import argparse
    
    from src.cli.commands import main
    
    # 捕获帮助输出
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    
    try:
        with patch('sys.argv', ['weiqi-joseki', 'katago', '--help']):
            main()
    except SystemExit as e:
        pass
    
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    # 验证新参数存在
    assert '--mode' in output, "帮助中应包含 --mode 参数"
    assert '--force-rebuild' in output, "帮助中应包含 --force-rebuild 参数"
    assert 'custom' in output, "帮助中应提到 custom 模式"
    assert 'auto' in output, "帮助中应提到 auto 模式"
    
    print("✓ test_help_output: 帮助输出正确")


if __name__ == "__main__":
    test_cli_parser()
    test_auto_mode()
    test_help_output()
    print("\n✅ All CLI tests passed!")

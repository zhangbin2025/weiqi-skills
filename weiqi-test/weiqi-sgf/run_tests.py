"""
weiqi-sgf 前端自动化测试

使用 Playwright 进行端到端测试
"""

import subprocess
import sys
import os


def check_playwright():
    """检查 Playwright 是否安装"""
    try:
        import pytest_playwright
        return True
    except ImportError:
        return False


def install_playwright():
    """安装 Playwright 和浏览器"""
    print("正在安装 Playwright...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest-playwright"])
    print("正在安装浏览器...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])


def run_tests():
    """运行测试"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建 pytest 命令
    cmd = [
        sys.executable, "-m", "pytest",
        test_dir,
        "-v",  # 详细输出
        "--headed" if "--headed" in sys.argv else "--headless",
        "--browser=chromium",
        "--slowmo=100" if "--slowmo" in sys.argv else "",
    ]
    
    # 过滤空字符串
    cmd = [c for c in cmd if c]
    
    # 运行测试
    result = subprocess.call(cmd)
    return result


def main():
    """主函数"""
    print("=" * 60)
    print("weiqi-sgf 前端自动化测试")
    print("=" * 60)
    
    # 检查 Playwright
    if not check_playwright():
        print("\nPlaywright 未安装，是否安装? [Y/n]")
        response = input().strip().lower()
        if response in ("", "y", "yes"):
            install_playwright()
        else:
            print("请先安装 Playwright: pip install pytest-playwright")
            sys.exit(1)
    
    # 运行测试
    print("\n开始运行测试...\n")
    result = run_tests()
    
    sys.exit(result)


if __name__ == "__main__":
    main()

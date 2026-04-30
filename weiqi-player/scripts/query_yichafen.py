#!/usr/bin/env python3
"""
易查分平台围棋业余段位查询 - 浏览器会话复用优化版（支持 JSON 输出）
使用 Playwright 持久化上下文实现会话复用

优化效果：
- 单次查询：~8-10秒（启动+关闭浏览器）
- 批量查询：~3-5秒/人（复用会话，一次启动）

依赖安装：
    pip install playwright
    playwright install chromium

【单个查询】
    python3 query_yichafen.py 张三
    python3 query_yichafen.py 李四 --json

【批量查询 - 推荐】
    python3 query_yichafen.py --batch 张三 李四 王五
    python3 query_yichafen.py --batch 赵六 孙七 --json
"""

import sys
import json
import time
import os
import argparse
from pathlib import Path
from contextlib import contextmanager
from collections import OrderedDict

# 尝试导入 playwright
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ 请先安装 Playwright:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)

# 配置
BASE_URL = "https://yeyuweiqi.yichafen.com/qz/s9W2g0zKmt"
USER_DATA_DIR = Path("/tmp/yichafen_browser_data")
SESSION_TIMEOUT = 300  # 会话有效期5分钟
STATE_FILE = Path("/tmp/yichafen_state.json")


# ===== 性能计时工具 =====
class PerformanceTimer:
    """性能计时器 - 追踪每个步骤的执行耗时"""
    def __init__(self):
        self.timings = OrderedDict()
        self.start_time = None
    
    def start(self):
        """开始总计时"""
        self.start_time = time.time()
        return self
    
    @contextmanager
    def step(self, name):
        """上下文管理器 - 计时单个步骤"""
        step_start = time.time()
        try:
            yield self
        finally:
            elapsed = time.time() - step_start
            self.timings[name] = elapsed
    
    def get_total(self):
        """获取总耗时"""
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    def format_report(self):
        """格式化计时报告（Markdown 格式）"""
        lines = []
        lines.append("\n" + "="*50)
        lines.append("⏱️  性能计时报告（易查分查询）")
        lines.append("="*50)
        
        total_step_time = 0
        for name, elapsed in self.timings.items():
            total_step_time += elapsed
            lines.append(f"  {name:20s} : {elapsed:>8.3f}s")
        
        lines.append("-"*50)
        lines.append(f"  {'步骤累计':20s} : {total_step_time:>8.3f}s")
        lines.append(f"  {'总耗时':20s} : {self.get_total():>8.3f}s")
        lines.append("="*50)
        return "\n".join(lines)
    
    def to_dict(self):
        """返回计时数据字典（用于 JSON）"""
        return {
            "steps": dict(self.timings),
            "total": round(self.get_total(), 3)
        }


# 全局计时器实例
timer = PerformanceTimer()


def is_browser_ready():
    """检查浏览器是否已准备好（页面已加载）"""
    if not STATE_FILE.exists():
        return False
    
    # 检查状态文件是否过期
    age = time.time() - STATE_FILE.stat().st_mtime
    if age > SESSION_TIMEOUT:
        return False
    
    return True


def query_player(name, headless=True):
    """
    查询单个选手的业余段位信息
    
    Args:
        name: 选手姓名
        headless: 是否无头模式
    
    Returns:
        str: 页面文本内容，失败返回 None
    """
    global timer
    timer.start()
    
    with sync_playwright() as p:
        # 启动浏览器
        with timer.step("启动浏览器"):
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(USER_DATA_DIR),
                headless=headless,
                args=['--no-sandbox'] if headless else []
            )
        
        try:
            # 获取页面
            with timer.step("加载并查询"):
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto(BASE_URL, wait_until='domcontentloaded')
                
                # 等待输入框
                page.wait_for_selector('input[placeholder*="姓名"], input[type="text"]', timeout=10000)
                
                # 填写姓名
                input_selector = 'input[placeholder*="姓名"], input[type="text"]'
                input_box = page.locator(input_selector).first
                input_box.fill(name)
                time.sleep(0.3)
                
                # 点击查询按钮
                button_selector = 'button:has-text("查询"), .query-btn, [class*="query"]'
                button = page.locator(button_selector).first
                if button.count() > 0:
                    button.click()
                else:
                    input_box.press('Enter')
                
                # 等待结果
                time.sleep(1.2)
                try:
                    page.wait_for_selector('.result-container, .info-item, table', timeout=5000)
                except:
                    pass
                
                # 获取页面文本
                text_content = page.locator('body').inner_text()
            
            # 提取数据
            with timer.step("提取数据"):
                info = parse_player_info(text_content)
            
            return text_content
            
        except Exception as e:
            print(f"❌ 查询出错: {e}")
            return None
        finally:
            # 关闭浏览器
            with timer.step("关闭浏览器"):
                browser.close()


def parse_player_info(text):
    """
    解析选手信息
    
    Args:
        text: 页面文本内容
    
    Returns:
        dict: 选手信息字典
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    info = {
        '段位': None,
        '等级分': None,
        '总排名': None,
        '省区排名': None,
        '本市排名': None,
        '省区': None,
        '城市': None,
        '性别': None,
        '出生': None,
        '备注': None,
    }
    
    # 简单解析逻辑
    for i, line in enumerate(lines):
        # 段位（简单格式如 "6段"，不含其他文字）
        if line.endswith('段') and len(line) <= 3 and '晋升' not in line and '备注' not in line:
            info['段位'] = line
        
        # 等级分（通常是一个四位数左右的数字）
        if line.replace('.', '').isdigit():
            val = float(line)
            if 1000 < val < 3000:
                info['等级分'] = line
        
        # 总排名（格式: "总排名\t2559" 或两行格式）
        if line.startswith('总排名'):
            parts = line.split('\t')
            if len(parts) > 1:
                info['总排名'] = parts[1].strip()
            elif i + 1 < len(lines):
                next_line = lines[i + 1].replace('\t', '').strip()
                if next_line.isdigit():
                    info['总排名'] = next_line
        
        # 省区排名
        if line.startswith('省区排名'):
            parts = line.split('\t')
            if len(parts) > 1:
                info['省区排名'] = parts[1].strip()
            elif i + 1 < len(lines):
                info['省区排名'] = lines[i + 1].replace('\t', '').strip()
        
        # 本市排名
        if line.startswith('本市排名'):
            parts = line.split('\t')
            if len(parts) > 1:
                info['本市排名'] = parts[1].strip()
            elif i + 1 < len(lines):
                info['本市排名'] = lines[i + 1].replace('\t', '').strip()
        
        # 省区
        if line.startswith('省区') and not line.startswith('省区排名'):
            parts = line.split('\t')
            if len(parts) > 1:
                info['省区'] = parts[1].strip()
            elif i + 1 < len(lines):
                info['省区'] = lines[i + 1]
        
        # 城市
        if line.startswith('城市'):
            parts = line.split('\t')
            if len(parts) > 1:
                info['城市'] = parts[1].strip()
            elif i + 1 < len(lines):
                info['城市'] = lines[i + 1]
        
        # 性别
        if line.startswith('性别'):
            parts = line.split('\t')
            if len(parts) > 1:
                info['性别'] = parts[1].strip()
            elif i + 1 < len(lines):
                info['性别'] = lines[i + 1]
        
        # 出生
        if line.startswith('出生'):
            parts = line.split('\t')
            if len(parts) > 1:
                info['出生'] = parts[1].strip()
            elif i + 1 < len(lines):
                info['出生'] = lines[i + 1]
        
        # 备注（以"备注"开头或包含晋升信息）
        if line.startswith('备注\t') or (len(line) > 10 and '晋升' in line and '杯' in line):
            info['备注'] = line.replace('备注\t', '')
    
    return info


def format_output(name, info, elapsed):
    """格式化输出结果 - Markdown 格式"""
    output = []
    output.append(f"\n📋 **{name}** - 易查分业余段位查询\n")
    
    parts = []
    if info.get('段位'):
        parts.append(f"段位: {info['段位']}")
    if info.get('等级分'):
        parts.append(f"等级分: {info['等级分']}")
    if info.get('总排名'):
        parts.append(f"总排名: {info['总排名']}")
    if info.get('省区'):
        parts.append(f"地区: {info['省区']} {info.get('城市', '')}".strip())
    if info.get('性别'):
        parts.append(f"性别: {info['性别']}")
    if info.get('出生'):
        parts.append(f"出生: {info['出生']}")
    
    if parts:
        output.append(" | ".join(parts))
    else:
        output.append("⚠️ 未查询到业余段位信息")
    
    if info.get('备注'):
        output.append(f"\n备注: {info['备注']}")
    
    output.append(f"\n⏱️ 查询耗时: {elapsed:.1f}秒\n")
    output.append(timer.format_report())
    return "\n".join(output)


def format_json_output(name, info, elapsed):
    """格式化输出结果 - JSON 格式"""
    result = {
        "found": bool(info.get('段位') or info.get('等级分')),
        "name": name,
        "level": info.get('段位', ''),
        "rating": float(info.get('等级分', 0)) if info.get('等级分') else 0,
        "total_rank": int(info.get('总排名', 0)) if info.get('总排名') else 0,
        "province_rank": int(info.get('省区排名', 0)) if info.get('省区排名') else 0,
        "city_rank": int(info.get('本市排名', 0)) if info.get('本市排名') else 0,
        "gender": info.get('性别', ''),
        "birth_year": info.get('出生', ''),
        "province": info.get('省区', ''),
        "city": info.get('城市', ''),
        "notes": info.get('备注', ''),
        "query_time": round(elapsed, 1),
        "performance": timer.to_dict()
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def query_single_player(page, name, timer):
    """
    在已打开的页面中查询单个选手（用于批量查询）
    
    Args:
        page: Playwright page 对象
        name: 选手姓名
        timer: 性能计时器
    
    Returns:
        dict: 选手信息字典
    """
    try:
        # 重新导航到页面
        with timer.step(f"[{name}] 页面导航"):
            page.goto(BASE_URL, wait_until='domcontentloaded')
            time.sleep(0.8)
        
        # 填写表单
        with timer.step(f"[{name}] 填写表单"):
            input_selector = 'input[placeholder*="姓名"], input[type="text"]'
            input_box = page.locator(input_selector).first
            input_box.fill("")
            input_box.fill(name)
            time.sleep(0.2)
        
        # 点击查询
        with timer.step(f"[{name}] 点击查询"):
            button_selector = 'button:has-text("查询"), .query-btn, [class*="query"]'
            button = page.locator(button_selector).first
            if button.count() > 0:
                button.click()
            else:
                input_box.press('Enter')
        
        # 等待结果
        with timer.step(f"[{name}] 等待结果"):
            time.sleep(1.0)
            try:
                page.wait_for_selector('.result-container, .info-item, table', timeout=4000)
            except:
                pass
        
        # 提取数据
        with timer.step(f"[{name}] 提取数据"):
            text_content = page.locator('body').inner_text()
            info = parse_player_info(text_content)
            info['_name'] = name
            info['_raw'] = text_content
            return info
            
    except Exception as e:
        return {'_name': name, '_error': str(e)}


def query_multiple_players(names, headless=True):
    """
    批量查询多个选手（共享浏览器会话）
    
    Args:
        names: 姓名列表
        headless: 是否无头模式
    
    Returns:
        list: 选手信息列表
    """
    global timer
    timer.start()
    results = []
    
    with sync_playwright() as p:
        # 启动浏览器（只启动一次）
        with timer.step("启动浏览器"):
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(USER_DATA_DIR),
                headless=headless,
                args=['--no-sandbox'] if headless else []
            )
        
        # 获取页面
        with timer.step("初始化页面"):
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto(BASE_URL, wait_until='networkidle')
            page.wait_for_selector('input[placeholder*="姓名"], input[type="text"]', timeout=10000)
        
        # 逐个查询
        for i, name in enumerate(names, 1):
            info = query_single_player(page, name, timer)
            results.append(info)
        
        # 关闭浏览器（只关闭一次）
        with timer.step("关闭浏览器"):
            browser.close()
    
    return results


def format_batch_output(results, total_elapsed, json_mode=False):
    """格式化批量查询输出"""
    if json_mode:
        output = []
        for info in results:
            name = info.get('_name', '未知')
            if info.get('_error'):
                output.append({
                    "found": False,
                    "name": name,
                    "error": info['_error']
                })
            else:
                output.append({
                    "found": bool(info.get('段位') or info.get('等级分')),
                    "name": name,
                    "level": info.get('段位', ''),
                    "rating": float(info.get('等级分', 0)) if info.get('等级分') else 0,
                    "province": info.get('省区', ''),
                    "city": info.get('城市', ''),
                    "notes": info.get('备注', '')
                })
        print(json.dumps({
            "count": len(results),
            "results": output,
            "performance": timer.to_dict()
        }, ensure_ascii=False, indent=2))
    else:
        output = []
        output.append("\n📋 批量查询结果汇总\n")
        
        for info in results:
            name = info.get('_name', '未知')
            
            if info.get('_error'):
                output.append(f"• **{name}**: ❌ 查询失败 - {info['_error']}")
                continue
            
            parts = []
            if info.get('段位'):
                parts.append(f"段位: {info['段位']}")
            if info.get('等级分'):
                parts.append(f"等级分: {info['等级分']}")
            if info.get('总排名'):
                parts.append(f"总排名: {info['总排名']}")
            if info.get('省区'):
                parts.append(f"地区: {info['省区']}")
            
            if parts:
                output.append(f"• **{name}**: {' | '.join(parts)}")
            else:
                output.append(f"• **{name}**: ⚠️ 未找到段位信息")
        
        output.append(f"\n⏱️ 总耗时: {total_elapsed:.1f}秒 | 平均: {total_elapsed/len(results):.1f}秒/人\n")
        output.append(timer.format_report())
        return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description='查询易查分业余段位')
    parser.add_argument('names', nargs='+', help='选手姓名（单个或多个）')
    parser.add_argument('--batch', action='store_true', help='批量查询模式')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    parser.add_argument('--visible', action='store_true', help='显示浏览器窗口（调试用）')
    parser.add_argument('--debug', action='store_true', help='打印调试信息')
    args = parser.parse_args()
    
    headless = not args.visible
    
    # 批量查询模式
    if args.batch:
        start_time = time.time()
        results = query_multiple_players(args.names, headless=headless)
        total_elapsed = time.time() - start_time
        format_batch_output(results, total_elapsed, json_mode=args.json)
        return
    
    # 单个查询模式
    name = args.names[0]
    start_time = time.time()
    
    # 执行查询
    result_text = query_player(name, headless=headless)
    elapsed = time.time() - start_time
    
    if result_text:
        info = parse_player_info(result_text)
        if args.json:
            print(format_json_output(name, info, elapsed))
        else:
            print(format_output(name, info, elapsed))
        
        # 同时打印原始文本（调试用）
        if args.debug:
            print("\n原始文本:")
            print("-" * 50)
            print(result_text[:1500])
    else:
        if args.json:
            print(json.dumps({
                "found": False,
                "name": name,
                "error": "查询失败，请检查网络连接或稍后重试",
                "performance": timer.to_dict()
            }, ensure_ascii=False, indent=2))
        else:
            print("❌ 查询失败，请检查网络连接或稍后重试")


if __name__ == "__main__":
    main()

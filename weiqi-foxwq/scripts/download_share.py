#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
野狐围棋分享链接SGF下载器
支持从野狐H5分享链接提取棋谱SGF
自动检测对局状态：已结束使用API/页面解析，进行中使用WebSocket

用法:
    python3 download_share.py <分享链接> [输出文件]
    
示例:
    python3 download_share.py "https://h5.foxwq.com/yehunewshare/?svrid=1&svrtype=20010&roomid=12345..."
    python3 download_share.py "https://h5.foxwq.com/yehunewshare/?..." /tmp/output.sgf
"""

import os
import re
import sys
import asyncio
import argparse
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from contextlib import contextmanager
from collections import OrderedDict

# 性能计时工具
class PerformanceTimer:
    """性能计时器"""
    def __init__(self):
        self.timings = OrderedDict()
        self.start_time = None
    
    def start(self):
        self.start_time = datetime.now()
        return self
    
    @contextmanager
    def step(self, name):
        step_start = datetime.now()
        try:
            yield self
        finally:
            elapsed = (datetime.now() - step_start).total_seconds()
            self.timings[name] = elapsed
    
    def format_report(self):
        lines = ["\n" + "="*50, "⏱️  性能计时报告", "="*50]
        for name, elapsed in self.timings.items():
            lines.append(f"  {name:25s} : {elapsed:>8.3f}s")
        lines.append("="*50)
        return "\n".join(lines)

# 全局计时器
timer = PerformanceTimer()

def parse_share_url(url):
    """解析分享链接，提取参数"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    return {
        'roomid': params.get('roomid', [None])[0],
        'chessid': params.get('chessid', [None])[0],
        'createtime': params.get('createtime', [None])[0],
        'full_url': url
    }

def extract_moves_from_binary(data):
    """从二进制数据中提取着法 (08 xx 10 yy 模式)"""
    moves = []
    i = 0
    while i < len(data) - 4:
        if data[i] == 0x08 and data[i+2] == 0x10:
            x = data[i+1]
            y = data[i+3]
            if x < 19 and y < 19:
                moves.append((x, y))
                i += 4
                continue
        i += 1
    return moves

def extract_player_names(data):
    """从二进制数据中提取玩家名"""
    names = []
    try:
        # 方法1: 从UTF-8文本中提取
        text = data.decode('utf-8', errors='ignore')
        
        # 查找常见的玩家名模式
        # 野狐格式: 玩家名前面有 \x9a\x01\xXX (长度) 标记
        import re
        
        # 查找类似 \x9a\x01\x09idealmove 的模式
        # \x9a\x01 是 protobuf 字段标记，后面是长度和字符串
        idx = 0
        while idx < len(data) - 3:
            # 查找 \x9a\x01 后跟长度字节的模式
            if data[idx] == 0x9a and data[idx+1] == 0x01:
                str_len = data[idx+2]
                if 3 <= str_len <= 20 and idx + 3 + str_len <= len(data):
                    try:
                        name = data[idx+3:idx+3+str_len].decode('utf-8')
                        # 过滤有效的玩家名
                        if name and not name.startswith('http') and len(name) > 1:
                            # 排除一些常见的非玩家名
                            if name not in ['1.14.205.137', 'avatar']:
                                names.append(name)
                    except:
                        pass
            idx += 1
        
        # 方法2: 尝试从URL参数或页面描述中提取
        if not names:
            # 查找 [段位] 格式
            matches = re.findall(r'([\w\u4e00-\u9fff]+)\[\d+段\]', text)
            names.extend(matches)
        
        # 去重并保持顺序
        seen = set()
        unique_names = []
        for name in names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)
        
        return unique_names[:2]  # 返回前两个不同的名字
    except Exception as e:
        return names

async def extract_via_websocket(url, timeout=15):
    """通过WebSocket提取棋谱"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ 需要安装 playwright: pip3 install playwright")
        print("   然后运行: playwright install chromium")
        return None, None
    
    moves = []
    player_names = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
        )
        page = await context.new_page()
        
        def handle_ws(ws):
            async def on_message(data):
                nonlocal moves, player_names
                if isinstance(data, bytes):
                    # 查找大消息（完整棋谱）
                    if len(data) > 1000 and not moves:
                        moves = extract_moves_from_binary(data)
                        if not player_names:
                            player_names = extract_player_names(data)
            
            ws.on("framereceived", lambda d: asyncio.create_task(on_message(d)))
        
        page.on("websocket", handle_ws)
        
        with timer.step("WebSocket连接与数据获取"):
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(timeout)
        
        await browser.close()
    
    return moves, player_names

def create_sgf(moves, pb="黑棋", pw="白棋"):
    """创建SGF格式棋谱"""
    if not moves:
        return None
    
    coord_map = "abcdefghijklmnopqrs"
    sgf = f"(;GM[1]FF[4]CA[UTF-8]SZ[19]\n"
    sgf += f"PB[{pb}]PW[{pw}]\n"
    
    for i, (x, y) in enumerate(moves):
        color = "B" if i % 2 == 0 else "W"
        if 0 <= x < 19 and 0 <= y < 19:
            sgf += f";{color}[{coord_map[x]}{coord_map[y]}]\n"
    
    sgf += ")"
    return sgf

def extract_from_share_link(url, output_path=None):
    """主函数：从分享链接提取SGF"""
    
    print("="*60)
    print("🎯 野狐围棋分享链接SGF下载器")
    print("="*60)
    
    timer.start()
    
    # 解析URL
    with timer.step("解析分享链接"):
        params = parse_share_url(url)
    
    if not params['chessid']:
        print("❌ 无效的分享链接，无法提取chessid")
        return None
    
    print(f"\n对局信息:")
    print(f"  Room ID: {params['roomid']}")
    print(f"  Chess ID: {params['chessid']}")
    print()
    
    # 使用WebSocket提取
    print("🌐 连接WebSocket获取实时数据...")
    moves, player_names = asyncio.run(extract_via_websocket(url))
    
    if not moves:
        print("❌ 无法提取棋谱数据")
        print(timer.format_report())
        return None
    
    # 确定玩家名
    pb = player_names[0] if len(player_names) > 0 else "黑棋"
    pw = player_names[1] if len(player_names) > 1 else "白棋"
    
    print(f"\n✅ 成功提取棋谱!")
    print(f"  总手数: {len(moves)} 手")
    print(f"  黑棋: {pb}")
    print(f"  白棋: {pw}")
    
    # 生成SGF
    with timer.step("生成SGF"):
        sgf = create_sgf(moves, pb, pw)
    
    if not sgf:
        print("❌ 生成SGF失败")
        return None
    
    # 确定输出路径
    if not output_path:
        output_path = f"/tmp/foxwq_{params['roomid']}_{params['chessid']}.sgf"
    
    # 保存文件
    with timer.step("保存文件"):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sgf)
    
    print(f"\n💾 SGF已保存: {output_path}")
    
    # 显示前10手
    print(f"\n前10手预览:")
    for i, (x, y) in enumerate(moves[:10]):
        color = "黑" if i % 2 == 0 else "白"
        coord = chr(ord('A') + x) + str(19 - y)
        print(f"  {i+1}. {color}: {coord}")
    
    print(timer.format_report())
    
    return output_path

def main():
    parser = argparse.ArgumentParser(
        description='从野狐围棋分享链接下载SGF棋谱',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python3 download_share.py "https://h5.foxwq.com/yehunewshare/?roomid=123..."
  python3 download_share.py "https://h5.foxwq.com/..." /tmp/game.sgf
        '''
    )
    
    parser.add_argument('url', help='野狐H5分享链接')
    parser.add_argument('output', nargs='?', help='输出SGF文件路径（可选）')
    
    args = parser.parse_args()
    
    result = extract_from_share_link(args.url, args.output)
    
    if result:
        print(f"\n✅ 下载成功: {result}")
        sys.exit(0)
    else:
        print("\n❌ 下载失败")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
野狐围棋分享链接SGF下载器
支持从野狐H5分享链接提取棋谱SGF
自动检测对局状态：已结束使用API，进行中使用WebSocket

用法:
    python3 download_share.py <分享链接> [输出文件]
    
示例:
    python3 download_share.py "https://h5.foxwq.com/yehunewshare/?chessid=12345..."
    python3 download_share.py "https://h5.foxwq.com/..." /tmp/game.sgf
"""

import os
import re
import sys
import json
import asyncio
import argparse
import requests
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
        'uid': params.get('uid', [None])[0],
        'createtime': params.get('createtime', [None])[0],
        'full_url': url
    }

def extract_via_api(chessid):
    """
    通过API获取历史棋谱SGF
    适用于已结束的对局
    
    API端点: https://h5.foxwq.com/yehuDiamond/chessbook_local/YHWQFetchChess
    """
    api_url = f"https://h5.foxwq.com/yehuDiamond/chessbook_local/YHWQFetchChess?chessid={chessid}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
        'Accept': 'application/json',
        'Referer': 'https://h5.foxwq.com/'
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('result') != 0:
            print(f"⚠️ API返回错误码: {data.get('result')}")
            return None
        
        sgf = data.get('chess')
        if not sgf:
            print("⚠️ API未返回棋谱数据")
            return None
        
        return sgf
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ API请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"⚠️ API返回数据解析失败: {e}")
        return None

def extract_game_info(chessid, uid=None):
    """
    获取对局基本信息
    
    API端点: https://h5.foxwq.com/yehuDiamond/chessbook_local/FetchChessSummaryByChessID
    """
    uid_param = f"&uid={uid}" if uid else ""
    api_url = f"https://h5.foxwq.com/yehuDiamond/chessbook_local/FetchChessSummaryByChessID?with_edu=1&chessid={chessid}{uid_param}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
        'Accept': 'application/json',
        'Referer': 'https://h5.foxwq.com/'
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('result') != 0:
            return None
        
        chesslist = data.get('chesslist', {})
        return {
            'black_nick': chesslist.get('blacknick', '黑棋'),
            'white_nick': chesslist.get('whitenick', '白棋'),
            'black_dan': chesslist.get('blackdan', 0),
            'white_dan': chesslist.get('whitedan', 0),
            'result': chesslist.get('result', ''),
            'start_time': chesslist.get('gamestarttime', ''),
            'movenum': chesslist.get('movenum', 0)
        }
        
    except Exception as e:
        return None

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

def extract_handicap_from_binary(data):
    """从二进制数据中提取让子数
    
    野狐WebSocket协议中GameRule结构:
    - 08 xx: boardsize (19 = 0x13)
    - 10 xx: playingType
    - 18 xx: handicap (让子数)
    - 20 xx: komi
    """
    try:
        # 方法1: 查找 GameRule 模式 (08 13 10 01 18 xx)
        # boardsize=19(0x13), playingType=1, handicap=xx
        for i in range(len(data) - 6):
            if (data[i] == 0x08 and data[i+1] == 0x13 and  # boardsize = 19
                data[i+2] == 0x10 and data[i+3] == 0x01 and  # playingType = 1
                data[i+4] == 0x18):  # handicap field
                handicap = data[i+5]
                if 2 <= handicap <= 9:
                    return handicap
        
        # 方法2: 查找 HA[数字] 文本模式（SGF格式）
        text = data.decode('utf-8', errors='ignore')
        ha_match = re.search(r'HA\[(\d+)\]', text)
        if ha_match:
            return int(ha_match.group(1))
        
        return 0
    except Exception:
        return 0

def extract_player_names(data):
    """从二进制数据中提取玩家名"""
    names = []
    try:
        idx = 0
        while idx < len(data) - 3:
            if data[idx] == 0x9a and data[idx+1] == 0x01:
                str_len = data[idx+2]
                if 3 <= str_len <= 20 and idx + 3 + str_len <= len(data):
                    try:
                        name = data[idx+3:idx+3+str_len].decode('utf-8')
                        if name and not name.startswith('http') and len(name) > 1:
                            if name not in ['1.14.205.137', 'avatar']:
                                names.append(name)
                    except:
                        pass
            idx += 1
        
        if not names:
            text = data.decode('utf-8', errors='ignore')
            matches = re.findall(r'([\w\u4e00-\u9fff]+)\[\d+段\]', text)
            names.extend(matches)
        
        seen = set()
        unique_names = []
        for name in names:
            if name not in seen:
                seen.add(name)
                unique_names.append(name)
        
        return unique_names[:2]
    except Exception as e:
        return names

async def extract_via_websocket(url, timeout=15, debug=False):
    """
    通过WebSocket提取棋谱（可选功能，仅用于进行中的对局）
    
    注意: 此功能需要可选依赖 playwright
    历史棋谱请使用 --mode api 模式，无需安装 playwright
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("⚠️  未安装可选依赖: playwright")
        print("   如需提取进行中的对局，请运行:")
        print("   pip3 install playwright && playwright install chromium")
        print()
        print("   💡 提示: 历史棋谱可使用 --mode api 模式，无需 playwright")
        return None, None, 0
    
    moves = []
    player_names = []
    handicap = 0
    raw_data = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
        )
        page = await context.new_page()
        
        def handle_ws(ws):
            async def on_message(data):
                nonlocal moves, player_names, handicap, raw_data
                if isinstance(data, bytes):
                    if len(data) > 1000:
                        raw_data = data
                        if not moves:
                            moves = extract_moves_from_binary(data)
                        if not player_names:
                            player_names = extract_player_names(data)
                        if handicap == 0:
                            handicap = extract_handicap_from_binary(data)
            
            ws.on("framereceived", lambda d: asyncio.create_task(on_message(d)))
        
        page.on("websocket", handle_ws)
        
        with timer.step("WebSocket连接与数据获取"):
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(timeout)
        
        await browser.close()
    
    # 调试模式：保存原始数据供分析
    if debug and raw_data:
        debug_file = f"/tmp/foxwq_ws_debug_{datetime.now().strftime('%H%M%S')}.bin"
        with open(debug_file, 'wb') as f:
            f.write(raw_data)
        print(f"   调试数据已保存: {debug_file}")
        
        # 输出前200字节的十六进制供分析
        print(f"   原始数据前200字节:")
        hex_str = ' '.join(f'{b:02x}' for b in raw_data[:200])
        print(f"   {hex_str}")
        
        # 尝试解码文本部分
        text = raw_data.decode('utf-8', errors='ignore')
        if text:
            print(f"   可解码文本片段:")
            for line in text.split('\x00')[:10]:
                if len(line) > 3 and len(line) < 100:
                    print(f"     {line}")
    
    return moves, player_names, handicap

def create_sgf(moves, pb="黑棋", pw="白棋", handicap=0):
    """创建SGF格式棋谱
    
    让子棋规则：
    - 黑棋先摆好让子（AB标记）
    - 第一手由白棋下
    """
    if not moves:
        return None
    
    coord_map = "abcdefghijklmnopqrs"
    sgf = f"(;GM[1]FF[4]CA[UTF-8]SZ[19]\n"
    sgf += f"PB[{pb}]PW[{pw}]\n"
    
    # 添加让子信息
    if handicap >= 2:
        sgf += f"HA[{handicap}]\n"
        # 添加让子落子（标准星位）
        handicap_coords = {
            2: [(3, 3), (15, 15)],  # 4-4 对角
            3: [(3, 3), (15, 15), (3, 15)],  # 4-4 + 4-16
            4: [(3, 3), (15, 15), (3, 15), (15, 3)],  # 4-4 四角
            5: [(3, 3), (15, 15), (3, 15), (15, 3), (9, 9)],  # 4-4 + 天元
            6: [(3, 3), (15, 15), (3, 15), (15, 3), (9, 3), (9, 15)],  # 4-4 + 边星
            7: [(3, 3), (15, 15), (3, 15), (15, 3), (9, 3), (9, 15), (9, 9)],  # 6子 + 天元
            8: [(3, 3), (15, 15), (3, 15), (15, 3), (9, 3), (9, 15), (3, 9), (15, 9)],  # 4-4 + 边星
            9: [(3, 3), (15, 15), (3, 15), (15, 3), (9, 3), (9, 15), (3, 9), (15, 9), (9, 9)],  # 九星
        }
        if handicap in handicap_coords:
            for hx, hy in handicap_coords[handicap]:
                sgf += f";AB[{coord_map[hx]}{coord_map[hy]}]\n"
    
    # 处理让子棋的着法顺序
    # 有让子时：第一手是白棋（因为黑棋已经摆好让子）
    # 无让子时：第一手是黑棋
    for i, (x, y) in enumerate(moves):
        if handicap >= 2:
            # 让子棋：白棋先下
            color = "W" if i % 2 == 0 else "B"
        else:
            # 普通对局：黑棋先下
            color = "B" if i % 2 == 0 else "W"
        if 0 <= x < 19 and 0 <= y < 19:
            sgf += f";{color}[{coord_map[x]}{coord_map[y]}]\n"
    
    sgf += ")"
    return sgf

def parse_sgf_info(sgf):
    """从SGF中提取信息"""
    info = {}
    
    pb_match = re.search(r'PB\[([^\]]*)\]', sgf)
    pw_match = re.search(r'PW\[([^\]]*)\]', sgf)
    br_match = re.search(r'BR\[([^\]]*)\]', sgf)
    wr_match = re.search(r'WR\[([^\]]*)\]', sgf)
    re_match = re.search(r'RE\[([^\]]*)\]', sgf)
    dt_match = re.search(r'DT\[([^\]]*)\]', sgf)
    
    info['pb'] = pb_match.group(1) if pb_match else '黑棋'
    info['pw'] = pw_match.group(1) if pw_match else '白棋'
    info['br'] = br_match.group(1) if br_match else ''
    info['wr'] = wr_match.group(1) if wr_match else ''
    info['result'] = re_match.group(1) if re_match else ''
    info['date'] = dt_match.group(1) if dt_match else ''
    
    # 计算手数
    moves = re.findall(r';[BW]\[[a-z]{2}\]', sgf)
    info['movenum'] = len(moves)
    
    return info

def extract_from_share_link(url, output_path=None, mode='auto'):
    """
    主函数：从分享链接提取SGF
    
    Args:
        url: 分享链接
        output_path: 输出文件路径（可选）
        mode: 提取模式 ('auto', 'api', 'websocket')
              auto - 自动选择（优先API）
              api - 仅使用API
              websocket - 仅使用WebSocket
    """
    
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
    print(f"  Chess ID: {params['chessid']}")
    print(f"  提取模式: {mode}")
    print()
    
    sgf = None
    game_info = None
    
    # 根据模式选择提取方式
    if mode in ('auto', 'api'):
        print("🔍 尝试通过API获取棋谱...")
        with timer.step("API获取棋谱"):
            sgf = extract_via_api(params['chessid'])
        
        if sgf:
            print("✅ API获取成功！")
            # 同时获取对局信息
            game_info = extract_game_info(params['chessid'], params.get('uid'))
        elif mode == 'api':
            print("❌ API获取失败")
            return None
    
    # 如果API失败且不是仅API模式，尝试WebSocket
    if not sgf and mode in ('auto', 'websocket'):
        print("🌐 尝试通过WebSocket获取棋谱...")
        print("   (适用于进行中的对局)")
        
        moves, player_names, handicap = asyncio.run(extract_via_websocket(url))
        
        if moves:
            print("✅ WebSocket获取成功！")
            pb = player_names[0] if len(player_names) > 0 else "黑棋"
            pw = player_names[1] if len(player_names) > 1 else "白棋"
            
            if handicap > 0:
                print(f"   检测到让子: {handicap}子")
            
            with timer.step("生成SGF"):
                sgf = create_sgf(moves, pb, pw, handicap)
            
            game_info = {
                'pb': pb,
                'pw': pw,
                'movenum': len(moves),
                'handicap': handicap
            }
        else:
            print("❌ WebSocket获取失败")
    
    if not sgf:
        print("\n❌ 无法提取棋谱数据")
        print("   可能原因：")
        print("   - 对局已结束且未保存")
        print("   - 分享链接已过期")
        print("   - 需要登录权限")
        print(timer.format_report())
        return None
    
    # 解析SGF信息
    sgf_info = parse_sgf_info(sgf)
    
    # 合并信息（API信息优先）
    if game_info:
        sgf_info.update({k: v for k, v in game_info.items() if v})
    
    print(f"\n📋 对局详情:")
    print(f"  黑棋: {sgf_info['pb']} {sgf_info['br']}")
    print(f"  白棋: {sgf_info['pw']} {sgf_info['wr']}")
    print(f"  结果: {sgf_info['result']}")
    print(f"  日期: {sgf_info['date']}")
    print(f"  手数: {sgf_info['movenum']}")
    
    # 确定输出路径
    if not output_path:
        output_path = f"/tmp/foxwq_{params['chessid']}.sgf"
    
    # 保存文件
    with timer.step("保存文件"):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sgf)
    
    print(f"\n💾 SGF已保存: {output_path}")
    
    # 显示前10手
    moves = re.findall(r';([BW])\[([a-z]{2})\]', sgf)
    if moves:
        print(f"\n前10手预览:")
        for i, (color, coord) in enumerate(moves[:10]):
            x = ord(coord[0]) - ord('a')
            y = ord(coord[1]) - ord('a')
            color_zh = "黑" if color == "B" else "白"
            coord_str = chr(ord('A') + x) + str(19 - y)
            print(f"  {i+1}. {color_zh}: {coord_str}")
    
    print(timer.format_report())
    
    return output_path

def main():
    parser = argparse.ArgumentParser(
        description='从野狐围棋分享链接下载SGF棋谱',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python3 download_share.py "https://h5.foxwq.com/yehunewshare/?chessid=123..."
  python3 download_share.py "https://h5.foxwq.com/..." /tmp/game.sgf
  python3 download_share.py "..." --mode api        # 仅使用API
  python3 download_share.py "..." --mode websocket  # 仅使用WebSocket
        '''
    )
    
    parser.add_argument('url', help='野狐H5分享链接')
    parser.add_argument('output', nargs='?', help='输出SGF文件路径（可选）')
    parser.add_argument('--mode', choices=['auto', 'api', 'websocket'], 
                       default='auto', help='提取模式 (默认: auto)')
    
    args = parser.parse_args()
    
    result = extract_from_share_link(args.url, args.output, args.mode)
    
    if result:
        print(f"\n✅ 下载成功: {result}")
        sys.exit(0)
    else:
        print("\n❌ 下载失败")
        sys.exit(1)

if __name__ == "__main__":
    main()

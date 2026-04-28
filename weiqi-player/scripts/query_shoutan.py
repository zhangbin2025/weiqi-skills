#!/usr/bin/env python3
"""
手谈等级分查询 - 性能计时版（支持 JSON 输出）
查询围棋选手的手谈等级分、排名等信息
支持显示多个同名选手

使用方法:
    python3 query_shoutan.py 张三
    python3 query_shoutan.py 李四 --json
    python3 query_shoutan.py 王五
"""

import sys
import base64
import json
import time
import argparse
import requests
from contextlib import contextmanager
from collections import OrderedDict

import re


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
        lines.append("⏱️  性能计时报告（手谈查询）")
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


def fetch_url(url, timeout=30):
    """获取URL内容"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers, timeout=timeout)
    return response.text


def parse_shoutan_basic(html, name):
    """
    解析手谈等级分基础信息（支持多同名选手）
    提取表格中的选手数据
    """
    players = []
    
    # 检查是否有多个选手（通过"请确认您要查看的选手"判断）
    if '请确认您要查看的选手' in html or 'onclick="ChooseQy' in html:
        # 多个选手 - 解析选择列表
        # 匹配: <td align="center">姓名</td><td align="center">地区</td>...
        #       <tr onclick="ChooseQy(...)">...</tr>
        
        # 查找所有选手行
        pattern = r'<tr[^>]*onclick="ChooseQy\((\d+),\s*\'([^\']+)\'\)"[^>]*>.*?<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>.*?</tr>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for match in matches:
            user_id, player_id = match[0], match[1]
            name_cell = match[2]
            region = match[3].strip()
            title = match[4].strip()
            rating = match[5].strip()
            rank = match[6].strip()
            games = match[7].strip()
            
            # 提取姓名（去除HTML标签）
            clean_name = re.sub(r'<[^>]+>', '', name_cell).strip()
            
            player = {
                "姓名": clean_name,
                "地区": region,
                "称谓": title,
                "等级分": rating,
                "全国排名": rank,
                "对局次数": games,
                "Yh": user_id,
                "编号": player_id
            }
            players.append(player)
    else:
        # 单个选手 - 解析详情页
        # 尝试提取基本信息
        if '未找到任何记录' in html or '找不到符合条件的数据' in html:
            return []
        
        # 尝试从HTML提取选手信息（详情页格式）
        # 查找姓名、地区等信息
        name_match = re.search(r'姓名[:：]\s*<[^>]*>([^<]+)</td>', html)
        region_match = re.search(r'地区[:：]\s*<[^>]*>([^<]+)</td>', html)
        title_match = re.search(r'段位[:：]\s*<[^>]*>([^<]+)</td>', html)
        rating_match = re.search(r'等级分[:：]\s*<[^>]*>([^<]+)</td>', html)
        rank_match = re.search(r'全国排名[:：]\s*<[^>]*>([^<]+)</td>', html)
        games_match = re.search(r'对局[:：]\s*<[^>]*>([^<]+)</td>', html)
        
        if name_match:
            player = {
                "姓名": name_match.group(1).strip(),
                "地区": region_match.group(1).strip() if region_match else "未知",
                "称谓": title_match.group(1).strip() if title_match else "",
                "等级分": rating_match.group(1).strip() if rating_match else "",
                "全国排名": rank_match.group(1).strip() if rank_match else "",
                "对局次数": games_match.group(1).strip() if games_match else "",
                "Yh": "",
                "编号": ""
            }
            players.append(player)
    
    return players


def get_detail_url(player, base_url="https://v.dzqzd.com/SpBody.aspx"):
    """生成选手详细记录链接"""
    if not player.get('Yh') or not player.get('编号'):
        return None
    
    xml = f'<Redi Ns="Sp" Jk="等级分明细" Yh="{player["Yh"]}" 选手号="{player["编号"]}"/>'
    encoded = base64.b64encode(xml.encode('utf-8')).decode('utf-8')
    return f"{base_url}?r={encoded}"


def query_shoutan(name, timer):
    """
    查询手谈等级分（支持多同名选手）
    
    Args:
        name: 选手姓名
        timer: 性能计时器实例
    
    Returns:
        list: 选手信息列表（可能包含多个同名选手）
    """
    base_url = "https://v.dzqzd.com/SpBody.aspx"
    
    # 步骤1: 构造查询参数
    with timer.step("构造查询参数"):
        xml = f'<Redi Ns="Sp" Jk="选手查询" 姓名="{name}"/>'
        encoded = base64.b64encode(xml.encode('utf-8')).decode('utf-8')
        url = f"{base_url}?r={encoded}"
    
    # 步骤2: 发送HTTP请求
    with timer.step("HTTP请求"):
        try:
            html = fetch_url(url)
        except Exception as e:
            raise Exception(f"查询失败: {e}")
    
    # 步骤3: 解析HTML内容
    with timer.step("解析HTML"):
        players = parse_shoutan_basic(html, name)
    
    return players


def format_player_info_single_line(player):
    """格式化单个选手信息为单行 Markdown 格式"""
    parts = []
    parts.append(f"**{player['姓名']}** ({player['地区']})")
    
    if player.get('称谓'):
        parts.append(f"段位: {player['称谓']}")
    if player.get('等级分'):
        parts.append(f"等级分: {player['等级分']}")
    if player.get('全国排名'):
        parts.append(f"全国排名: {player['全国排名']}")
    if player.get('对局次数'):
        parts.append(f"对局: {player['对局次数']}局")
    
    return " | ".join(parts)


def format_output(players, timer):
    """格式化输出结果 - Markdown 格式"""
    name = players[0]['姓名'] if players else '未知'
    output = []
    output.append(f"\n📋 **{name}** - 手谈等级分查询结果\n")
    
    if len(players) > 1:
        output.append(f"⚠️ 找到 {len(players)} 位同名选手\n")
    
    for i, player in enumerate(players, 1):
        if len(players) > 1:
            output.append(f"{i}. {format_player_info_single_line(player)}")
        else:
            output.append(format_player_info_single_line(player))
        
        # 生成详细记录链接
        detail_url = get_detail_url(player)
        if detail_url:
            display_name = player['地区']
            output.append(f"   👉 [查看{display_name}详细记录]({detail_url})\n")
    
    # 输出性能报告
    output.append(timer.format_report())
    return "\n".join(output)


def format_json_output(players, timer, name):
    """格式化输出结果 - JSON 格式"""
    result = {
        "found": len(players) > 0,
        "count": len(players),
        "name": name,
        "players": []
    }
    
    for player in players:
        player_data = {
            "name": player.get("姓名", ""),
            "city": player.get("地区", ""),
            "level": player.get("称谓", ""),
            "rating": float(player.get("等级分", 0)) if player.get("等级分") else 0,
            "rank": int(player.get("全国排名", 0)) if player.get("全国排名") else 0,
            "games": int(player.get("对局次数", 0)) if player.get("对局次数") else 0,
            "detail_url": get_detail_url(player)
        }
        result["players"].append(player_data)
    
    result["performance"] = timer.to_dict()
    
    return json.dumps(result, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='查询手谈等级分')
    parser.add_argument('name', help='选手姓名')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    args = parser.parse_args()
    
    name = args.name
    
    # 创建计时器并启动
    timer = PerformanceTimer()
    timer.start()
    
    try:
        # 执行查询
        players = query_shoutan(name, timer)
        
        if players:
            if args.json:
                print(format_json_output(players, timer, name))
            else:
                print(format_output(players, timer))
        else:
            if args.json:
                result = {
                    "found": False,
                    "count": 0,
                    "name": name,
                    "players": [],
                    "error": f"未找到选手 '{name}' 的信息",
                    "performance": timer.to_dict()
                }
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"\n❌ 未找到选手 '{name}' 的信息")
                print(timer.format_report())
    except Exception as e:
        if args.json:
            result = {
                "found": False,
                "count": 0,
                "name": name,
                "players": [],
                "error": str(e),
                "performance": timer.to_dict()
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n❌ 查询失败: {e}")
            print(timer.format_report())


if __name__ == "__main__":
    main()

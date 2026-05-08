#!/usr/bin/env python3
"""
易查分平台围棋业余段位查询 - HTTP 请求版（支持 JSON 输出）
使用 requests 库发送 HTTP 请求，无需 Playwright

性能：~1-2秒/查询（相比 Playwright 的 8-10 秒）

【单个查询】
    python3 query_yichafen.py 张三
    python3 query_yichafen.py 李四 --json

【批量查询】
    python3 query_yichafen.py --batch 张三 李四 王五
    python3 query_yichafen.py --batch 赵六 孙七 --json
"""

import sys
import json
import time
import os
import re
import argparse
import requests
from datetime import datetime

# 配置
BASE_URL = "https://yeyuweiqi.yichafen.com/qz/s9W2g0zKmt"
VERIFY_URL = "https://yeyuweiqi.yichafen.com/public/verifycondition/sqcode/MsjcAn0mNDU5N3xjYTNmMGU0OWQxN2IwNzEyMTQ2YTViM2ZjZGY1M2VjZnwxMjc0MTQO0O0O/from_device/mobile.html"
RESULT_URL = "https://yeyuweiqi.yichafen.com/public/queryresult/from_device/mobile.html"


def create_session():
    """创建 session 并访问主页获取 cookie"""
    session = requests.Session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # 访问主页，获取 session/cookie
    session.get(BASE_URL, headers=headers, timeout=30)
    
    return session, headers


def query_player(name, session=None, headers=None):
    """
    查询单个选手的业余段位信息
    
    Args:
        name: 选手姓名
        session: requests.Session 实例（可选）
        headers: 请求头（可选）
    
    Returns:
        dict: 选手信息字典
    """
    start_time = time.time()
    
    # 创建 session
    if session is None:
        session, headers = create_session()
    
    headers['Referer'] = BASE_URL
    
    try:
        # 第一步：POST 请求查询
        data = {'s_xingming': name}
        response = session.post(VERIFY_URL, data=data, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return {
                'found': False,
                'error': f'HTTP {response.status_code}',
                'name': name
            }
        
        # 检查是否查询成功
        if '查询成功' not in response.text and 'status":1' not in response.text:
            # 可能是验证码或其他错误
            if '验证码' in response.text:
                return {
                    'found': False,
                    'error': '需要验证码',
                    'name': name
                }
            return {
                'found': False,
                'error': '查询失败',
                'name': name
            }
        
        # 第二步：访问结果页面
        response = session.get(RESULT_URL, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return {
                'found': False,
                'error': f'HTTP {response.status_code}',
                'name': name
            }
        
        # 检查是否有来源异常
        if '来源异常' in response.text or '请从查分主页登陆' in response.text:
            return {
                'found': False,
                'error': '来源验证失败',
                'name': name
            }
        
        # 解析选手信息
        info = parse_player_info(response.text)
        
        elapsed = time.time() - start_time
        
        return {
            'found': info is not None,
            'name': name,
            'info': info,
            'elapsed': round(elapsed, 2)
        }
        
    except Exception as e:
        return {
            'found': False,
            'error': str(e),
            'name': name
        }


def parse_player_info(html):
    """
    从 HTML 中解析选手信息
    
    Args:
        html: HTML 文本
    
    Returns:
        dict: 选手信息字典
    """
    info = {
        'name': '',
        'level': '',        # 段位
        'rating': '',       # 等级分
        'rank_total': '',   # 总排名
        'rank_province': '',# 省区排名
        'rank_city': '',    # 本市排名
        'rank_age': '',     # 同龄排名
        'rank_u18': '',     # U18排名
        'gender': '',       # 性别
        'birth_year': '',   # 出生年份
        'province': '',     # 省区
        'city': '',         # 城市
        'games_total': '',  # 总对局数
        'games_year': '',   # 年度对局
        'wins_year': '',    # 年度胜局
        'last_game': '',    # 最近对局
        'cert_date': '',    # 发证日期
        'note': ''          # 备注
    }
    
    # 提取姓名（在 font-size:36px 的 div 中）
    name_match = re.search(r'<div style="font-size:36px;">([^<]+)</div>', html)
    if name_match:
        info['name'] = name_match.group(1).strip()
    
    # 提取段位（类似格式的第二个 div）
    name_matches = re.findall(r'<div style="font-size:36px;">([^<]+)</div>', html)
    if len(name_matches) >= 2:
        info['level'] = name_matches[1].strip()
    
    # 提取等级分
    rating_match = re.search(r'等级分.*?<div[^>]*>([\d.]+)</div>', html, re.DOTALL)
    if rating_match:
        info['rating'] = rating_match.group(1).strip()
    
    # 提取表格中的信息
    # 格式：<td class="left_cell"><span >总排名</span></td><td class="right_cell">777</td>
    def extract_field(label):
        pattern = rf'<span[^>]*>\s*{re.escape(label)}\s*</span>.*?<td class="right_cell">([^<]+)</td>'
        match = re.search(pattern, html, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ''
    
    info['rank_total'] = extract_field('总排名')
    info['rank_province'] = extract_field('省区排名')
    info['rank_city'] = extract_field('本市排名')
    info['rank_age'] = extract_field('同龄排名')
    info['rank_u18'] = extract_field('U18排名')
    info['gender'] = extract_field('性别')
    info['birth_year'] = extract_field('出生')
    info['province'] = extract_field('省区')
    info['city'] = extract_field('城市')
    info['games_total'] = extract_field('总对局数')
    info['games_year'] = extract_field('年度对局')
    info['wins_year'] = extract_field('年度胜局')
    info['last_game'] = extract_field('最近对局')
    info['cert_date'] = extract_field('发证日期')
    info['note'] = extract_field('备注')
    
    # 检查是否有有效信息
    if not info['name'] and not info['level']:
        return None
    
    return info


def format_output(result, json_output=False):
    """格式化输出结果"""
    if json_output:
        # 保持和原来一致的 JSON 格式
        info = result.get('info', {})
        output = {
            "found": result.get('found', False),
            "name": result.get('name', ''),
            "level": info.get('level', ''),
            "rating": float(info.get('rating', 0)) if info.get('rating') else 0,
            "total_rank": int(info.get('rank_total', 0)) if info.get('rank_total') else 0,
            "province_rank": int(info.get('rank_province', 0)) if info.get('rank_province') else 0,
            "city_rank": int(info.get('rank_city', 0)) if info.get('rank_city') else 0,
            "gender": info.get('gender', ''),
            "birth_year": info.get('birth_year', ''),
            "province": info.get('province', ''),
            "city": info.get('city', ''),
            "notes": info.get('note', ''),
            "query_time": result.get('elapsed', 0)
        }
        return json.dumps(output, ensure_ascii=False, indent=2)
    
    if not result.get('found'):
        return f"❌ {result['name']}: {result.get('error', '未找到')}"
    
    info = result.get('info', {})
    lines = []
    
    lines.append(f"\n{'='*50}")
    lines.append(f"📋 {info.get('name', result['name'])} - 易查分业余段位")
    lines.append(f"{'='*50}")
    
    if info.get('level'):
        lines.append(f"🏆 段位: {info['level']}")
    if info.get('rating'):
        lines.append(f"📊 等级分: {info['rating']}")
    
    lines.append("")
    
    if info.get('rank_total'):
        lines.append(f"📌 总排名: {info['rank_total']}")
    if info.get('rank_province'):
        lines.append(f"📍 省区排名: {info['rank_province']}")
    if info.get('rank_city'):
        lines.append(f"🏙️  本市排名: {info['rank_city']}")
    
    lines.append("")
    
    if info.get('province') or info.get('city'):
        lines.append(f"🌍 地区: {info.get('province', '')} {info.get('city', '')}")
    if info.get('gender') or info.get('birth_year'):
        lines.append(f"👤 性别: {info.get('gender', '')} | 出生: {info.get('birth_year', '')}")
    
    if info.get('games_total'):
        lines.append(f"🎮 总对局: {info['games_total']}")
    if info.get('last_game'):
        lines.append(f"📅 最近对局: {info['last_game']}")
    
    if result.get('elapsed'):
        lines.append(f"\n⏱️  查询耗时: {result['elapsed']}秒")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='易查分业余段位查询（HTTP 请求版）')
    parser.add_argument('name', nargs='*', help='选手姓名')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    parser.add_argument('--batch', action='store_true', help='批量查询模式')
    args = parser.parse_args()
    
    if not args.name:
        print(__doc__)
        print("\n【单个查询】")
        print("  python3 query_yichafen.py 张三")
        print("  python3 query_yichafen.py 李四 --json")
        print("\n【批量查询】")
        print("  python3 query_yichafen.py --batch 张三 李四 王五")
        sys.exit(0)
    
    names = args.name
    
    # 创建 session（复用于所有查询）
    session, headers = create_session()
    
    if args.batch:
        # 批量查询
        results = []
        for name in names:
            result = query_player(name, session, headers)
            results.append(result)
            if not args.json:
                print(format_output(result))
        
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        # 单个查询
        result = query_player(names[0], session, headers)
        print(format_output(result, args.json))


if __name__ == "__main__":
    main()

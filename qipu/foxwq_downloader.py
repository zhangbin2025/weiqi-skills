#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
野狐围棋棋谱自动下载脚本
自动下载指定日期的棋谱并发送邮件报告
"""

import os
import re
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin
import subprocess
from contextlib import contextmanager
from collections import OrderedDict

# 尝试导入requests，如果不存在则使用urllib
import urllib.request
import urllib.error
import ssl

# HTML解析库
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("⚠️  BeautifulSoup 未安装，将使用正则解析作为备选")

# 禁用SSL验证（部分网站需要）
ssl._create_default_https_context = ssl._create_unverified_context

# ===== 性能计时工具 =====
class PerformanceTimer:
    """性能计时器 - 追踪每个步骤的执行耗时"""
    def __init__(self):
        self.timings = OrderedDict()
        self.start_time = None
        self.step_start = None
    
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
        """格式化计时报告"""
        lines = []
        lines.append("\n" + "="*50)
        lines.append("⏱️  性能计时报告")
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

# 全局计时器实例
timer = PerformanceTimer()

# 配置
WORK_DIR = "/root/.openclaw/workspace/qipu"
EMAIL_SCRIPT = "/root/.openclaw/workspace/send_email.py"
TO_EMAIL = "195021300@qq.com"
BASE_URL = "https://www.foxwq.com"
LIST_URL = "https://www.foxwq.com/qipu.html"

def fetch_url(url):
    """获取URL内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"❌ 获取失败 {url}: {e}")
        return None

def extract_qipu_links(html, target_date):
    """从HTML中提取指定日期的棋谱链接"""
    links = []
    
    if BS4_AVAILABLE:
        # 使用 BeautifulSoup 高效解析
        soup = BeautifulSoup(html, 'lxml')
        
        # 查找所有表格行
        for row in soup.find_all('tr'):
            # 获取日期单元格
            date_cells = row.find_all('td')
            if len(date_cells) < 2:
                continue
            
            # 检查日期是否匹配（最后一个td通常是日期）
            date_text = date_cells[-1].get_text(strip=True)
            if not date_text.startswith(target_date):
                continue
            
            # 查找链接和标题
            link_tag = row.find('a', href=re.compile(r'/qipu/newlist/id/\d+\.html'))
            if not link_tag:
                continue
            
            # 提取标题（在h4标签内或a标签文本）
            title_tag = link_tag.find('h4')
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                title = link_tag.get_text(strip=True)
            
            # 清理标题
            title = title.replace('\n', ' ').replace('\r', '').replace('&nbsp;', ' ')
            
            full_url = urljoin(BASE_URL, link_tag['href'])
            links.append({
                'title': title,
                'url': full_url,
                'date': target_date
            })
    else:
        # 备选：使用正则解析（较慢）
        pattern = r'<tr[^>]*>.*?<a[^>]*href="(/qipu/newlist/id/\d+\.html)"[^>]*>.*?<h4[^>]*>(.*?)</h4>.*?</td>.*?<td[^>]*>' + re.escape(target_date) + r'[^<]*</td>.*?</tr>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        for path, title in matches:
            full_url = urljoin(BASE_URL, path)
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            clean_title = clean_title.replace('&nbsp;', ' ')
            links.append({
                'title': clean_title,
                'url': full_url,
                'date': target_date
            })
    
    return links

def extract_sgf(html):
    """从HTML中提取SGF格式的棋谱"""
    # SGF格式以 (;GM[ 开头
    match = re.search(r'\(;GM\[1\]FF\[4\].*?\)\s*\)\s*\)', html, re.DOTALL)
    if match:
        sgf = match.group(0)
        # 清理可能的截断
        sgf = re.sub(r'\n\s*<<<END_EXTERNAL.*', '', sgf)
        return sgf
    
    # 尝试更宽松的匹配
    match = re.search(r'\(;GM\[1\]FF\[4\].*', html, re.DOTALL)
    if match:
        sgf = match.group(0)
        # 清理截断内容
        sgf = re.sub(r'\n\s*<<<END_EXTERNAL.*', '', sgf)
        sgf = re.sub(r'/"juey.*', ')', sgf)
        # 尝试平衡括号
        open_count = sgf.count('(')
        close_count = sgf.count(')')
        if open_count > close_count:
            sgf += ')' * (open_count - close_count)
        return sgf
    
    return None

def download_qipu(link_info, save_dir):
    """下载单个棋谱"""
    print(f"📥 下载: {link_info['title']}")
    
    html = fetch_url(link_info['url'])
    if not html:
        return None
    
    sgf = extract_sgf(html)
    if not sgf:
        print(f"  ⚠️ 无法提取SGF内容")
        return None
    
    # 生成文件名
    safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', link_info['title'])[:50]
    # 从URL中提取ID
    match = re.search(r'/id/(\d+)', link_info['url'])
    file_id = match.group(1) if match else datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{file_id}_{safe_title}.sgf"
    filepath = os.path.join(save_dir, filename)
    
    # 保存文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(sgf)
    
    print(f"  ✅ 已保存: {filename}")
    return {
        'filename': filename,
        'title': link_info['title'],
        'path': filepath
    }

def send_email_report(target_date, success_list, failed_list, timer=None):
    """发送邮件报告"""
    success_count = len(success_list)
    failed_count = len(failed_list)
    
    # 构建性能报告部分
    perf_section = ""
    if timer:
        perf_section = "\n=============================\n⏱️  性能计时\n=============================\n\n"
        for name, elapsed in timer.timings.items():
            perf_section += f"  {name:20s} : {elapsed:>8.3f}s\n"
        perf_section += f"\n  {'总耗时':20s} : {timer.get_total():>8.3f}s\n"
    
    if success_count > 0:
        subject = f"野狐围棋棋谱下载报告 - {target_date}"
        body = f"""🎯 野狐围棋棋谱下载报告

下载日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
目标日期: {target_date}

=============================
📊 下载统计
=============================

✅ 下载成功: {success_count} 局
❌ 下载失败: {failed_count} 局

=============================
📁 下载的棋谱
=============================
"""
        for item in success_list:
            body += f"\n• {item['title']}\n  文件: {item['filename']}\n"
        
        body += perf_section
        body += """
---
本邮件由 OpenClaw 自动发送
"""
    else:
        subject = f"野狐围棋棋谱下载报告 - {target_date}"
        body = f"""🎯 野狐围棋棋谱下载报告

下载日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
目标日期: {target_date}

=============================
📊 下载统计
=============================

📋 今日无新棋谱下载

可能原因:
- 野狐围棋网站昨日无职业比赛
- 网站访问受限

网站地址: https://www.foxwq.com/qipu.html
"""
        body += perf_section
        body += """
---
本邮件由 OpenClaw 自动发送
"""
    
    # 发送邮件
    if os.path.exists(EMAIL_SCRIPT):
        cmd = ['python3', EMAIL_SCRIPT, '--to', TO_EMAIL, '--subject', subject, '--body', body]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"❌ 邮件发送失败: {result.stderr}")
    else:
        print(f"❌ 邮件脚本不存在: {EMAIL_SCRIPT}")

def main():
    # 获取昨天日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    target_date = sys.argv[1] if len(sys.argv) > 1 else yesterday
    
    print(f"🎯 野狐围棋棋谱下载")
    print(f"目标日期: {target_date}")
    print(f"{'='*50}")
    
    # 启动性能计时
    timer.start()
    
    # 创建保存目录
    save_dir = os.path.join(WORK_DIR, target_date)
    with timer.step("创建目录"):
        os.makedirs(save_dir, exist_ok=True)
    print(f"保存路径: {save_dir}")
    print()
    
    # 获取列表页
    print("📄 获取棋谱列表...")
    with timer.step("获取列表页"):
        html = fetch_url(LIST_URL)
    if not html:
        print("❌ 无法获取列表页")
        print(timer.format_report())
        send_email_report(target_date, [], ["无法获取列表页"], timer)
        return
    
    # 提取链接
    with timer.step("解析棋谱链接"):
        links = extract_qipu_links(html, target_date)
    print(f"✅ 找到 {len(links)} 个{target_date}的棋谱")
    print()
    
    if not links:
        print("📋 今日无新棋谱")
        print(timer.format_report())
        send_email_report(target_date, [], [], timer)
        return
    
    # 下载棋谱
    success_list = []
    failed_list = []
    
    with timer.step(f"下载{len(links)}个棋谱"):
        for link in links:
            result = download_qipu(link, save_dir)
            if result:
                success_list.append(result)
            else:
                failed_list.append(link['title'])
    
    print()
    print(f"{'='*50}")
    print(f"📊 下载完成: 成功 {len(success_list)} / 失败 {len(failed_list)}")
    
    # 打印性能报告到控制台
    print(timer.format_report())
    
    # 发送邮件报告（包含性能数据）
    with timer.step("发送邮件"):
        send_email_report(target_date, success_list, failed_list, timer)

if __name__ == "__main__":
    main()

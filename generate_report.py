#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime

DATE = "2026-03-13"
QIPU_DIR = f"/root/.openclaw/workspace/qipu/{DATE}"

# 棋谱信息
games_info = [
    {
        "filename": "2026031356342596_zhouhongyu_vs_shangyelisha.sgf",
        "title": "第8届扇兴杯世界女子最强战8强 周泓余执黑中盘胜上野梨纱",
        "date": "2026-03-13 15:39",
        "black": "周泓余 P7段",
        "white": "上野梨纱 P2段",
        "result": "B+R (黑中盘胜)"
    },
    {
        "filename": "2026031351544694_jineunchi_vs_jiatengqianxiao.sgf",
        "title": "第8届扇兴杯世界女子最强战8强 金恩持执黑中盘胜加藤千笑",
        "date": "2026-03-13 14:19",
        "black": "김은지 (金恩持) P9段",
        "white": "加藤千笑 P4段",
        "result": "B+R (黑中盘胜)"
    },
    {
        "filename": "2026031350795502_fuzelinai_vs_yangzixuan.sgf",
        "title": "第8届扇兴杯世界女子最强战8强 藤泽里菜执白中盘胜杨子萱",
        "date": "2026-03-13 14:06",
        "black": "杨子萱 P6段",
        "white": "藤沢里菜 (藤泽里菜) P7段",
        "result": "W+R (白中盘胜)"
    },
    {
        "filename": "2026031343947660_shangyeaixiaomei_vs_tangsamu.sgf",
        "title": "第8届扇兴杯世界女子最强战8强 上野爱咲美执白中盘胜唐萨姆",
        "date": "2026-03-13 12:12",
        "black": "DawnSum (唐萨姆) 9段",
        "white": "上野愛咲美 (上野爱咲美) P6段",
        "result": "W+R (白中盘胜)"
    },
    {
        "filename": "2026031336713449_liuyuncheng_vs_zhangxinyu.sgf",
        "title": "衢州葛道职业训练赛 刘云程执白中盘胜张歆宇",
        "date": "2026-03-13 10:11",
        "black": "张歆宇 P5段",
        "white": "刘云程 P4段",
        "result": "W+R (白中盘胜)"
    }
]

# 验证文件
success_count = 0
failed = []
for game in games_info:
    filepath = os.path.join(QIPU_DIR, game["filename"])
    if os.path.exists(filepath):
        success_count += 1
        game["status"] = "✓ 成功"
        game["size"] = os.path.getsize(filepath)
    else:
        game["status"] = "✗ 失败"
        failed.append(game["filename"])

# 生成邮件内容
subject = f"野狐围棋棋谱下载报告 - {DATE}"

body = f"""野狐围棋棋谱下载报告
{'='*60}

下载日期: {DATE}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

【下载统计】
- 成功: {success_count} 局
- 失败: {len(failed)} 局
- 保存路径: {QIPU_DIR}

【棋谱详情】
"""

for i, game in enumerate(games_info, 1):
    body += f"""
{i}. {game['title']}
   文件名: {game['filename']}
   对局时间: {game['date']}
   黑方: {game['black']}
   白方: {game['white']}
   结果: {game['result']}
   状态: {game['status']}
"""

body += f"""
{'='*60}

【赛事汇总】
第8届扇兴杯世界女子最强战8强: 4局
衢州葛道职业训练赛: 1局

【备注】
- 棋谱使用SGF格式保存
- 可使用围棋软件（如弈客、野狐围棋、Sabaki等）打开查看
- 棋谱包含绝艺AI讲解数据

{'='*60}
自动发送 | OpenClaw 野狐围棋棋谱下载器
"""

# 发送邮件
print("="*60)
print("野狐围棋棋谱下载报告")
print("="*60)
print(f"\n下载日期: {DATE}")
print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\n成功下载: {success_count} 局")
print(f"保存路径: {QIPU_DIR}")
print(f"\n{'='*60}")
print("正在发送邮件...")

# 调用邮件脚本
result = subprocess.run([
    "python3", "/root/.openclaw/workspace/send_email.py",
    "--to", "195021300@qq.com",
    "--subject", subject,
    "--body", body
], capture_output=True, text=True)

if result.returncode == 0:
    print("✓ 邮件发送成功!")
else:
    print(f"✗ 邮件发送失败: {result.stderr}")

print("="*60)

# 同时保存报告到文件
report_path = f"/root/.openclaw/workspace/qipu/report_{DATE}.txt"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(body)
print(f"报告已保存到: {report_path}")

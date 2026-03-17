#!/usr/bin/env python3
"""
易查分平台围棋业余段位查询 - 浏览器会话复用优化版

优化点：
- 首次查询启动浏览器并保持会话
- 后续查询复用同一会话，只刷新页面
- 从 10-15秒 降到 3-5秒

使用方法：
    python3 yichafen_query.py 朱玲钰
    python3 yichafen_query.py 熊益成
    python3 yichafen_query.py 田翔宇
"""

import subprocess
import sys
import json
import time
import os

# 会话状态文件
SESSION_FILE = "/tmp/yichafen_session.json"
BASE_URL = "https://yeyuweiqi.yichafen.com/qz/s9W2g0zKmt"


def run_browser_command(args, wait=True):
    """执行 browser 命令"""
    cmd = ["openclaw", "browser"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"命令失败: {' '.join(cmd)}")
        print(f"错误: {result.stderr}")
        return None
    return result.stdout.strip()


def get_session():
    """获取当前会话ID"""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                data = json.load(f)
                return data.get('targetId')
        except:
            pass
    return None


def save_session(target_id):
    """保存会话ID"""
    with open(SESSION_FILE, 'w') as f:
        json.dump({'targetId': target_id, 'timestamp': time.time()}, f)


def clear_session():
    """清除会话"""
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)


def is_session_valid():
    """检查会话是否仍然有效（5分钟内）"""
    if not os.path.exists(SESSION_FILE):
        return False
    try:
        with open(SESSION_FILE, 'r') as f:
            data = json.load(f)
            timestamp = data.get('timestamp', 0)
            # 5分钟内有效
            return time.time() - timestamp < 300
    except:
        return False


def init_browser():
    """初始化浏览器并返回 targetId"""
    print("🚀 首次查询，启动浏览器...")
    
    # 启动浏览器并打开页面
    result = run_browser_command(["open", BASE_URL])
    if not result:
        return None
    
    # 等待页面加载
    time.sleep(2)
    
    # 获取页面快照以确认加载成功
    snapshot = run_browser_command(["snapshot"])
    if not snapshot or "请输入姓名" not in snapshot:
        print("⚠️ 页面加载异常")
        return None
    
    # 获取 targetId（从 browser status 或 snapshot 中解析）
    # 这里我们使用一个简化方式：保存当前状态
    save_session("active")
    print("✅ 浏览器初始化完成")
    return "active"


def query_with_browser(name):
    """使用浏览器查询"""
    
    # 检查会话是否有效
    if not is_session_valid():
        # 关闭旧浏览器（如果有）
        try:
            run_browser_command(["stop"])
            time.sleep(1)
        except:
            pass
        
        # 重新初始化
        if not init_browser():
            return None
    else:
        print("🔄 复用现有浏览器会话...")
        # 刷新页面
        run_browser_command(["navigate", BASE_URL])
        time.sleep(1)
    
    # 获取页面元素
    snapshot = run_browser_command(["snapshot"])
    if not snapshot:
        print("❌ 无法获取页面快照")
        return None
    
    # 查找输入框和查询按钮的 ref
    # 根据快照格式解析 refs
    input_ref = None
    button_ref = None
    
    # 简单解析：查找包含特定文本的行
    for line in snapshot.split('\n'):
        if '请输入姓名' in line or 'textbox' in line.lower():
            # 提取 ref，格式如 [ref=e1]
            import re
            match = re.search(r'\[ref=([^\]]+)\]', line)
            if match:
                input_ref = match.group(1)
        if '查询' in line and ('button' in line.lower() or 'link' in line.lower()):
            import re
            match = re.search(r'\[ref=([^\]]+)\]', line)
            if match:
                button_ref = match.group(1)
    
    if not input_ref:
        print("❌ 未找到姓名输入框")
        return None
    
    if not button_ref:
        print("❌ 未找到查询按钮")
        return None
    
    print(f"📍 找到输入框 ref={input_ref}, 按钮 ref={button_ref}")
    
    # 清空输入框并填写姓名
    print(f"📝 填写姓名: {name}")
    run_browser_command(["act", "--kind", "fill", "--ref", input_ref, "--text", name])
    time.sleep(0.5)
    
    # 点击查询按钮
    print("🔍 点击查询...")
    run_browser_command(["act", "--kind", "click", "--ref", button_ref])
    time.sleep(2)  # 等待结果加载
    
    # 获取结果
    print("📊 获取查询结果...")
    result_text = run_browser_command(["act", "--kind", "evaluate", "--fn", "document.body.innerText"])
    
    # 更新会话时间
    save_session("active")
    
    return result_text


def parse_result(text):
    """解析查询结果"""
    if not text:
        return None
    
    lines = text.strip().split('\n')
    result = {}
    
    # 简单解析关键字段
    current_key = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 判断是否是主要字段
        if '段位' in line and '段' in line:
            result['段位'] = line
        elif '等级分' in line and len(line) < 20:
            result['等级分标题'] = line
        elif '总排名' in line:
            parts = line.split()
            if len(parts) >= 2:
                result['总排名'] = parts[1]
        elif '省区排名' in line:
            parts = line.split()
            if len(parts) >= 2:
                result['省区排名'] = parts[1]
        elif '性别' in line:
            parts = line.split()
            if len(parts) >= 2:
                result['性别'] = parts[1]
        elif '出生' in line:
            parts = line.split()
            if len(parts) >= 2:
                result['出生年份'] = parts[1]
        elif '省区' in line and '省区排名' not in line:
            parts = line.split()
            if len(parts) >= 2:
                result['省区'] = parts[1]
        elif '城市' in line:
            parts = line.split()
            if len(parts) >= 2:
                result['城市'] = parts[1]
        elif '总对局数' in line:
            parts = line.split()
            if len(parts) >= 2:
                result['总对局数'] = parts[1]
        elif line.replace('.', '').replace('-', '').isdigit() and '等级分' not in result:
            # 可能是等级分数字
            if float(line) > 1000:  # 等级分通常在1000以上
                result['等级分'] = line
    
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python3 yichafen_query.py <姓名>")
        print("示例: python3 yichafen_query.py 朱玲钰")
        sys.exit(1)
    
    name = sys.argv[1]
    print(f"\n{'='*40}")
    print(f"查询选手: {name}")
    print(f"{'='*40}\n")
    
    start_time = time.time()
    
    # 执行查询
    result_text = query_with_browser(name)
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  查询耗时: {elapsed:.1f}秒\n")
    
    if result_text:
        print("原始结果:")
        print("-" * 40)
        print(result_text[:2000])  # 限制输出长度
        print("-" * 40)
        
        # 尝试解析
        parsed = parse_result(result_text)
        if parsed:
            print("\n解析结果:")
            for k, v in parsed.items():
                print(f"  {k}: {v}")
    else:
        print("❌ 查询失败")


if __name__ == "__main__":
    main()

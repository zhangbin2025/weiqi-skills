#!/usr/bin/env python3
"""
易查分查询调试脚本 - 带详细日志
"""
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ 请先安装 Playwright")
    sys.exit(1)

BASE_URL = "https://yeyuweiqi.yichafen.com/qz/s9W2g0zKmt"

def debug_query(name):
    print(f"🔍 调试查询: {name}")
    print("="*50)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        page = browser.new_page()
        
        # 加载页面
        print("1️⃣ 加载页面...")
        page.goto(BASE_URL, wait_until='networkidle')
        print(f"   页面标题: {page.title()}")
        
        # 检查页面内容
        print("\n2️⃣ 检查页面元素...")
        body_text = page.locator('body').inner_text()
        print(f"   页面文本长度: {len(body_text)} 字符")
        
        # 查找输入框
        input_selector = 'input[name="s_xingming"]'
        input_box = page.locator(input_selector)
        print(f"   输入框存在: {input_box.count() > 0}")
        
        if input_box.count() == 0:
            # 尝试其他选择器
            input_box = page.locator('input[type="text"]').first
            print(f"   备用输入框存在: {input_box.count() > 0}")
        
        # 填写姓名
        print(f"\n3️⃣ 填写姓名: {name}")
        input_box.fill(name)
        time.sleep(0.5)
        
        # 查找查询按钮
        button_selector = '#yiDunSubmitBtn'
        button = page.locator(button_selector)
        print(f"   查询按钮存在: {button.count() > 0}")
        
        if button.count() == 0:
            button = page.locator('button:has-text("查询")').first
            print(f"   备用按钮存在: {button.count() > 0}")
        
        # 点击查询
        print("\n4️⃣ 点击查询按钮...")
        if button.count() > 0:
            button.click()
        else:
            input_box.press('Enter')
            print("   使用 Enter 键提交")
        
        # 等待结果
        print("\n5️⃣ 等待结果加载...")
        time.sleep(3)
        
        # 检查页面变化
        new_text = page.locator('body').inner_text()
        print(f"   查询后文本长度: {len(new_text)} 字符")
        
        # 检查是否有验证码
        if '验证码' in new_text or 'verify' in new_text.lower():
            print("   ⚠️ 检测到验证码！")
        
        # 检查是否有结果
        if '段' in new_text and name in new_text:
            print("   ✅ 找到结果数据！")
        elif '暂无数据' in new_text or '未找到' in new_text:
            print("   ⚠️ 暂无数据")
        else:
            print("   ❌ 未找到结果数据")
        
        # 打印关键文本
        print("\n6️⃣ 页面关键内容:")
        lines = [l.strip() for l in new_text.split('\n') if l.strip()][:30]
        for line in lines:
            print(f"   | {line}")
        
        browser.close()

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "朱玲钰"
    debug_query(name)

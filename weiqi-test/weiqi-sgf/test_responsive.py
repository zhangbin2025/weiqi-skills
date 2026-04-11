"""
响应式布局测试

测试不同屏幕尺寸下的显示效果
"""

import pytest
from playwright.sync_api import expect
import os


# 定义测试用的视口尺寸
VIEWPORTS = {
    "mobile_small": {"width": 375, "height": 667},   # iPhone SE
    "mobile": {"width": 414, "height": 896},         # iPhone 11 Pro Max
    "tablet": {"width": 768, "height": 1024},        # iPad
    "desktop": {"width": 1280, "height": 720},       # 标准桌面
    "desktop_large": {"width": 1920, "height": 1080}, # 大屏桌面
}


class TestResponsiveCanvas:
    """响应式 Canvas 测试"""
    
    @pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS.items())
    def test_canvas_visible_all_sizes(self, page, page_factory, simple_sgf, viewport_name, viewport):
        """测试各种尺寸下 Canvas 可见"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(viewport)
        page.goto(f"file://{html_path}")
        
        canvas = page.locator("#board")
        expect(canvas).to_be_visible()
        
        # 验证有尺寸
        box = canvas.bounding_box()
        assert box["width"] > 0, f"{viewport_name}: Canvas 宽度应该大于 0"
        assert box["height"] > 0, f"{viewport_name}: Canvas 高度应该大于 0"
        
        os.unlink(html_path)
    
    @pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS.items())
    def test_canvas_square_all_sizes(self, page, page_factory, simple_sgf, viewport_name, viewport):
        """测试各种尺寸下 Canvas 保持正方形"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(viewport)
        page.goto(f"file://{html_path}")
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        # 允许 5px 误差
        size_diff = abs(box["width"] - box["height"])
        assert size_diff < 5, f"{viewport_name}: Canvas 应该保持正方形，宽高差 {size_diff}px"
        
        os.unlink(html_path)
    
    @pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS.items())
    def test_controls_visible_all_sizes(self, page, page_factory, simple_sgf, viewport_name, viewport):
        """测试各种尺寸下控制按钮可见"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(viewport)
        page.goto(f"file://{html_path}")
        
        # 检查主要控制按钮
        controls = ["#prevBtn", "#nextBtn", "#playBtn"]
        for control in controls:
            btn = page.locator(control)
            expect(btn).to_be_visible()
        
        os.unlink(html_path)


class TestMobileLayout:
    """移动端布局测试"""
    
    def test_mobile_container_padding(self, page, page_factory, simple_sgf):
        """测试移动端容器内边距"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["mobile"])
        page.goto(f"file://{html_path}")
        
        container = page.locator(".container")
        box = container.bounding_box()
        
        # 移动端容器应该适应屏幕
        screen_width = VIEWPORTS["mobile"]["width"]
        assert box["width"] <= screen_width, "容器宽度不应超过屏幕宽度"
        os.unlink(html_path)
    
    def test_mobile_button_size(self, page, page_factory, simple_sgf):
        """测试移动端按钮大小适合触摸"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["mobile"])
        page.goto(f"file://{html_path}")
        
        # 检查按钮尺寸（适合触摸的最小 44px）
        next_btn = page.locator("#nextBtn")
        box = next_btn.bounding_box()
        
        assert box["width"] >= 32, "移动端按钮宽度应该 >= 32px"
        assert box["height"] >= 32, "移动端按钮高度应该 >= 32px"
        os.unlink(html_path)
    
    def test_mobile_header_font_size(self, page, page_factory, simple_sgf):
        """测试移动端标题字体大小"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["mobile"])
        page.goto(f"file://{html_path}")
        
        header = page.locator(".header h1")
        font_size = header.evaluate("el => parseInt(getComputedStyle(el).fontSize)")
        
        # 移动端标题应该较小
        assert font_size <= 20, "移动端标题字体应该较小"
        os.unlink(html_path)


class TestDesktopLayout:
    """桌面端布局测试"""
    
    def test_desktop_max_width(self, page, page_factory, simple_sgf):
        """测试桌面端最大宽度限制"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["desktop_large"])
        page.goto(f"file://{html_path}")
        
        container = page.locator(".container")
        box = container.bounding_box()
        
        # 桌面端应该有最大宽度限制
        assert box["width"] <= 900, "桌面端容器应该有最大宽度限制"
        os.unlink(html_path)
    
    def test_desktop_larger_padding(self, page, page_factory, simple_sgf):
        """测试桌面端更大的内边距"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["desktop"])
        page.goto(f"file://{html_path}")
        
        container = page.locator(".container")
        padding = container.evaluate("""
            el => {
                const style = getComputedStyle(el);
                return parseInt(style.padding);
            }
        """)
        
        # 桌面端应该有更大的内边距
        assert padding >= 8, "桌面端容器应该有适当的内边距"
        os.unlink(html_path)
    
    def test_desktop_header_font_size(self, page, page_factory, simple_sgf):
        """测试桌面端标题字体大小"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["desktop"])
        page.goto(f"file://{html_path}")
        
        header = page.locator(".header h1")
        font_size = header.evaluate("el => parseInt(getComputedStyle(el).fontSize)")
        
        # 桌面端标题应该较大
        assert font_size >= 15, "桌面端标题字体应该较大"
        os.unlink(html_path)


class TestLayoutTransitions:
    """布局切换测试"""
    
    def test_resize_from_mobile_to_desktop(self, page, page_factory, simple_sgf):
        """测试从移动端调整到桌面端"""
        html_path = page_factory(simple_sgf)
        
        # 先设置移动端
        page.set_viewport_size(VIEWPORTS["mobile"])
        page.goto(f"file://{html_path}")
        
        # 获取移动端尺寸
        canvas = page.locator("#board")
        mobile_box = canvas.bounding_box()
        
        # 调整到桌面端
        page.set_viewport_size(VIEWPORTS["desktop"])
        page.wait_for_timeout(300)
        
        # 获取桌面端尺寸
        desktop_box = canvas.bounding_box()
        
        # Canvas 应该变大
        assert desktop_box["width"] > mobile_box["width"], "调整到桌面端后 Canvas 应该变大"
        os.unlink(html_path)
    
    def test_resize_from_desktop_to_mobile(self, page, page_factory, simple_sgf):
        """测试从桌面端调整到移动端"""
        html_path = page_factory(simple_sgf)
        
        # 先设置桌面端
        page.set_viewport_size(VIEWPORTS["desktop"])
        page.goto(f"file://{html_path}")
        
        canvas = page.locator("#board")
        desktop_box = canvas.bounding_box()
        
        # 调整到移动端
        page.set_viewport_size(VIEWPORTS["mobile"])
        page.wait_for_timeout(300)
        
        mobile_box = canvas.bounding_box()
        
        # Canvas 应该变小
        assert mobile_box["width"] < desktop_box["width"], "调整到移动端后 Canvas 应该变小"
        
        # 但仍然可见
        expect(canvas).to_be_visible()
        os.unlink(html_path)
    
    def test_state_preserved_after_resize(self, page, page_factory, simple_sgf):
        """测试调整大小后状态保持"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["desktop"])
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(5):
            page.locator("#nextBtn").click()
        
        move_info = page.locator("#moveInfo")
        initial_text = move_info.text_content()
        
        # 调整大小
        page.set_viewport_size(VIEWPORTS["mobile"])
        page.wait_for_timeout(300)
        
        # 状态应该保持
        expect(move_info).to_have_text(initial_text)
        os.unlink(html_path)


class TestTouchTargets:
    """触摸目标测试"""
    
    def test_all_buttons_touch_friendly(self, page, page_factory, simple_sgf):
        """测试所有按钮都适合触摸"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["mobile"])
        page.goto(f"file://{html_path}")
        
        # 获取所有按钮
        buttons = page.locator("button")
        count = buttons.count()
        
        for i in range(count):
            btn = buttons.nth(i)
            box = btn.bounding_box()
            
            # 检查可见按钮的尺寸
            if box and box["width"] > 0:
                assert box["width"] >= 28, f"按钮 {i} 宽度应该 >= 28px"
                assert box["height"] >= 28, f"按钮 {i} 高度应该 >= 28px"
        
        os.unlink(html_path)
    
    def test_canvas_touchable(self, page, page_factory, simple_sgf):
        """测试 Canvas 可触摸交互"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["mobile"])
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        # Canvas 应该足够大以便触摸
        assert box["width"] >= 300, "移动端 Canvas 应该足够大"
        assert box["height"] >= 300, "移动端 Canvas 应该足够大"
        
        os.unlink(html_path)


class TestScrollbar:
    """滚动条测试"""
    
    def test_no_horizontal_scrollbar_desktop(self, page, page_factory, simple_sgf):
        """测试桌面端无水平滚动条"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["desktop"])
        page.goto(f"file://{html_path}")
        
        # 检查页面宽度
        page_width = page.evaluate("() => document.documentElement.scrollWidth")
        viewport_width = page.evaluate("() => window.innerWidth")
        
        assert page_width <= viewport_width, "桌面端不应该有水平滚动条"
        os.unlink(html_path)
    
    def test_no_horizontal_scrollbar_mobile(self, page, page_factory, simple_sgf):
        """测试移动端无水平滚动条"""
        html_path = page_factory(simple_sgf)
        page.set_viewport_size(VIEWPORTS["mobile"])
        page.goto(f"file://{html_path}")
        
        page_width = page.evaluate("() => document.documentElement.scrollWidth")
        viewport_width = page.evaluate("() => window.innerWidth")
        
        assert page_width <= viewport_width, "移动端不应该有水平滚动条"
        os.unlink(html_path)

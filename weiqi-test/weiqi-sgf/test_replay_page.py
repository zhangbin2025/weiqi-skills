"""
页面级 E2E 测试 - 验证页面加载和基础功能
"""

import pytest
from playwright.sync_api import expect
import os


class TestPageLoad:
    """页面加载测试"""
    
    def test_page_title(self, page, page_factory, simple_sgf):
        """测试页面标题正确显示"""
        html_path = page_factory(simple_sgf, "LG杯决赛")
        page.goto(f"file://{html_path}")
        
        expect(page).to_have_title("LG杯决赛")
        os.unlink(html_path)
    
    def test_game_info_display(self, page, page_factory, simple_sgf):
        """测试棋局信息显示"""
        html_path = page_factory(simple_sgf, "测试对局")
        page.goto(f"file://{html_path}")
        
        # 检查玩家名称
        black_name = page.locator("#blackName")
        white_name = page.locator("#whiteName")
        
        expect(black_name).to_contain_text("黑棋")
        expect(white_name).to_contain_text("白棋")
        os.unlink(html_path)
    
    def test_canvas_exists(self, page, page_factory, simple_sgf):
        """测试 Canvas 元素存在并可访问"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        canvas = page.locator("#board")
        expect(canvas).to_be_visible()
        
        # 验证 Canvas 有尺寸
        box = canvas.bounding_box()
        assert box["width"] > 0
        assert box["height"] > 0
        os.unlink(html_path)
    
    def test_initial_state(self, page, page_factory, simple_sgf):
        """测试初始状态显示"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 初始状态显示"第 0 手"
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 0 手")
        
        # 控制按钮状态
        prev_btn = page.locator("#prevBtn")
        expect(prev_btn).to_be_disabled()
        os.unlink(html_path)


class TestBasicNavigation:
    """基础导航测试"""
    
    def test_next_move(self, page, page_factory, simple_sgf):
        """测试下一手按钮"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 点击下一手
        page.locator("#nextBtn").click()
        
        # 验证状态更新
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 1 手")
        os.unlink(html_path)
    
    def test_prev_move(self, page, page_factory, simple_sgf):
        """测试上一手按钮"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 先前进两手
        page.locator("#nextBtn").click()
        page.locator("#nextBtn").click()
        
        # 再后退一手
        page.locator("#prevBtn").click()
        
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 1 手")
        os.unlink(html_path)
    
    def test_slider_navigation(self, page, page_factory, simple_sgf):
        """测试滑条导航"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 获取滑条
        slider = page.locator("#moveSlider")
        
        # 拖动滑条到第 4 手
        slider.fill("4")
        
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 4 手")
        os.unlink(html_path)
    
    def test_keyboard_shortcuts(self, page, page_factory, simple_sgf):
        """测试键盘快捷键"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 按右箭头前进
        page.keyboard.press("ArrowRight")
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 1 手")
        
        # 按左箭头后退
        page.keyboard.press("ArrowLeft")
        expect(move_info).to_contain_text("第 0 手")
        os.unlink(html_path)


class TestAutoPlay:
    """自动播放功能测试"""
    
    def test_play_pause_toggle(self, page, page_factory, simple_sgf):
        """测试播放/暂停切换"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        play_btn = page.locator("#playBtn")
        
        # 初始状态是"播"
        expect(play_btn).to_contain_text("播")
        
        # 点击开始播放
        play_btn.click()
        expect(play_btn).to_contain_text("停")
        
        # 等待自动播放几步
        page.wait_for_timeout(1000)
        
        # 点击暂停
        play_btn.click()
        expect(play_btn).to_contain_text("播")
        os.unlink(html_path)
    
    def test_auto_play_advances(self, page, page_factory, simple_sgf):
        """测试自动播放确实会前进"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 开始播放
        page.locator("#playBtn").click()
        
        # 等待播放
        page.wait_for_timeout(1500)
        
        # 停止播放
        page.locator("#playBtn").click()
        
        # 验证已经前进（至少第 1 手）
        move_info = page.locator("#moveInfo")
        text = move_info.text_content()
        hand_num = int(text.replace("第 ", "").replace(" 手", ""))
        assert hand_num >= 1, f"自动播放后应该至少前进到第 1 手，实际在第 {hand_num} 手"
        os.unlink(html_path)


class TestSoundToggle:
    """音效开关测试"""
    
    def test_sound_toggle(self, page, page_factory, simple_sgf):
        """测试音效开关按钮"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        sound_btn = page.locator("#soundToggleBtn")
        
        # 初始状态是开启（🔊）
        expect(sound_btn).to_contain_text("🔊")
        
        # 点击关闭
        sound_btn.click()
        expect(sound_btn).to_contain_text("🔇")
        
        # 点击开启
        sound_btn.click()
        expect(sound_btn).to_contain_text("🔊")
        os.unlink(html_path)


class TestMoveNumbers:
    """手数显示测试"""
    
    def test_toggle_move_numbers(self, page, page_factory, simple_sgf):
        """测试手数显示切换"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 先前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        canvas = page.locator("#board")
        num_btn = page.locator("#numToggleBtn")
        
        # 获取第一手棋子的像素（未开启手数显示时）
        before_click = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                const margin = canvas.width * 0.02 + canvas.width * 0.018;
                const gridSize = (canvas.width - 2 * margin) / 18;
                const stoneX = Math.floor(margin + 15 * gridSize);
                const stoneY = Math.floor(margin + 3 * gridSize);
                const pixel = ctx.getImageData(stoneX, stoneY, 1, 1).data;
                return { r: pixel[0], g: pixel[1], b: pixel[2] };
            }
        """)
        
        # 点击显示手数
        num_btn.click()
        page.wait_for_timeout(100)
        
        # 获取开启手数显示后的像素
        after_click = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                const margin = canvas.width * 0.02 + canvas.width * 0.018;
                const gridSize = (canvas.width - 2 * margin) / 18;
                const stoneX = Math.floor(margin + 15 * gridSize);
                const stoneY = Math.floor(margin + 3 * gridSize);
                const pixel = ctx.getImageData(stoneX, stoneY, 1, 1).data;
                return { r: pixel[0], g: pixel[1], b: pixel[2] };
            }
        """)
        
        # 开启手数后，黑棋中心应该显示白色数字（RGB 值应该变高）
        # 或者检测按钮是否可点击（未被禁用）
        expect(num_btn).to_be_enabled()
        
        # 通过检查像素变化来验证手数显示功能
        # 黑棋上显示白色数字，中心像素应该从深色变为浅色
        color_changed = (before_click['r'] < 100 and after_click['r'] > 150) or \
                       (abs(before_click['r'] - after_click['r']) > 50)
        assert color_changed, f"开启手数显示后棋子中心像素应该有变化: 之前 RGB({before_click['r']},{before_click['g']},{before_click['b']}), 之后 RGB({after_click['r']},{after_click['g']},{after_click['b']})"
        os.unlink(html_path)


class TestSGFDownload:
    """SGF 下载功能测试"""
    
    def test_download_button_exists(self, page, page_factory, simple_sgf):
        """测试下载按钮存在"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 找到下载按钮（通过 title 或包含 💾 的按钮）
        download_btn = page.locator("button[title='下载SGF']")
        expect(download_btn).to_be_visible()
        os.unlink(html_path)
    
    def test_download_triggers(self, page, page_factory, simple_sgf):
        """测试下载功能可触发"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 设置下载监听
        with page.expect_download() as download_info:
            page.locator("button[title='下载SGF']").click()
        
        download = download_info.value
        assert download.suggested_filename.endswith('.sgf')
        os.unlink(html_path)

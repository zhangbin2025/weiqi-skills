"""
导航控制综合测试

测试滑条、键盘快捷键、播放控制等导航功能
"""

import pytest
from playwright.sync_api import expect
import os


class TestSliderNavigation:
    """滑条导航测试"""
    
    def test_slider_initial_value(self, page, page_factory, simple_sgf):
        """测试滑条初始值为 0"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        slider = page.locator("#moveSlider")
        expect(slider).to_have_value("0")
        os.unlink(html_path)
    
    def test_slider_updates_on_next(self, page, page_factory, simple_sgf):
        """测试前进时滑条更新"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        page.locator("#nextBtn").click()
        
        slider = page.locator("#moveSlider")
        expect(slider).to_have_value("1")
        os.unlink(html_path)
    
    def test_slider_updates_on_prev(self, page, page_factory, simple_sgf):
        """测试后退时滑条更新"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进3手
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        # 后退1手
        page.locator("#prevBtn").click()
        
        slider = page.locator("#moveSlider")
        expect(slider).to_have_value("2")
        os.unlink(html_path)
    
    def test_slider_max_value(self, page, page_factory, simple_sgf):
        """测试滑条最大值"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 获取滑条最大值属性
        slider = page.locator("#moveSlider")
        max_value = slider.get_attribute("max")
        
        # 简单棋谱有 8 手
        assert int(max_value) >= 8, f"滑条最大值应该 >= 8，实际是 {max_value}"
        os.unlink(html_path)
    
    def test_slider_drag_to_position(self, page, page_factory, simple_sgf):
        """测试拖动滑条到指定位置"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        slider = page.locator("#moveSlider")
        
        # 设置滑条值
        slider.fill("5")
        
        # 验证状态更新
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 5 手")
        os.unlink(html_path)
    
    def test_slider_to_zero(self, page, page_factory, simple_sgf):
        """测试滑条回到 0"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(5):
            page.locator("#nextBtn").click()
        
        # 滑条回到 0
        slider = page.locator("#moveSlider")
        slider.fill("0")
        
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 0 手")
        os.unlink(html_path)


class TestKeyboardNavigation:
    """键盘导航测试"""
    
    def test_arrow_right_advances(self, page, page_factory, simple_sgf):
        """测试右箭头前进"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        page.keyboard.press("ArrowRight")
        
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 1 手")
        os.unlink(html_path)
    
    def test_arrow_left_goes_back(self, page, page_factory, simple_sgf):
        """测试左箭头后退"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 先前进
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowRight")
        
        # 再后退
        page.keyboard.press("ArrowLeft")
        
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 1 手")
        os.unlink(html_path)
    
    def test_space_toggles_play(self, page, page_factory, simple_sgf):
        """测试空格键播放/暂停"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        play_btn = page.locator("#playBtn")
        
        # 初始状态
        expect(play_btn).to_contain_text("播")
        
        # 按空格开始播放
        page.keyboard.press(" ")
        expect(play_btn).to_contain_text("停")
        
        # 等待一下
        page.wait_for_timeout(500)
        
        # 再按空格暂停
        page.keyboard.press(" ")
        expect(play_btn).to_contain_text("播")
        os.unlink(html_path)
    
    def test_multiple_arrow_keys(self, page, page_factory, simple_sgf):
        """测试连续按键"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 快速按多次右箭头
        for _ in range(5):
            page.keyboard.press("ArrowRight")
        
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 5 手")
        os.unlink(html_path)
    
    def test_arrow_at_boundaries(self, page, page_factory, simple_sgf):
        """测试边界按键"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 在 0 手时按左箭头（应该无效果）
        page.keyboard.press("ArrowLeft")
        
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 0 手")
        
        # 前进到最后一手之后再按右箭头
        slider = page.locator("#moveSlider")
        max_val = int(slider.get_attribute("max"))
        
        for _ in range(max_val + 5):  # 多按几次
            page.keyboard.press("ArrowRight")
        
        # 应该停在最大值
        expect(move_info).to_contain_text(f"第 {max_val} 手")
        os.unlink(html_path)


class TestPlayControl:
    """播放控制测试"""
    
    def test_play_button_text_toggle(self, page, page_factory, simple_sgf):
        """测试播放按钮文本切换"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        play_btn = page.locator("#playBtn")
        
        # 点击开始
        play_btn.click()
        expect(play_btn).to_contain_text("停")
        
        # 点击暂停
        play_btn.click()
        expect(play_btn).to_contain_text("播")
        os.unlink(html_path)
    
    def test_auto_play_stops_at_end(self, page, page_factory, simple_sgf):
        """测试自动播放到末尾停止"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 开始播放
        page.locator("#playBtn").click()
        
        # 等待足够长时间
        page.wait_for_timeout(10000)  # 10秒应该足够播完
        
        # 应该自动停止
        play_btn = page.locator("#playBtn")
        expect(play_btn).to_contain_text("播")
        os.unlink(html_path)
    
    def test_manual_stop_resets_text(self, page, page_factory, simple_sgf):
        """测试手动停止重置按钮文本"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        play_btn = page.locator("#playBtn")
        
        # 开始播放
        play_btn.click()
        page.wait_for_timeout(500)
        
        # 手动停止
        play_btn.click()
        expect(play_btn).to_contain_text("播")
        os.unlink(html_path)
    
    def test_play_disabled_when_no_moves(self, page, page_factory, empty_sgf):
        """测试空棋谱时播放按钮行为"""
        html_path = page_factory(empty_sgf)
        page.goto(f"file://{html_path}")
        
        # 空棋谱应该无法播放（没有后续着法）
        next_btn = page.locator("#nextBtn")
        expect(next_btn).to_be_disabled()
        os.unlink(html_path)


class TestButtonStates:
    """按钮状态测试"""
    
    def test_prev_disabled_at_start(self, page, page_factory, simple_sgf):
        """测试初始时后退按钮禁用"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        prev_btn = page.locator("#prevBtn")
        expect(prev_btn).to_be_disabled()
        os.unlink(html_path)
    
    def test_prev_enabled_after_move(self, page, page_factory, simple_sgf):
        """测试前进后后退按钮启用"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        page.locator("#nextBtn").click()
        
        prev_btn = page.locator("#prevBtn")
        expect(prev_btn).not_to_be_disabled()
        os.unlink(html_path)
    
    def test_next_disabled_at_end(self, page, page_factory, simple_sgf):
        """测试到末尾时前进按钮禁用"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到最后一手
        slider = page.locator("#moveSlider")
        max_val = int(slider.get_attribute("max"))
        slider.fill(str(max_val))
        
        next_btn = page.locator("#nextBtn")
        expect(next_btn).to_be_disabled()
        os.unlink(html_path)
    
    def test_buttons_enabled_mid_game(self, page, page_factory, simple_sgf):
        """测试中盘时按钮都启用"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到中间
        for _ in range(4):
            page.locator("#nextBtn").click()
        
        prev_btn = page.locator("#prevBtn")
        next_btn = page.locator("#nextBtn")
        
        expect(prev_btn).not_to_be_disabled()
        expect(next_btn).not_to_be_disabled()
        os.unlink(html_path)


class TestQuickActions:
    """快捷操作测试"""
    
    def test_jump_to_start(self, page, page_factory, simple_sgf):
        """测试快速回到开头"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到后面
        for _ in range(5):
            page.locator("#nextBtn").click()
        
        # 滑条回到 0
        page.locator("#moveSlider").fill("0")
        
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 0 手")
        
        # 后退按钮应该禁用
        expect(page.locator("#prevBtn")).to_be_disabled()
        os.unlink(html_path)
    
    def test_jump_to_end(self, page, page_factory, simple_sgf):
        """测试快速跳转到末尾"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        slider = page.locator("#moveSlider")
        max_val = slider.get_attribute("max")
        
        # 滑条到最大值
        slider.fill(max_val)
        
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text(f"第 {max_val} 手")
        
        # 前进按钮应该禁用
        expect(page.locator("#nextBtn")).to_be_disabled()
        os.unlink(html_path)

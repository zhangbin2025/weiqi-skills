"""
变化分支导航测试

测试多级变化图的进入、退出、切换等功能
"""

import pytest
import re
from playwright.sync_api import expect
import os


class TestVariationPanel:
    """变化图面板测试"""
    
    def test_variation_panel_hidden_when_no_variations(self, page, page_factory, simple_sgf):
        """测试无变化图时面板隐藏"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(100)
        
        panel = page.locator("#variationPanel")
        expect(panel).not_to_have_class(re.compile(r"visible"))
        os.unlink(html_path)
    
    def test_variation_panel_shows_when_variations_exist(self, page, page_factory, variations_sgf):
        """测试有变化图时面板显示"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手 (B[pd])，此时会显示变化分支
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 检查变化面板显示
        panel = page.locator("#variationPanel")
        expect(panel).to_have_class(re.compile(r"visible"))
        os.unlink(html_path)
    
    def test_variation_buttons_displayed(self, page, page_factory, variations_sgf):
        """测试变化按钮正确显示"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        variation_list = page.locator("#variationList")
        buttons = variation_list.locator("button")
        
        # 应该有2个变化分支按钮（跳过主分支：小雪崩 + 超高目）
        expect(buttons).to_have_count(2)
        os.unlink(html_path)
    
    def test_variation_button_labels(self, page, page_factory, variations_sgf):
        """测试变化按钮标签正确"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        variation_list = page.locator("#variationList")
        buttons = variation_list.locator("button")
        
        # 获取按钮文本
        texts = buttons.all_text_contents()
        
        # 应该包含定义的标签
        assert any("小雪崩" in text for text in texts), f"应该有'小雪崩'变化，实际: {texts}"
        assert any("超高目" in text for text in texts), f"应该有'超高目'变化，实际: {texts}"
        os.unlink(html_path)
    
    def test_variation_win_rate_display(self, page, page_factory, variations_sgf):
        """测试变化按钮显示胜率或名称"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        variation_list = page.locator("#variationList")
        buttons = variation_list.locator("button")
        
        texts = buttons.all_text_contents()
        
        # 按钮文本应该包含胜率信息或名称（N属性优先）
        has_content = any("%" in text or "雪崩" in text or "高目" in text for text in texts)
        assert has_content, f"变化按钮应该显示胜率或名称，实际: {texts}"
        os.unlink(html_path)


class TestEnterVariation:
    """进入变化分支测试"""
    
    def test_enter_variation_changes_display(self, page, page_factory, variations_sgf):
        """测试进入变化分支后显示变化"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 点击第一个变化
        variation_list = page.locator("#variationList")
        buttons = variation_list.locator("button")
        buttons.first.click()
        page.wait_for_timeout(100)
        
        # 验证进入变化分支（手数应该变化）
        move_info = page.locator("#moveInfo")
        expect(move_info).not_to_contain_text("第 0 手")
        os.unlink(html_path)
    
    def test_back_button_appears_in_variation(self, page, page_factory, variations_sgf):
        """测试进入变化后显示返回按钮"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        
        # 返回按钮应该显示
        back_btn = page.locator("#backToParentBtn")
        expect(back_btn).to_be_visible()
        os.unlink(html_path)
    
    def test_slider_hidden_in_variation(self, page, page_factory, variations_sgf):
        """测试在变化分支中滑条隐藏"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        
        # 滑条应该隐藏
        slider = page.locator("#moveSlider")
        expect(slider).not_to_be_visible()
        os.unlink(html_path)
    
    def test_number_toggle_hidden_in_variation(self, page, page_factory, variations_sgf):
        """测试在变化分支中手数按钮隐藏"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        
        # 手数按钮应该隐藏
        num_btn = page.locator("#numToggleBtn")
        expect(num_btn).not_to_be_visible()
        os.unlink(html_path)
    
    def test_sound_toggle_hidden_in_variation(self, page, page_factory, variations_sgf):
        """测试在变化分支中音效按钮隐藏"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        
        # 音效按钮应该隐藏
        sound_btn = page.locator("#soundToggleBtn")
        expect(sound_btn).not_to_be_visible()
        os.unlink(html_path)


class TestBackToParent:
    """返回上级测试"""
    
    def test_back_button_returns_to_main(self, page, page_factory, variations_sgf):
        """测试返回按钮能回到主分支"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        page.wait_for_timeout(100)
        
        # 点击返回
        page.locator("#backToParentBtn").click()
        page.wait_for_timeout(100)
        
        # 应该回到主分支
        back_btn = page.locator("#backToParentBtn")
        expect(back_btn).not_to_be_visible()
        
        # 滑条应该重新显示
        slider = page.locator("#moveSlider")
        expect(slider).to_be_visible()
        os.unlink(html_path)
    
    def test_back_restores_controls(self, page, page_factory, variations_sgf):
        """测试返回后控制按钮恢复"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        page.wait_for_timeout(100)
        
        # 返回
        page.locator("#backToParentBtn").click()
        page.wait_for_timeout(100)
        
        # 手数和音效按钮应该恢复
        num_btn = page.locator("#numToggleBtn")
        sound_btn = page.locator("#soundToggleBtn")
        expect(num_btn).to_be_visible()
        expect(sound_btn).to_be_visible()
        os.unlink(html_path)


class TestVariationNavigation:
    """变化分支内导航测试"""
    
    def test_next_in_variation(self, page, page_factory, variations_sgf):
        """测试在变化分支中前进"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        page.wait_for_timeout(100)
        
        # 在变化分支中前进
        page.locator("#nextBtn").click()
        
        move_info = page.locator("#moveInfo")
        # 变化分支内显示的手数可能是相对的，检查不是第0手即可
        expect(move_info).not_to_contain_text("第 0 手")
        os.unlink(html_path)
    
    def test_prev_in_variation(self, page, page_factory, variations_sgf):
        """测试在变化分支中后退"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        page.wait_for_timeout(100)
        
        # 前进两步
        page.locator("#nextBtn").click()
        page.locator("#nextBtn").click()
        
        # 后退一步
        page.locator("#prevBtn").click()
        
        move_info = page.locator("#moveInfo")
        # 变化分支内后退后应该仍然显示手数（不是第0手）
        expect(move_info).not_to_contain_text("第 0 手")
        os.unlink(html_path)


class TestNestedVariations:
    """嵌套变化测试"""
    
    def test_deep_variation_navigation(self, page, page_factory, variations_sgf):
        """测试深层变化导航"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入第一层变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        page.wait_for_timeout(100)
        
        # 前进几步
        for _ in range(2):
            page.locator("#nextBtn").click()
        
        # 此时应该还在变化分支中
        back_btn = page.locator("#backToParentBtn")
        expect(back_btn).to_be_visible()
        os.unlink(html_path)


class TestVariationStatePersistence:
    """变化状态持久化测试"""
    
    def test_variation_state_after_resize(self, page, page_factory, variations_sgf):
        """测试调整窗口大小后变化状态保持"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手显示变化
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        # 进入变化
        variation_list = page.locator("#variationList")
        variation_list.locator("button").first.click()
        page.wait_for_timeout(100)
        
        # 前进几步
        page.locator("#nextBtn").click()
        
        # 记录当前手数
        move_info = page.locator("#moveInfo")
        initial_text = move_info.text_content()
        
        # 调整窗口大小
        page.set_viewport_size({"width": 800, "height": 600})
        page.wait_for_timeout(300)
        
        # 手数应该保持不变
        expect(move_info).to_have_text(initial_text)
        os.unlink(html_path)

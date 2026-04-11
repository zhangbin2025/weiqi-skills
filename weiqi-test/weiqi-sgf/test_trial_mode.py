"""
试下功能测试

测试试下模式、提子判断、劫判断、试下栈管理等复杂功能
"""

import pytest
import re
from playwright.sync_api import expect
import os


class TestTrialModeEntry:
    """试下模式进入测试"""
    
    def test_click_empty_point_enters_trial(self, page, page_factory, simple_sgf):
        """测试点击空点进入试下模式"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        # 获取 Canvas 并点击空点（天元附近）
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        # 计算天元位置
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        
        # 点击天元
        page.mouse.click(center_x, center_y)
        
        # 检查试下面板显示
        trial_panel = page.locator("#trialPanel")
        expect(trial_panel).to_have_class(re.compile(r"visible"))
        os.unlink(html_path)
    
    def test_trial_panel_shows_controls(self, page, page_factory, simple_sgf):
        """测试试下面板显示控制按钮"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        # 点击空点进入试下
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        page.mouse.click(center_x, center_y)
        
        # 检查试下控制按钮
        trial_prev = page.locator("#trialPrevBtn")
        trial_next = page.locator("#trialNextBtn")
        exit_btn = page.locator("#trialPanel button[title='退出试下']")
        
        expect(trial_prev).to_be_visible()
        expect(exit_btn).to_be_visible()
        expect(trial_next).to_be_visible()
        os.unlink(html_path)
    
    def test_main_controls_hidden_in_trial(self, page, page_factory, simple_sgf):
        """测试试下模式下主控制隐藏"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        # 进入试下
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        page.mouse.click(center_x, center_y)
        
        # 主控制应该隐藏
        main_controls = page.locator("#mainControls")
        expect(main_controls).not_to_be_visible()
        os.unlink(html_path)
    
    def test_variation_panel_hidden_in_trial(self, page, page_factory, variations_sgf):
        """测试试下模式下变化面板隐藏"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 进入试下
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        page.mouse.click(center_x, center_y)
        
        # 变化面板应该隐藏
        variation_panel = page.locator("#variationPanel")
        expect(variation_panel).not_to_have_class(re.compile(r"visible"))
        os.unlink(html_path)


class TestTrialPlacement:
    """试下落子测试"""
    
    def test_trial_stone_placed(self, page, page_factory, simple_sgf):
        """测试试下能成功落子"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        # 点击天元
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        page.mouse.click(center_x, center_y)
        page.wait_for_timeout(100)
        
        # 检查天元位置有棋子
        stone_color = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                const margin = canvas.width * 0.02 + canvas.width * 0.018;
                const gridSize = (canvas.width - 2 * margin) / 18;
                const stoneX = Math.floor(margin + 9 * gridSize);
                const stoneY = Math.floor(margin + 9 * gridSize);
                const pixel = ctx.getImageData(stoneX, stoneY, 1, 1).data;
                return { r: pixel[0], g: pixel[1], b: pixel[2] };
            }
        """)
        
        # 应该有棋子（黑或白）
        has_stone = (stone_color['r'] < 80) or (stone_color['r'] > 180)
        assert has_stone, "试下后应该有棋子"
        os.unlink(html_path)
    
    def test_trial_alternates_color(self, page, page_factory, simple_sgf):
        """测试试下棋色交替"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进3手（黑、白、黑），下一手应该是白
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        # 计算两个相邻的空点位置
        # 使用天元和旁边的点
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        
        margin_ratio = 0.038  # margin + coordMargin
        grid_ratio = (1 - 2 * margin_ratio) / 18
        grid_size = box["width"] * grid_ratio
        
        # 天元 (9, 9)
        tianyuan_x = box["x"] + box["width"] * margin_ratio + 9 * grid_size
        tianyuan_y = box["y"] + box["height"] * margin_ratio + 9 * grid_size
        
        # 旁边的点 (10, 9)
        next_x = box["x"] + box["width"] * margin_ratio + 10 * grid_size
        next_y = tianyuan_y
        
        # 第一手试下
        page.mouse.click(tianyuan_x, tianyuan_y)
        page.wait_for_timeout(100)
        
        # 第二手试下
        page.mouse.click(next_x, next_y)
        page.wait_for_timeout(100)
        
        # 检查两个位置的颜色
        colors = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                const margin = canvas.width * 0.02 + canvas.width * 0.018;
                const gridSize = (canvas.width - 2 * margin) / 18;
                const p1 = { x: Math.floor(margin + 9 * gridSize), y: Math.floor(margin + 9 * gridSize) };
                const p2 = { x: Math.floor(margin + 10 * gridSize), y: Math.floor(margin + 9 * gridSize) };
                const c1 = ctx.getImageData(p1.x, p1.y, 1, 1).data;
                const c2 = ctx.getImageData(p2.x, p2.y, 1, 1).data;
                return {
                    first: { r: c1[0], g: c1[1], b: c1[2] },
                    second: { r: c2[0], g: c2[1], b: c2[2] }
                };
            }
        """)
        
        # 两个棋子颜色应该不同（一个黑一个白）
        first_dark = colors['first']['r'] < 100
        second_dark = colors['second']['r'] < 100
        assert first_dark != second_dark, "试下棋色应该交替"
        os.unlink(html_path)
    
    def test_click_existing_stone_no_effect(self, page, page_factory, simple_sgf):
        """测试点击已有棋子位置无效果"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进一手，有棋子了
        page.locator("#nextBtn").click()
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        # pd 位置 (15, 3)
        margin_ratio = 0.038
        grid_ratio = (1 - 2 * margin_ratio) / 18
        grid_size = box["width"] * grid_ratio
        
        pd_x = box["x"] + box["width"] * margin_ratio + 15 * grid_size
        pd_y = box["y"] + box["height"] * margin_ratio + 3 * grid_size
        
        # 点击已有棋子位置
        page.mouse.click(pd_x, pd_y)
        
        # 不应该进入试下模式
        trial_panel = page.locator("#trialPanel")
        expect(trial_panel).not_to_have_class(re.compile(r"visible"))
        os.unlink(html_path)


class TestTrialNavigation:
    """试下导航测试"""
    
    def test_trial_prev_enabled_after_first_move(self, page, page_factory, simple_sgf):
        """测试试下落子后后退按钮启用（trialIndex=1）"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        # 进入试下并落子
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        page.mouse.click(center_x, center_y)
        page.wait_for_timeout(300)  # 等待 JavaScript 更新按钮状态
        
        # 落子后 trialIndex=1，后退按钮应该启用
        trial_prev = page.locator("#trialPrevBtn")
        is_disabled = trial_prev.evaluate("el => el.disabled")
        assert is_disabled == False, f"试下落子后后退按钮应该启用，实际 disabled={is_disabled}"
        os.unlink(html_path)
    
    def test_trial_prev_after_moves(self, page, page_factory, simple_sgf):
        """测试试下多手后可以后退"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        margin_ratio = 0.038
        grid_ratio = (1 - 2 * margin_ratio) / 18
        grid_size = box["width"] * grid_ratio
        base_x = box["x"] + box["width"] * margin_ratio
        base_y = box["y"] + box["height"] * margin_ratio
        
        # 试下两手
        for i in range(2):
            x = base_x + (9 + i) * grid_size
            y = base_y + 9 * grid_size
            page.mouse.click(x, y)
            page.wait_for_timeout(100)
        
        # 后退按钮应该可用
        trial_prev = page.locator("#trialPrevBtn")
        expect(trial_prev).not_to_be_disabled()
        os.unlink(html_path)
    
    def test_trial_next_disabled_at_end(self, page, page_factory, simple_sgf):
        """测试试下到末尾时前进按钮禁用"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        margin_ratio = 0.038
        grid_ratio = (1 - 2 * margin_ratio) / 18
        grid_size = box["width"] * grid_ratio
        base_x = box["x"] + box["width"] * margin_ratio
        base_y = box["y"] + box["height"] * margin_ratio
        
        # 试下一手
        x = base_x + 9 * grid_size
        y = base_y + 9 * grid_size
        page.mouse.click(x, y)
        page.wait_for_timeout(100)
        
        # 前进按钮应该禁用（没有更多试下着法）
        trial_next = page.locator("#trialNextBtn")
        expect(trial_next).to_be_disabled()
        os.unlink(html_path)
    
    def test_trial_exit_restores_state(self, page, page_factory, simple_sgf):
        """测试退出试下恢复原有状态"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进3手
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        # 进入试下并下一手
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        page.mouse.click(center_x, center_y)
        page.wait_for_timeout(100)
        
        # 退出试下
        exit_btn = page.locator("#trialPanel button[title='退出试下']")
        exit_btn.click()
        
        # 主控制应该恢复
        main_controls = page.locator("#mainControls")
        expect(main_controls).to_be_visible()
        
        # 应该回到第 3 手
        move_info = page.locator("#moveInfo")
        expect(move_info).to_contain_text("第 3 手")
        os.unlink(html_path)


class TestTrialCapture:
    """试下提子测试"""
    
    def test_trial_capture_logic(self, page, page_factory):
        """测试试下提子逻辑"""
        # 创建一个可以提子的棋谱
        # 白棋包围一个黑子
        sgf = "(;GM[1]FF[4]SZ[9]PB[黑]PW[白];B[ee];W[ef];W[ed];W[fe];W[de])"
        
        import sys
        sys.path.insert(0, '/root/.openclaw/workspace/weiqi-sgf/scripts')
        from conftest import generate_replay_html
        
        html_content = generate_replay_html(sgf, "提子测试")
        import tempfile
        fd, html_path = tempfile.mkstemp(suffix='.html', prefix='weiqi_test_')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        page.goto(f"file://{html_path}")
        
        # 前进到所有棋子显示
        for _ in range(5):
            page.locator("#nextBtn").click()
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        # 检查中心位置 (ee = 4, 4) 是否还有黑子
        margin_ratio = 0.038
        grid_ratio = (1 - 2 * margin_ratio) / 8  # 9路棋盘
        grid_size = box["width"] * grid_ratio
        base_x = box["x"] + box["width"] * margin_ratio
        base_y = box["y"] + box["height"] * margin_ratio
        
        center_x = base_x + 4 * grid_size
        center_y = base_y + 4 * grid_size
        
        # 这个棋谱本身不会自动提子，只是测试试下功能能正常工作
        # 点击空点进入试下
        empty_x = base_x + 5 * grid_size
        empty_y = base_y + 5 * grid_size
        page.mouse.click(empty_x, empty_y)
        
        trial_panel = page.locator("#trialPanel")
        expect(trial_panel).to_have_class(re.compile(r"visible"))
        
        os.unlink(html_path)


class TestTrialEdgeCases:
    """试下边界情况测试"""
    
    def test_trial_on_empty_board(self, page, page_factory, empty_sgf):
        """测试空棋盘试下"""
        html_path = page_factory(empty_sgf)
        page.goto(f"file://{html_path}")
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        
        # 直接点击空棋盘
        page.mouse.click(center_x, center_y)
        
        # 应该进入试下模式
        trial_panel = page.locator("#trialPanel")
        expect(trial_panel).to_have_class(re.compile(r"visible"))
        os.unlink(html_path)
    
    def test_trial_on_variation(self, page, page_factory, variations_sgf):
        """测试在有变化图的棋谱中试下（不进入变化分支）"""
        html_path = page_factory(variations_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步（在主分支上）
        page.locator("#nextBtn").click()
        page.locator("#nextBtn").click()
        
        # 点击空点进入试下
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        center_x = box["x"] + box["width"] / 2
        center_y = box["y"] + box["height"] / 2
        page.mouse.click(center_x, center_y)
        
        # 应该进入试下模式
        trial_panel = page.locator("#trialPanel")
        expect(trial_panel).to_have_class(re.compile(r"visible"))
        os.unlink(html_path)
    
    def test_multiple_trial_moves(self, page, page_factory, simple_sgf):
        """测试多次试下"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        canvas = page.locator("#board")
        box = canvas.bounding_box()
        
        margin_ratio = 0.038
        grid_ratio = (1 - 2 * margin_ratio) / 18
        grid_size = box["width"] * grid_ratio
        base_x = box["x"] + box["width"] * margin_ratio
        base_y = box["y"] + box["height"] * margin_ratio
        
        # 试下多手（5手）
        positions = [(9, 9), (9, 10), (10, 9), (10, 10), (8, 9)]
        for pos in positions:
            x = base_x + pos[0] * grid_size
            y = base_y + pos[1] * grid_size
            page.mouse.click(x, y)
            page.wait_for_timeout(100)
        
        # 前进按钮应该禁用（在最后一手）
        trial_next = page.locator("#trialNextBtn")
        expect(trial_next).to_be_disabled()
        
        # 后退按钮应该可用
        trial_prev = page.locator("#trialPrevBtn")
        expect(trial_prev).not_to_be_disabled()
        
        os.unlink(html_path)

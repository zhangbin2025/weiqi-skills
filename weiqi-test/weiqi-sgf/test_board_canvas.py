"""
棋盘 Canvas 渲染测试

测试棋盘绘制、棋子渲染、坐标转换等视觉相关功能
"""

import pytest
from playwright.sync_api import expect
import os


class TestBoardRendering:
    """棋盘渲染测试"""
    
    def test_board_background_color(self, page, page_factory, simple_sgf):
        """测试棋盘背景色（典型的围棋木色）"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(100)  # 等待渲染完成
        
        # 获取 Canvas 背景区域的像素颜色（避开中心星位和坐标标签）
        canvas = page.locator("#board")
        
        # 使用 JavaScript 读取像素 - 选择左上角附近，避开坐标标签区域
        pixel_color = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                // 读取 (30, 30) 位置的像素，避开坐标标签和网格线
                const pixel = ctx.getImageData(30, 30, 1, 1).data;
                return { r: pixel[0], g: pixel[1], b: pixel[2] };
            }
        """)
        
        # 棋盘背景应该是木色 #E3C16F (rgb(227, 193, 111))
        # 增加容差范围 ±30
        assert abs(pixel_color['r'] - 227) <= 30, f"棋盘背景 R 值应该在 227±30 范围内，实际 {pixel_color['r']}"
        assert abs(pixel_color['g'] - 193) <= 30, f"棋盘背景 G 值应该在 193±30 范围内，实际 {pixel_color['g']}"
        assert abs(pixel_color['b'] - 111) <= 30, f"棋盘背景 B 值应该在 111±30 范围内，实际 {pixel_color['b']}"
        os.unlink(html_path)
    
    def test_star_points_rendered(self, page, page_factory, simple_sgf):
        """测试星位（天元、小目等）是否正确绘制"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        canvas = page.locator("#board")
        
        # 获取天元（中心点）的像素颜色
        # 19路棋盘天元在 (9, 9)
        star_color = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                // 计算天元位置
                const margin = canvas.width * 0.02 + canvas.width * 0.018;
                const gridSize = (canvas.width - 2 * margin) / 18;
                const starX = Math.floor(margin + 9 * gridSize);
                const starY = Math.floor(margin + 9 * gridSize);
                const pixel = ctx.getImageData(starX, starY, 1, 1).data;
                return { r: pixel[0], g: pixel[1], b: pixel[2] };
            }
        """)
        
        # 星位应该是深色的（#333）
        assert star_color['r'] < 100, "星位应该是深色"
        assert star_color['g'] < 100, "星位应该是深色"
        assert star_color['b'] < 100, "星位应该是深色"
        os.unlink(html_path)
    
    def test_coordinate_labels(self, page, page_factory, simple_sgf):
        """测试坐标标签绘制 - 通过检查文字渲染是否改变像素"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(100)  # 等待渲染完成
        
        canvas = page.locator("#board")
        
        # 获取 Canvas 像素数据（检查是否有深色像素存在）
        # 坐标标签会在边缘区域绘制深色文字
        has_text_pixels = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                // 扫描顶部边缘区域（坐标标签所在位置）
                const baseMargin = canvas.width * 0.02;
                const coordMargin = canvas.width * 0.018;
                const margin = baseMargin + coordMargin;
                
                // 扫描坐标标签区域（顶部和左侧边缘）
                let darkPixelCount = 0;
                const threshold = 100; // 深色阈值
                
                // 扫描顶部边缘（X坐标标签）
                for (let x = 0; x < canvas.width; x += 5) {
                    for (let y = 0; y < margin; y += 2) {
                        const pixel = ctx.getImageData(x, y, 1, 1).data;
                        if (pixel[0] < threshold && pixel[1] < threshold && pixel[2] < threshold) {
                            darkPixelCount++;
                        }
                    }
                }
                
                // 扫描左侧边缘（Y坐标标签）
                for (let x = 0; x < margin; x += 2) {
                    for (let y = 0; y < canvas.height; y += 5) {
                        const pixel = ctx.getImageData(x, y, 1, 1).data;
                        if (pixel[0] < threshold && pixel[1] < threshold && pixel[2] < threshold) {
                            darkPixelCount++;
                        }
                    }
                }
                
                return { darkPixelCount, margin: Math.floor(margin) };
            }
        """)
        
        # 应该有足够的深色像素（坐标标签）
        assert has_text_pixels['darkPixelCount'] > 50, f"应该有坐标标签深色像素，实际找到 {has_text_pixels['darkPixelCount']} 个"
        os.unlink(html_path)


class TestStoneRendering:
    """棋子渲染测试"""
    
    def test_first_stone_rendered(self, page, page_factory, simple_sgf):
        """测试第一手棋子是否正确绘制"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第一手
        page.locator("#nextBtn").click()
        page.wait_for_timeout(200)  # 等待渲染完成
        
        canvas = page.locator("#board")
        
        # 获取动态网格参数和棋子颜色
        stone_check = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                const baseMargin = canvas.width * 0.02;
                const coordMargin = canvas.width * 0.018;
                const margin = baseMargin + coordMargin;
                const gridSize = (canvas.width - 2 * margin) / 18;
                
                // pd = D16，在 19x19 棋盘上
                // x = 'p' - 'a' = 15, y = 'd' - 'a' = 3
                const stoneX = Math.floor(margin + 15 * gridSize);
                const stoneY = Math.floor(margin + 3 * gridSize);
                
                // 检查棋子中心区域（棋子半径约为 gridSize * 0.48）
                const radius = Math.floor(gridSize * 0.3);
                let darkPixels = 0;
                let totalPixels = 0;
                
                for (let dx = -radius; dx <= radius; dx++) {
                    for (let dy = -radius; dy <= radius; dy++) {
                        const x = stoneX + dx;
                        const y = stoneY + dy;
                        if (x >= 0 && x < canvas.width && y >= 0 && y < canvas.height) {
                            const pixel = ctx.getImageData(x, y, 1, 1).data;
                            totalPixels++;
                            // 黑棋 RGB 应该都 < 150
                            if (pixel[0] < 150 && pixel[1] < 150 && pixel[2] < 150) {
                                darkPixels++;
                            }
                        }
                    }
                }
                
                return { 
                    darkPixels, 
                    totalPixels, 
                    stoneX, 
                    stoneY, 
                    centerPixel: ctx.getImageData(stoneX, stoneY, 1, 1).data,
                    ratio: darkPixels / totalPixels 
                };
            }
        """)
        
        # 棋子区域内应该有足够比例的深色像素（>50%）
        assert stone_check['ratio'] > 0.5, f"黑棋区域深色像素比例应该 > 50%，实际 {stone_check['ratio']:.2%}，中心像素 RGB({stone_check['centerPixel'][0]}, {stone_check['centerPixel'][1]}, {stone_check['centerPixel'][2]})"
        os.unlink(html_path)
    
    def test_second_stone_rendered(self, page, page_factory, simple_sgf):
        """测试第二手棋子是否正确绘制"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进到第二手
        page.locator("#nextBtn").click()
        page.locator("#nextBtn").click()
        page.wait_for_timeout(200)  # 等待渲染完成
        
        canvas = page.locator("#board")
        
        # 获取动态网格参数和棋子颜色
        stone_check = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                const baseMargin = canvas.width * 0.02;
                const coordMargin = canvas.width * 0.018;
                const margin = baseMargin + coordMargin;
                const gridSize = (canvas.width - 2 * margin) / 18;
                
                // dp = D4 (小目)
                // dp: x=3, y=15 (从0开始，dp -> d=3, p=15)
                const stoneX = Math.floor(margin + 3 * gridSize);
                const stoneY = Math.floor(margin + 15 * gridSize);
                
                // 检查棋子中心区域
                const radius = Math.floor(gridSize * 0.3);
                let lightPixels = 0;
                let totalPixels = 0;
                
                for (let dx = -radius; dx <= radius; dx++) {
                    for (let dy = -radius; dy <= radius; dy++) {
                        const x = stoneX + dx;
                        const y = stoneY + dy;
                        if (x >= 0 && x < canvas.width && y >= 0 && y < canvas.height) {
                            const pixel = ctx.getImageData(x, y, 1, 1).data;
                            totalPixels++;
                            // 白棋 RGB 应该都 > 150
                            if (pixel[0] > 150 && pixel[1] > 150 && pixel[2] > 150) {
                                lightPixels++;
                            }
                        }
                    }
                }
                
                return { 
                    lightPixels, 
                    totalPixels, 
                    stoneX, 
                    stoneY,
                    centerPixel: ctx.getImageData(stoneX, stoneY, 1, 1).data,
                    ratio: lightPixels / totalPixels 
                };
            }
        """)
        
        # 棋子区域内应该有足够比例的浅色像素（>50%）
        assert stone_check['ratio'] > 0.5, f"白棋区域浅色像素比例应该 > 50%，实际 {stone_check['ratio']:.2%}，中心像素 RGB({stone_check['centerPixel'][0]}, {stone_check['centerPixel'][1]}, {stone_check['centerPixel'][2]})"
        os.unlink(html_path)
    
    def test_last_move_marker(self, page, page_factory, simple_sgf):
        """测试最后一手的标记（小圆点）"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进一手
        page.locator("#nextBtn").click()
        page.wait_for_timeout(100)
        
        canvas = page.locator("#board")
        
        # 最后一手应该有标记（小圆点）
        marker_check = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                const margin = canvas.width * 0.02 + canvas.width * 0.018;
                const gridSize = (canvas.width - 2 * margin) / 18;
                const stoneX = Math.floor(margin + 15 * gridSize);
                const stoneY = Math.floor(margin + 3 * gridSize);
                // 检查棋子中心（应该是白色标记）
                const centerPixel = ctx.getImageData(stoneX, stoneY, 1, 1).data;
                return { r: centerPixel[0], g: centerPixel[1], b: centerPixel[2] };
            }
        """)
        
        # 黑棋上的标记应该是白色
        assert marker_check['r'] > 200, "最后一手标记应该是白色"
        os.unlink(html_path)


class TestHandicapStones:
    """让子测试"""
    
    def test_handicap_stones_rendered(self, page, page_factory, handicap_sgf):
        """测试让子棋子是否正确显示"""
        html_path = page_factory(handicap_sgf)
        page.goto(f"file://{html_path}")
        
        canvas = page.locator("#board")
        
        # 检查四个星位应该有黑子
        # 4 路让子：dd, pd, dp, pp (左上、右上、左下、右下)
        handicap_positions = [
            (3, 3),    # dd
            (15, 3),   # pd
            (3, 15),   # dp
            (15, 15),  # pp
        ]
        
        for pos in handicap_positions:
            stone_color = canvas.evaluate(f"""
                canvas => {{
                    const ctx = canvas.getContext('2d');
                    const margin = canvas.width * 0.02 + canvas.width * 0.018;
                    const gridSize = (canvas.width - 2 * margin) / 18;
                    const stoneX = Math.floor(margin + {pos[0]} * gridSize);
                    const stoneY = Math.floor(margin + {pos[1]} * gridSize);
                    const pixel = ctx.getImageData(stoneX, stoneY, 1, 1).data;
                    return {{ r: pixel[0], g: pixel[1], b: pixel[2] }};
                }}
            """)
            
            # 让子都是黑棋
            assert stone_color['r'] < 100, f"让子位置 {pos} 应该有黑棋"
        
        os.unlink(html_path)
    
    def test_handicap_affects_move_number(self, page, page_factory, handicap_sgf):
        """测试让子后第一手是谁"""
        html_path = page_factory(handicap_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进一手，应该是白棋
        page.locator("#nextBtn").click()
        page.wait_for_timeout(200)
        
        canvas = page.locator("#board")
        
        # qf = Q16
        stone_check = canvas.evaluate("""
            canvas => {
                const ctx = canvas.getContext('2d');
                const baseMargin = canvas.width * 0.02;
                const coordMargin = canvas.width * 0.018;
                const margin = baseMargin + coordMargin;
                const gridSize = (canvas.width - 2 * margin) / 18;
                // qf: q=16, f=5
                const stoneX = Math.floor(margin + 16 * gridSize);
                const stoneY = Math.floor(margin + 5 * gridSize);
                
                // 检查棋子区域
                const radius = Math.floor(gridSize * 0.3);
                let lightPixels = 0;
                let totalPixels = 0;
                
                for (let dx = -radius; dx <= radius; dx++) {
                    for (let dy = -radius; dy <= radius; dy++) {
                        const x = stoneX + dx;
                        const y = stoneY + dy;
                        if (x >= 0 && x < canvas.width && y >= 0 && y < canvas.height) {
                            const pixel = ctx.getImageData(x, y, 1, 1).data;
                            totalPixels++;
                            if (pixel[0] > 150 && pixel[1] > 150 && pixel[2] > 150) {
                                lightPixels++;
                            }
                        }
                    }
                }
                
                return { 
                    lightPixels, 
                    totalPixels, 
                    centerPixel: ctx.getImageData(stoneX, stoneY, 1, 1).data,
                    ratio: totalPixels > 0 ? lightPixels / totalPixels : 0
                };
            }
        """)
        
        # 第一手应该是白棋（让4子后白先），浅色像素比例应该 > 50%
        assert stone_check['ratio'] > 0.5, f"让子后第一手应该是白棋，浅色像素比例 {stone_check['ratio']:.2%}，中心像素 RGB({stone_check['centerPixel'][0]}, {stone_check['centerPixel'][1]}, {stone_check['centerPixel'][2]})"
        os.unlink(html_path)


class TestCanvasResize:
    """Canvas 尺寸调整测试"""
    
    def test_canvas_resizes_with_window(self, page, page_factory, simple_sgf):
        """测试 Canvas 随窗口大小调整"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步确保有棋子
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        # 获取初始尺寸
        canvas = page.locator("#board")
        initial_box = canvas.bounding_box()
        initial_size = (initial_box["width"], initial_box["height"])
        
        # 改变窗口大小
        page.set_viewport_size({"width": 800, "height": 600})
        page.wait_for_timeout(300)  # 等待调整
        
        # 获取新尺寸
        new_box = canvas.bounding_box()
        new_size = (new_box["width"], new_box["height"])
        
        # 尺寸应该变化
        assert new_size != initial_size, "Canvas 应该随窗口调整大小"
        
        # 但宽高比应该保持 1:1
        assert abs(new_box["width"] - new_box["height"]) < 5, "Canvas 应该保持正方形"
        os.unlink(html_path)
    
    def test_stones_visible_after_resize(self, page, page_factory, simple_sgf):
        """测试调整大小后棋子仍然可见"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        page.wait_for_timeout(100)
        
        # 改变窗口大小
        page.set_viewport_size({"width": 400, "height": 600})
        page.wait_for_timeout(300)
        
        canvas = page.locator("#board")
        
        # 检查棋子仍然可见（pd 位置）
        stone_color = canvas.evaluate("""
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
        
        # 黑棋仍然应该可见
        assert stone_color['r'] < 100, "调整大小后黑棋应该仍然可见"
        os.unlink(html_path)


class TestMoveNumbersRendering:
    """手数显示渲染测试"""
    
    def test_move_numbers_visible_when_enabled(self, page, page_factory, simple_sgf):
        """测试开启手数显示后数字可见"""
        html_path = page_factory(simple_sgf)
        page.goto(f"file://{html_path}")
        
        # 前进几步
        for _ in range(3):
            page.locator("#nextBtn").click()
        
        # 开启手数显示
        page.locator("#numToggleBtn").click()
        page.wait_for_timeout(100)
        
        canvas = page.locator("#board")
        
        # 检查棋子中心应该有数字（对比色文字）
        # 黑棋上的数字应该是白色
        text_color = canvas.evaluate("""
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
        
        # 数字应该是亮色（在黑棋上）
        assert text_color['r'] > 180, "手数数字应该可见"
        os.unlink(html_path)

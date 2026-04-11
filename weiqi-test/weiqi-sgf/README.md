# weiqi-sgf 前端自动化测试

使用 Playwright 对 weiqi-sgf 的 replay.html 进行端到端测试。

## 测试覆盖范围

### 1. 页面加载测试 (`test_replay_page.py`)
- 页面标题、棋局信息显示
- Canvas 初始化
- 初始状态验证
- SGF 下载功能

### 2. 棋盘渲染测试 (`test_board_canvas.py`)
- 棋盘背景色、网格线、星位
- 棋子渲染（黑/白）
- 最后一手标记
- 坐标标签显示
- 让子棋子显示
- Canvas 尺寸调整
- 手数数字显示

### 3. 导航控制测试 (`test_navigation.py`)
- 上一手/下一手按钮
- 滑条导航
- 键盘快捷键（←/→/空格）
- 自动播放控制
- 按钮状态管理

### 4. 变化分支测试 (`test_variations.py`)
- 变化面板显示/隐藏
- 变化按钮标签（胜率、名称）
- 进入/退出变化分支
- 变化分支内导航
- 返回上级功能

### 5. 试下功能测试 (`test_trial_mode.py`)
- 试下模式进入/退出
- 试下落子（颜色交替）
- 试下前进/后退
- 提子判断
- 边界情况处理

### 6. 响应式布局测试 (`test_responsive.py`)
- 移动端/桌面端适配
- Canvas 尺寸调整
- 触摸目标大小
- 布局切换状态保持

## 安装依赖

```bash
pip install pytest-playwright
playwright install chromium
```

## 运行测试

### 运行所有测试
```bash
cd /root/.openclaw/workspace/weiqi-test/weiqi-sgf
python run_tests.py
```

### 运行特定测试文件
```bash
pytest test_replay_page.py -v
```

### 运行特定测试类
```bash
pytest test_board_canvas.py::TestStoneRendering -v
```

### 有界面模式（调试用）
```bash
pytest --headed --slowmo=1000
```

### 生成测试报告
```bash
pytest --html=report.html --self-contained-html
```

## 测试数据

测试使用以下 SGF 数据：

- **simple.sgf** - 简单棋谱（8手，无变化图）
- **variations.sgf** - 带变化图的棋谱
- **handicap.sgf** - 让子棋谱（4路让子）
- **empty.sgf** - 空棋谱

## 项目结构

```
weiqi-test/weiqi-sgf/
├── conftest.py              # 测试配置和 fixtures
├── test_replay_page.py      # 页面加载测试
├── test_board_canvas.py     # 棋盘渲染测试
├── test_navigation.py       # 导航控制测试
├── test_variations.py       # 变化分支测试
├── test_trial_mode.py       # 试下功能测试
├── test_responsive.py       # 响应式布局测试
├── run_tests.py             # 测试运行脚本
└── README.md                # 本文档
```

## 编写新测试

参考现有测试，基本结构如下：

```python
def test_example(page, page_factory, simple_sgf):
    """测试示例"""
    # 生成测试页面
    html_path = page_factory(simple_sgf, "测试对局")
    page.goto(f"file://{html_path}")
    
    # 执行操作
    page.locator("#nextBtn").click()
    
    # 验证结果
    move_info = page.locator("#moveInfo")
    expect(move_info).to_contain_text("第 1 手")
    
    # 清理临时文件
    os.unlink(html_path)
```

## 注意事项

1. **临时文件**: 测试会生成临时 HTML 文件，测试结束后自动清理
2. **Canvas 测试**: 像素级测试可能因浏览器渲染差异而失败，设置合理误差范围
3. **异步操作**: 涉及渲染的操作后添加 `page.wait_for_timeout(100)`
4. **无头模式**: CI 环境建议使用 `--headless` 模式

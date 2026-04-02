# 围棋实战选点 (weiqi-move)

从带AI变化图的SGF棋谱中提取选点题，生成交互式做题网页。

## 功能介绍

- **多格式支持**: 自动识别野狐围棋、KataGo、星阵围棋等AI分析棋谱
- **智能提取**: 从变化图中提取选点题，自动去重和分类
- **交互式做题**: 点击棋盘或按钮选点，即时显示对错
- **变化图浏览**: 查看各选点的后续变化
- **难度分级**: 根据胜率差自动判断题目难度（简单/中等/困难）
- **阶段分类**: 自动识别布局、中盘、官子阶段
- **恶手题检测**: 自动识别最优与实战着法差距超过20%的恶手题

## 文件结构

```
weiqi-move/
├── SKILL.md                 # 本文件
├── scripts/
│   ├── sgf_parser.py        # SGF解析器
│   └── quiz.py              # 主脚本
└── templates/
    └── quiz.html            # 做题网页模板
```

## 使用方法

### 基本用法

```bash
# 生成全部选点题
python3 scripts/quiz.py game.sgf

# 指定输出文件
python3 scripts/quiz.py game.sgf -o quiz.html
```

### 题目筛选

```bash
# 只生成恶手题
python3 scripts/quiz.py game.sgf -t blunder

# 只生成中盘题
python3 scripts/quiz.py game.sgf --phase middle

# 组合筛选：中盘的简单题
python3 scripts/quiz.py game.sgf --phase middle -t easy
```

### 题目类型说明

| 类型 | 说明 |
|------|------|
| `blunder` | 恶手题：最优与次优选点胜率差 > 20% |
| `easy` | 简单题：最优胜率 > 次优15% |
| `medium` | 中等题：胜率差 5%-15% |
| `hard` | 困难题：胜率差 < 5% |

### 阶段说明

| 阶段 | 手数范围 |
|------|----------|
| `layout` | ≤ 60手 (布局) |
| `middle` | 60-180手 (中盘) |
| `endgame` | > 180手 (官子) |

## 做题页面操作

### 打谱模式
- **左右箭头 / 滑动条**: 浏览当前题目前的历史进程
- **做题按钮**: 进入做题模式

### 做题模式
- **棋盘点击**: 直接点击带A/B/C/D标注的选点
- **选项按钮**: 点击下方A/B/C/D按钮选点
- **即时反馈**: 选点后立即显示 ✓ / ✗ 对错标记
- **变化图**: 点击查看各选点的后续变化
- **返回打谱**: 回到打谱模式浏览历史

### 题目导航
- **上一题 / 下一题**: 切换题目
- **进度显示**: 显示当前题号/总题数
- **标签**: 显示题目阶段和难度

## 支持格式

### 野狐围棋 (foxwq)
- 特征: 胜率标注、绝艺分析
- 胜率格式: `黑65.3%`、`白48.2%`

### KataGo (katago)
- 特征: KataGo分析标签
- 胜率格式: `B 65.3%`、`W 48.2%`

### 星阵围棋 (xingzhen)
- 特征: 星阵推荐、胜率标注
- 胜率格式: `胜率:黑 65.3%`

## 技术说明

### 提取规则

1. **变化去重**: 第一步坐标相同的变化只保留胜率最高的
2. **题目筛选**: 至少需要两个不同的选点
3. **正确答案**: 胜率最高的选点
4. **难度计算**: 最优与次优选点的胜率差

### HTML输出

生成的单文件HTML包含:
- 完整的围棋规则实现（提子、气、打劫）
- Canvas棋盘渲染
- 响应式布局（支持移动端）
- 纯前端实现，无需服务器

## 示例输出

```bash
$ python3 scripts/quiz.py example.sgf

正在解析: example.sgf
棋局: 柯洁 vs 申真谞
主分支手数: 243
变化图数量: 156
检测到的格式: foxwq

正在提取选点题...
提取到 18 道题目
  - 布局: 3, 中盘: 12, 官子: 3
  - 简单: 8, 中等: 6, 困难: 4
  - 恶手题: 2

正在生成做题网页...
已生成做题网页: /path/to/example.html
```

## 扩展开发

### 添加新的格式适配器

在 `quiz.py` 中添加新的适配器类:

```python
class MyFormatAdapter(FormatAdapter):
    """自定义格式适配器"""
    
    def detect(self, sgf_content: str) -> bool:
        return '特征字符串' in sgf_content
    
    def parse_winrate(self, comment: str) -> Optional[Dict]:
        match = re.search(r'胜率[:\s]*([黑白])\s*(\d+\.?\d*)%', comment)
        if match:
            color = 'B' if match.group(1) == '黑' else 'W'
            return {'color': color, 'rate': float(match.group(2))}
        return None
    
    def get_name(self) -> str:
        return 'myformat'
```

然后将适配器添加到 `FORMAT_ADAPTERS` 列表。

## 依赖

- Python 3.6+
- 仅使用标准库（无第三方依赖）

## 注意事项

1. 棋谱需要包含AI分析的变化图数据
2. 纯对局记录（无AI分析）无法提取选点题
3. 生成的HTML文件可以离线打开使用

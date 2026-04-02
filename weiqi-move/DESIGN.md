# 围棋实战选点 (weiqi-move) - 设计文档

## 1. 概述

### 1.1 名称
- **中文名**: 围棋实战选点
- **英文名**: weiqi-move
- **Slug**: weiqi-move

### 1.2 定位
从带AI变化图的实战棋谱中提取选点题，生成交互式做题网页。

**支持的棋谱格式**:
- 野狐围棋（绝艺）
- KataGo分析棋谱
- 星阵围棋
- 其他带胜率标注的SGF格式（可扩展）

---

## 2. 核心功能

### 2.1 输入
- 带变化图和胜率的SGF棋谱

### 2.2 输出
- 单文件HTML做题网页

### 2.3 做题网页功能

| 功能 | 说明 |
|------|------|
| **棋盘选点** | 直接点击棋盘上的A/B/C/D标注选择答案 |
| **答案判断** | 选点后即时提示对错 |
| **变化图浏览** | 变化图按钮显示对错标记（✓/✗），点击进入查看 |
| **历史打谱** | 浏览当前题目前的完整对局进程 |
| **试下功能** | 支持在棋盘上自由试下 |
| **保存SGF** | 保存当前局面的SGF |

---

## 3. 多格式适配设计

### 3.1 格式检测器

```python
class FormatDetector:
    """检测SGF来源格式"""
    
    FORMATS = {
        'foxwq': {
            'name': '野狐围棋',
            'patterns': ['胜率', '绝艺', '黑.*?%', '白.*?%'],
            'winrate_pattern': r'([黑白]).*?(\d+\.?\d*)%',
        },
        'katago': {
            'name': 'KataGo',
            'patterns': ['KataGo', 'winrate', 'B \d+', 'W \d+'],
            'winrate_pattern': r'([BW]) (\d+\.?\d*)%',
        },
        'xingzhen': {
            'name': '星阵',
            'patterns': ['星阵', '推荐', '胜率'],
            'winrate_pattern': r'胜率[:\s]*([黑白])\s*(\d+\.?\d*)%',
        }
    }
    
    @classmethod
    def detect(cls, sgf_content):
        """返回检测到的格式名称"""
```

### 3.2 胜率解析器

```python
class WinRateParser:
    """统一胜率解析接口"""
    
    PARSERS = {
        'foxwq': FoxWQParser(),
        'katago': KataGoParser(),
        'xingzhen': XingZhenParser(),
        'default': DefaultParser(),
    }
    
    def parse(self, comment, format_type=None):
        """
        解析胜率信息
        Returns: {'color': 'B'/'W', 'rate': float, 'text': str}
        """
```

---

## 4. 文件结构

```
weiqi-move/
├── SKILL.md                 # 技能文档
├── README.md                # 项目说明
├── scripts/
│   ├── sgf_parser.py        # SGF解析（拷贝自weiqi-sgf）
│   └── quiz.py              # 主脚本：提取+生成 ⭐️
└── templates/
    └── quiz.html            # 做题网页模板
```

---

## 5. 核心模块

### 5.1 quiz.py

```python
#!/usr/bin/env python3
"""
围棋实战选点 - 主脚本

功能：
1. 解析SGF棋谱
2. 检测棋谱格式（野狐/KataGo/星阵）
3. 提取选点题
4. 生成做题网页
"""

import argparse
from pathlib import Path

# 格式适配器注册表
FORMAT_ADAPTERS = {}

def register_adapter(name):
    """注册格式适配器装饰器"""
    def decorator(cls):
        FORMAT_ADAPTERS[name] = cls()
        return cls
    return decorator

class FormatAdapter:
    """格式适配器基类"""
    def detect(self, sgf_content):
        return False
    
    def parse_winrate(self, comment):
        return None
    
    def extract_variations(self, node):
        return []

@register_adapter('foxwq')
class FoxWQAdapter(FormatAdapter):
    """野狐围棋适配器"""
    pass

@register_adapter('katago')
class KataGoAdapter(FormatAdapter):
    """KataGo适配器"""
    pass

@register_adapter('xingzhen')
class XingZhenAdapter(FormatAdapter):
    """星阵适配器"""
    pass

def detect_format(sgf_content):
    """检测棋谱格式"""
    for name, adapter in FORMAT_ADAPTERS.items():
        if adapter.detect(sgf_content):
            return name
    return 'default'

def extract_problems(moves, variations, format_type='default'):
    """
    提取选点题
    
    规则：
    - 至少两个不同选点
    - 第一步相同的变化去重（保留胜率最高的）
    - 按手数分类：布局(≤60)/中盘(60-180)/官子(>180)
    - 恶手题：胜率差>20%
    """

def generate_quiz_html(problems, game_info, sgf_content):
    """生成做题网页"""

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser()
    parser.add_argument('sgf', help='输入SGF文件')
    parser.add_argument('-o', '--output', help='输出HTML路径')
    parser.add_argument('-t', '--type', help='题目类型筛选')
    args = parser.parse_args()
    
    # 1. 读取SGF
    # 2. 检测格式
    # 3. 提取题目
    # 4. 生成网页
```

---

## 6. 提取规则

### 6.1 选点提取

```python
def deduplicate_variations(variations):
    """
    第一步相同的变化去重
    保留胜率最高的一个
    """
    seen = {}
    for var in variations:
        first_coord = var['moves'][0]['coord']
        rate = parse_winrate(var['winRate'])
        if first_coord not in seen or rate > seen[first_coord]['rate']:
            seen[first_coord] = var
    return list(seen.values())

def classify_problem(move_num, variations):
    """
    题目分类
    
    阶段：
    - layout: move_num <= 60
    - middle: 60 < move_num <= 180
    - endgame: move_num > 180
    
    难度：
    - easy: 最优胜率 > 次优15%
    - medium: 胜率差 5%-15%
    - hard: 胜率差 < 5%
    
    恶手题：最优与实战着法胜率差 > 20%
    """
```

---

## 7. 做题页面交互

### 7.1 页面布局

```
┌─────────────────────────────┐
│  标题 + 题目类型标签           │
├─────────────────────────────┤
│      ┌───────────────┐      │
│      │    棋盘        │      │ ← 点击选点（A/B/C/D标注）
│      │  (带选点标记)  │      │
│      └───────────────┘      │
├─────────────────────────────┤
│  打谱控制区（进度条/播放）    │ ← 浏览当前题目前的历史
├─────────────────────────────┤
│  结果提示区（隐藏→显示）      │ ← 选点后显示 ✓/✗
├─────────────────────────────┤
│  [变化图 A✓ B✗ C D]        │ ← 按钮显示对错标记
├─────────────────────────────┤
│  [上一题] [下一题] [保存]   │
└─────────────────────────────┘
```

### 7.2 交互逻辑

1. **选点**：点击棋盘上的字母标注 → 即时判断对错
2. **显示结果**：结果区显示 ✓/✗，变化图按钮更新标记
3. **查看变化图**：点击变化图按钮 → 进入变化图模式（禁用打谱）
4. **退出变化图**：✕按钮 → 恢复打谱
5. **切换题目**：上一题/下一题

---

## 8. 扩展性设计

### 8.1 添加新格式适配器

```python
@register_adapter('new_format')
class NewFormatAdapter(FormatAdapter):
    def detect(self, sgf_content):
        return '特征字符串' in sgf_content
    
    def parse_winrate(self, comment):
        match = re.search(r'自定义正则', comment)
        if match:
            return {'color': match.group(1), 'rate': float(match.group(2))}
        return None
```

---

## 9. 使用示例

```bash
# 生成全部选点题
python3 scripts/quiz.py game.sgf

# 只生成中盘恶手题
python3 scripts/quiz.py game.sgf -t blunder --phase middle

# 指定输出
python3 scripts/quiz.py game.sgf -o output.html
```

---

**文档版本**: 1.1  
**最后更新**: 2026-04-02

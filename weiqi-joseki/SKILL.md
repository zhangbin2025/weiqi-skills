---
name: 围棋定式数据库
description: weiqi-joseki 围棋定式数据库 - 基于KataGo棋谱构建。模块化设计，数据完全本地存储。支持定式发现、提取、导出等功能。
tags: ["围棋", "weiqi", "go", "定式", "joseki", "SGF", "KataGo"]
---

# 围棋定式数据库

基于KataGo Archive棋谱构建的围棋定式数据库。采用模块化架构设计，数据完全本地存储，支持从大量棋谱中自动提取高频定式。

**核心理念**: 从实战中学习的定式库，收录AI对局中出现频率最高的定式变化。

## 项目结构

```
weiqi-joseki/
├── SKILL.md                 # 技能文档
└── src/                     # 重构后的模块化代码
    ├── builder/             # 定式库构建器
    │   ├── katago_builder.py
    │   └── __init__.py
    ├── cli/                 # 命令行接口
    │   ├── commands.py
    │   └── __init__.py
    ├── core/                # 核心模块（坐标系统）
    │   ├── coords.py
    │   └── __init__.py
    ├── discover/            # 定式发现
    │   ├── discoverer.py
    │   └── __init__.py
    ├── extraction/          # 棋谱提取
    │   ├── extractor.py
    │   ├── component_detector.py
    │   ├── katago_downloader.py
    │   ├── sgf_parser.py
    │   └── __init__.py
    ├── matching/            # Trie匹配
    │   ├── trie.py
    │   └── __init__.py
    ├── storage/             # 存储
    │   ├── json_storage.py
    │   └── __init__.py
    ├── utils/               # 工具
    │   ├── cms.py
    │   └── __init__.py
    └── __init__.py
```

## 数据存储

- **数据库路径**: `~/.weiqi-joseki/database.json`
- **KataGo缓存**: `~/.weiqi-joseki/katago-cache/`
- 自动创建目录和文件

### 定式数据格式

```json
{
  "joseki_list": [
    {
      "id": "kj_00001",
      "source": "katago",
      "moves": ["pd", "qf", "nc", "rd"],
      "frequency": 5234,
      "direction": "ruld",
      "created_at": "2026-04-21T10:00:00"
    }
  ]
}
```

**字段说明：**
- `id`: 定式唯一标识（格式: kj_NNNNN）
- `source`: 数据来源（katago）
- `moves`: 着法序列（右上角视角，ruld方向）
- `frequency`: 出现频率（统计次数）
- `direction`: 提取时的方向（ruld/rudl）
- `created_at`: 创建时间

**注意**: 数据模型已简化，不再包含name、category、tags等字段，专注于基础定式数据。

## CLI 命令

### 全局选项

```bash
python3 -m src.cli.commands [全局选项] [命令] [选项]
```

**全局选项：**
- `--db <路径>` - 指定数据库路径（默认: ~/.weiqi-joseki/database.json）

### 初始化数据库
```bash
python3 -m src.cli.commands init
```

### 从KataGo构建定式库 ⭐

从 [KataGo Archive](https://katagoarchive.org/kata1/ratinggames/) 下载棋谱并构建定式库。

**基本用法：**
```bash
# 构建指定日期范围的定式库
python3 -m src.cli.commands katago \
  --start-date 2026-01-01 \
  --end-date 2026-04-21
```

**完整参数：**
```bash
python3 -m src.cli.commands katago \
  --start-date 2026-01-01 \      # 起始日期（必需）
  --end-date 2026-04-21 \        # 结束日期（必需）
  --min-freq 10 \                # 最小出现频率（默认10）
  --top-k 100000 \               # 入库数量上限（默认10万）
  --first-n 80 \                 # 每谱提取前N手（默认80）
  --distance-threshold 4 \       # 连通块距离阈值（默认4）
  --min-moves 4                  # 最少手数（默认4）
```

**构建流程：**
1. **下载/检查缓存** - 下载或复用本地缓存的tar文件
2. **Phase 1** - 统一扫描所有棋谱，CMS统计频率
3. **Phase 2-3** - 逆向遍历+单链检测+去重，选取top-k定式
4. **Phase 4** - 统一入库到数据库

**输出示例：**
```
📅 日期范围: 2026-01-01 至 2026-04-21（共110天）
💾 缓存目录: ~/.weiqi-joseki/katago-cache
🗄️  数据库: ~/.weiqi-joseki/database.json

📥 开始下载/检查缓存...
✅ 文件准备完成: 105/110 个

⏳ 开始构建定式库（前80手）...
   参数: min-freq=10, top-k=100000

📊 Phase 1: CMS统计前缀频率...
   处理: 2026-01-01rating.tar.bz2...
      累计: 1211谱, 9104定式串, 288838前缀
   ...
✅ Phase 1完成: 115000谱, 850000定式串, 25000000前缀

🔄 Phase 2-3: 逆向遍历+单链检测+去重...
✅ 构建完成: 52347 条定式

🔄 Phase 4: 保存到数据库...
已保存 52347 条定式到 ~/.weiqi-joseki/database.json

==================================================
🎉 全部完成！共 52347 条定式
==================================================
```

### 列出定式
```bash
# 列出所有定式
python3 -m src.cli.commands list

# 按频率排序
python3 -m src.cli.commands list --sort freq

# 按手数排序
python3 -m src.cli.commands list --sort length

# 限制数量
python3 -m src.cli.commands list --limit 20
```

**输出示例：**
```
共 52347 条定式

ID           手数   频率     着法串
------------------------------------------------------------
kj_00001        4   5234   pd qf nc rd
kj_00002        4   5122   pd qc pc qd
kj_00003        5   2669   pd qc pc qd pe
...
```

### 统计信息
```bash
python3 -m src.cli.commands stats
```

**输出示例：**
```
==================================================
定式库统计
==================================================
总定式数:     52347
总出现次数:   1523456

【频率统计】
  最高:       5234
  最低:       10
  平均:       29.1
  中位数:     15
  Top 10%平均: 156.3

【着法长度统计】
  最长:       31 手
  最短:       4 手
  平均:       6.8 手
  中位数:     6 手

【出现最多定式】
  ID:         kj_00001
  频率:       5234
  着法:       pd qf nc rd
```

### 从SGF提取四角着法
```bash
# 提取四角着法
python3 -m src.cli.commands extract game.sgf

# 详细输出
python3 -m src.cli.commands extract game.sgf --verbose

# 保存MULTIGOGM格式
python3 -m src.cli.commands extract game.sgf --output corners.sgf
```

**输出示例：**
```
提取结果（前80手，距离阈值4）:

【左上】12子
  dd fc df ch cj cm dp dq fq

【右上】15子
  pd qf nc rd qc qd pc pe qb

【左下】8子
  dp cn fq jp jq

【右下】10子
  pp qn on np mq
```

### 从SGF发现定式
```bash
# 发现棋谱中的定式
python3 -m src.cli.commands discover game.sgf

# 详细输出
python3 -m src.cli.commands discover game.sgf --verbose
```

**工作原理：**
1. 提取四角着法
2. 转换到右上角视角
3. 生成ruld和rudl两个方向
4. Trie树匹配最长前缀
5. 返回匹配结果和来源角

**输出示例：**
```
发现定式:

【右上】
  - kj_00001: 匹配4/4手 (ruld)
    定式: pd qf nc rd
  - kj_00015: 匹配8/11手 (rudl)
    定式: pd qc pc qd pe pf...

【左上】
  - kj_00234: 匹配6/6手 (ruld)
    定式: dd fc df ch cj cm
```

### 导出定式
```bash
# 导出为JSON
python3 -m src.cli.commands export --output joseki.json

# 导出为SGF
python3 -m src.cli.commands export --format sgf --output joseki.sgf

# 限制数量
python3 -m src.cli.commands export --limit 1000 --output top1000.json
```

## 核心算法

### 连通块提取（8-connectivity）

从棋谱中提取定式的核心算法：

1. **八连通找块** - 识别棋盘上属于同一局部的棋子
2. **距离阈值合并** - 距离小于阈值的连通块合并
3. **最近角筛选** - 只保留离角最近的连通块
4. **脱先检测** - 检测连续同色着法，插入tt标记

### CMS频率统计

Count-Min Sketch算法估算前缀出现频率：
- 宽度: 200000
- 深度: 5
- 内存占用: ~3.8MB

### 逆向遍历 + 单链检测

从长到短遍历前缀，检测单链并去重：
- 单链阈值: 5%（count变化小于5%视为单链）
- 小顶堆选top-k
- 统一转ruld方向去重

## Python API

```python
from weiqi_joseki.src.builder import KatagoJosekiBuilder, build_katago_joseki_db
from weiqi_joseki.src.discover import discover_joseki, JosekiDiscoverer
from weiqi_joseki.src.extraction import extract_moves_all_corners, get_move_sequence
from weiqi_joseki.src.storage import JsonStorage

# 构建定式库
joseki_list = build_katago_joseki_db(
    tar_path="/path/to/katago.tar.bz2",
    db_path="~/.weiqi-joseki/database.json",
    min_freq=10,
    top_k=100000,
    first_n=80,
    distance_threshold=4,
    min_moves=4
)

# 发现定式
storage = JsonStorage()
joseki_list = storage.get_all()

results = discover_joseki(
    sgf_data=open("game.sgf").read(),
    joseki_list=joseki_list,
    first_n=80,
    distance_threshold=4
)

for corner, matches in results.items():
    for match in matches:
        print(f"{corner}: {match.joseki_id} "
              f"匹配{match.prefix_len}/{match.total_moves}手")

# 提取四角着法
result = extract_moves_all_corners(
    sgf_data=open("game.sgf").read(),
    first_n=80,
    distance_threshold=4
)

for corner, moves in result.items():
    coords = get_move_sequence(moves)
    print(f"{corner}: {' '.join(coords)}")
```

## 隐私声明

- ❌ 不收集个人数据
- ❌ 无内置数据
- ✅ 数据完全本地存储
- ✅ 仅提供开放数据获取工具

## 依赖

- Python 3.6+
- 无第三方依赖（纯标准库）

## 版本更新

### v1.2.0 (2026-04-21) - 重构版
- ✅ **完全重构**: 从旧代码重构为模块化架构
- ✅ **简化数据模型**: 去除name/category/tags字段，保留核心数据
- ✅ **统一入库**: 先扫描所有棋谱统计，再统一选取定式入库
- ✅ **简化CLI**: 保留核心命令（init, katago, list, stats, extract, discover, export）
- ✅ **连通块提取**: 使用8-connectivity检测棋盘上同一局部的棋子
- ✅ **核心算法保留**: CMS统计、逆向遍历、单链检测全部保留

### v1.1.x (2026-04-10 及之前)
- 旧版本功能（已归档）

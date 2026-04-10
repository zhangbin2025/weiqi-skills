---
name: 围棋定式数据库
description: weiqi-joseki 围棋定式数据库 - 支持定式录入、自动角位识别、8向变化生成、去重、冲突检测、棋谱定式识别。模块化设计，支持从KataGo Archive自动导入。数据存储于 ~/.weiqi-joseki/database.json
tags: ["围棋", "weiqi", "go", "定式", "joseki", "变化图", "SGF", "定式识别"]
---

# 围棋定式数据库

模块化围棋定式数据库，支持自动角位识别、8向变化生成、冲突检测、定式识别。代码采用模块化设计，便于维护和扩展。

## 项目结构

```
weiqi-joseki/
├── db.py                    # 兼容性入口（已弃用，保留向后兼容）
├── SKILL.md                 # 技能文档
└── scripts/                 # 核心模块目录
    ├── __init__.py          # 包初始化
    ├── cli.py               # 命令行入口
    ├── sgf_parser.py        # SGF解析器
    ├── joseki_extractor.py  # 定式提取器
    ├── joseki_db.py         # 定式数据库核心
    └── katago_downloader.py # KataGo棋谱下载器
```

## 数据存储

- **数据库路径**: `~/.weiqi-joseki/database.json`
- 自动创建目录和文件

## CLI 命令

### 全局选项

```bash
python3 scripts/cli.py [全局选项] [命令] [选项]
```

**全局选项：**
- `--db <路径>` - 指定数据库路径（默认: ~/.weiqi-joseki/database.json）

### 初始化数据库
```bash
python3 scripts/cli.py init
```

### 添加定式
```bash
# 从坐标添加
python3 scripts/cli.py add --name "星位小飞挂" --category "/星位/小飞挂" --moves "pd,qf,nc,rd"

# 从SGF添加（自动识别角位并转换为右上角视角）
python3 scripts/cli.py add --name "定式名" --category "/分类" --sgf "(;B[pd];W[qf]...)"

# 强制添加（跳过冲突检测）
python3 scripts/cli.py add ... --force

# 添加标签和描述
python3 scripts/cli.py add --name "定式名" --category "/分类" --moves "pd,qf" --tag "标签1" --tag "标签2" --description "描述"
```

**入库流程：**
1. 自动识别定式属于哪个角（左上/右上/左下/右下）
2. 转换到**右上角视角**（ruld 方向）统一存储
3. 检查是否与已有定式冲突（比较 ruld 和 rudl 两个方向）

### 删除定式
```bash
python3 scripts/cli.py remove <定式ID>
```

### 清空数据库
```bash
# 交互式确认
python3 scripts/cli.py clear

# 强制清空
python3 scripts/cli.py clear --force
```

### 列出现式
```bash
# 列出所有
python3 scripts/cli.py list

# 按分类列出
python3 scripts/cli.py list --category "/星位"

# 限制数量
python3 scripts/cli.py list --limit 20
```

### 生成8向变化SGF ⭐
```bash
# 输出到控制台
python3 scripts/cli.py 8way <定式ID>

# 保存到文件
python3 scripts/cli.py 8way <定式ID> --output joseki_8way.sgf

# 指定特定方向（逗号分隔）
python3 scripts/cli.py 8way <定式ID> --direction "ruld,rudl"
```

**8向SGF格式示例：**
```
(;CA[utf-8]FF[4]AP[JosekiDB]SZ[19]GM[1]KM[0]MULTIGOGM[1]C[定式名]
  (C[左上(右→下) lurd];B[dd];W[cf];B[fc]...)
  (C[左上(下→右) ludr];B[dc];W[ce];B[fc]...)
  ...
)
```

**8个方向说明：**
| 方向 | 位置 | 描述 |
|------|------|------|
| lurd | 左上 | 右→下 |
| ludr | 左上 | 下→右 |
| ldru | 左下 | 右→上 |
| ldur | 左下 | 上→右 |
| ruld | 右上 | 左→下 |
| rudl | 右上 | 下→左 |
| rdlu | 右下 | 左→上 |
| rdul | 右下 | 上→左 |

### 匹配定式
```bash
# 从文件匹配指定角
python3 scripts/cli.py match --sgf-file game.sgf --corner tr --top-k 5

# 从SGF字符串匹配
python3 scripts/cli.py match --sgf "(;B[pd];W[qf]...)" --corner tl

# 从stdin读取SGF
python3 scripts/cli.py match < game.sgf
```

### 识别整盘棋
```bash
# 表格格式输出
python3 scripts/cli.py identify --sgf-file game.sgf

# JSON格式输出
python3 scripts/cli.py identify --sgf-file game.sgf --output json

# 指定返回匹配数量
python3 scripts/cli.py identify --sgf-file game.sgf --top-k 3
```

**输出示例：**
```
======================================================================
「定式识别结果」
======================================================================
  左上: 小目小飞挂 (相似度: 0.92) ✓ 高置信度
  右上: 星位点三三 (相似度: 0.88)
  左下: (无匹配)
  右下: 星位小飞挂 (相似度: 0.95) ✓ 高置信度
======================================================================
```

### 统计信息
```bash
python3 scripts/cli.py stats
```

### 从SGF提取定式
```bash
# 提取四角定式（输出MULTIGOGM格式）
python3 scripts/cli.py extract --sgf-file game.sgf

# 只取前N手
python3 scripts/cli.py extract --sgf-file game.sgf --first-n 50

# 只提取指定角（tl=左上, tr=右上, bl=左下, br=右下）
python3 scripts/cli.py extract --sgf-file game.sgf --corner tr

# 保存到文件
python3 scripts/cli.py extract --sgf-file game.sgf --output joseki.sgf
```

**输出格式：**
```
(;CA[utf-8]FF[4]AP[JosekiExtract]SZ[19]GM[1]KM[0]MULTIGOGM[1]
  (C[右上 黑先];B[pd];W[qf];B[nc];W[rd]...)
  (C[左上 白先→黑先];B[pc];W[qe];B[od]...)
  (C[左下 白先→黑先];B[qd];W[pd];B[pc]...)
  (C[右下 黑先 含脱先];B[pc];W[pe];B[qe]...;W[tt])
)
```

### 批量导入定式 ⭐
```bash
# 从SGF目录批量导入（自动提取、统计频率、入库）
python3 scripts/cli.py import /path/to/sgf/dir

# 设置最少出现次数（默认10）
python3 scripts/cli.py import /path/to/sgf/dir --min-count 5

# 设置最少手数（默认4手）
python3 scripts/cli.py import /path/to/sgf/dir --min-moves 3

# 设置最小出现概率%（默认0）
python3 scripts/cli.py import /path/to/sgf/dir --min-rate 1.0

# 设置每谱提取前N手（默认50）
python3 scripts/cli.py import /path/to/sgf/dir --first-n 80

# 试运行（只统计不真入库）
python3 scripts/cli.py import /path/to/sgf/dir --dry-run
```

**完整示例：**
```bash
python3 scripts/cli.py import /path/to/sgf/dir \
    --min-count 10 \
    --min-moves 4 \
    --min-rate 0.5 \
    --first-n 50
```

**输出示例：**
```
📁 找到 97 个SGF文件
⏳ 正在提取定式（前50手）...
✅ 提取到 370 个定式（去重后 89 个）
⏳ 正在统计前缀频率...

📊 统计结果（次数≥10，手数≥4，概率≥0.5%）:
   总棋谱数: 97，候选定式: 24
排名     频率       定式
------------------------------------------------------------
1      50       pd qc pc qd                              (4手)
2      35       pd qc qd pc                              (4手)
3      27       pd qc pc qd qf                           (5手)
...

⏳ 开始入库（共24个候选）...
✅ 入库: joseki_001 (4手, 频率50)
✅ 入库: joseki_002 (5手, 频率27)
...

🎉 完成！新增 13 个定式，跳过 11 个（已存在）
```

### 导出定式库 ⭐
```bash
# 导出全部到文件
python3 scripts/cli.py export --output joseki_library.sgf

# 按分类导出
python3 scripts/cli.py export --category "/星位" --output star_joseki.sgf

# 按手数范围导出
python3 scripts/cli.py export --min-moves 4 --max-moves 10 --output short_joseki.sgf

# 按标签导出
python3 scripts/cli.py export --tag "常用" --export common.sgf

# 指定定式ID导出
python3 scripts/cli.py export --id "joseki_001,joseki_002" --output selected.sgf
```

### 从KataGo棋谱库导入定式 ⭐⭐

自动从 [KataGo Archive](https://katagoarchive.org/kata1/ratinggames/) 下载棋谱并提取定式。

**KataGo棋谱库信息：**
- 基础URL: https://katagoarchive.org/kata1/ratinggames/
- 文件格式: YYYY-MM-DDrating.tar.bz2（每日一个压缩包，200KB-6MB）
- 每个压缩包包含数百至数千局SGF棋谱
- 数据范围: 约2019年起 **持续更新中**（可获取最新日期数据）

**基本用法：**
```bash
# 下载一周的数据并提取定式
python3 scripts/cli.py katago --start-date 2026-03-01 --end-date 2026-03-07

# 只统计不入库（试运行）
python3 scripts/cli.py katago --start-date 2026-03-01 --end-date 2026-03-07 --dry-run

# 断点续传（中断后从上次位置继续）
python3 scripts/cli.py katago --start-date 2026-03-01 --end-date 2026-03-07 --resume

# 导入整个月的数据（如2026年3月）
python3 scripts/cli.py katago --start-date 2026-03-01 --end-date 2026-03-31 --min-count 5
```

**完整参数：**
```bash
python3 scripts/cli.py katago \
    --start-date 2026-03-01 \           # 起始日期（必需）
    --end-date 2026-03-31 \             # 结束日期（必需）
    --cache-dir ~/.weiqi-joseki/katago-cache \  # 下载缓存目录
    --remove-cache \                    # 下载后删除缓存（默认保留）
    --workers 3 \                       # 并行下载线程数（默认1）
    --max-memory-mb 512 \               # 内存上限MB（默认512）
    --resume \                          # 断点续传
    --min-count 10 \                    # 最少出现次数才入库（默认10）
    --min-moves 4 \                     # 最少手数（默认4）
    --min-rate 0.5 \                    # 最小出现概率%（默认0.5）
    --first-n 100 \                     # 每谱提取前N手（默认50）
    --dry-run                           # 试运行
```

**输出示例：**
```
📅 日期范围: 2026-03-01 至 2026-03-31（共31天）
💾 缓存目录: ~/.weiqi-joseki/katago-cache
📊 进度文件: ~/.weiqi-joseki/katago-progress.json

📥 开始下载（并行3线程）...
📥 下载进度: 7/7 (100.0%) | 当前: 2026-03-07rating.tar.bz2 | 剩余时间: 0s
✅ 下载完成: 7/7 个文件

⚙️ 开始处理棋谱（前100手）...
⚙️ 处理进度: 7/7 | 当前: 2026-03-07   | 棋谱: 2844 | 定式: 3358 | 内存: 0.0MB | 剩余: 0s

⏳ 正在统计前缀频率...

📊 统计结果（次数≥10，手数≥4，概率≥0.5%）：
   总棋谱数: 10375，候选定式: 290
排名     频率       定式
------------------------------------------------------------
1      5225     pd qc pc qd                              (4手)
2      5122     pd qc qd pc                              (4手)
3      2669     pd qc pc qd pe                           (5手)
...

⏳ 开始入库（共81个候选）...
✅ 入库: joseki_001 (6手, 频率647)
✅ 入库: joseki_002 (8手, 频率507)
...

🎉 完成！新增 60 个定式，跳过 21 个（已存在）
🧹 已清理进度文件
```

**功能特性：**
- **断点续传**: 使用 `--resume` 从中断处继续，进度保存在 `~/.weiqi-joseki/katago-progress.json`
- **内存控制**: 自动监控内存使用，超过90%时强制GC，超过100%时保存进度退出
- **流式解压**: 不解压整个文件，直接流式读取tar.bz2内容
- **多线程下载**: 支持并行下载多个日期的文件
- **错误恢复**: 下载失败自动重试3次，解压失败跳过该日期
- **信号捕获**: Ctrl+C 中断时自动保存进度
- **脱先定式**: 支持检测"角部下棋→脱先→回角部继续"的完整定式序列

## Python API

```python
from scripts.joseki_db import JosekiDB

# 初始化
db = JosekiDB()  # 使用默认路径 ~/.weiqi-joseki/database.json

# 添加定式（自动识别角位并转换为右上角视角）
joseki_id, conflict = db.add(
    name="星位小飞挂一间低夹",
    category_path="/星位/小飞挂/一间低夹",
    moves=["B[pd]", "W[qf]", "B[nc]", ...]
)

# 检查冲突（比较右上角 ruld 和 rudl 两个方向）
conflict = db.check_conflict(moves)
if conflict.has_conflict:
    for s in conflict.similar_joseki:
        print(f"冲突: {s['name']}")

# 匹配定式
results = db.match(["pd", "qf", "nc", "rd"], top_k=5)
for r in results:
    print(f"{r.name}: {r.similarity:.2f} ({r.matched_direction})")

# 生成8向SGF ⭐
sgf = db.generate_8way_sgf("joseki_001")
with open("output.sgf", "w") as f:
    f.write(sgf)

# 识别棋谱四角
results = db.identify_corners(sgf_data, top_k=3)
for corner, matches in results.items():
    print(f"{corner}: {matches[0].name if matches else '无匹配'}")

# 从SGF提取四角定式
from scripts.joseki_extractor import extract_joseki_from_sgf
sgf = open("game.sgf").read()
result = extract_joseki_from_sgf(sgf, first_n=50)  # 输出MULTIGOGM格式
print(result)

# 批量导入定式
added, skipped, candidates = db.import_from_sgfs(
    sgf_sources=["/path/to/game1.sgf", "/path/to/game2.sgf"],
    min_count=10,
    min_moves=4,
    min_rate=0.5,
    first_n=50,
    dry_run=False,
    progress_callback=lambda c, t: print(f"{c}/{t}")
)

# 导出定式库
sgf = db.export_to_sgf(
    output_path="joseki_library.sgf",
    category="/星位",
    min_moves=4,
    max_moves=20,
    tags=["常用"],
    ids=["joseki_001", "joseki_002"]
)
```

## 数据格式

### 定式条目
```json
{
  "id": "joseki_001",
  "name": "星位小飞挂",
  "category_path": "/星位/小飞挂",
  "description": "",
  "tags": [],
  "moves": ["pd", "qf", "nc", "rd"],
  "created_at": "2026-03-29T23:22:36.968667"
}
```

**字段说明：**
- `id`: 定式唯一标识
- `name`: 定式名称（可选）
- `category_path`: 分类路径（可选）
- `description`: 描述字段（可选）
- `tags`: 标签数组（可选）
- `moves`: 定式着法序列（统一存储为**右上角 ruld 视角**）
- `created_at`: 创建时间

> **存储优化**: 数据库只存储单一方向（右上角 ruld）的变化，需要时动态生成8向。这大幅减少了存储空间，同时保证冲突检测和匹配的准确性。

### 8个方向
在冲突检测、匹配和8向SGF生成时，系统会自动从单一方向展开为8个方向：

| 方向 | 位置 | 描述 |
|------|------|------|
| lurd | 左上 | 右→下 |
| ludr | 左上 | 下→右 |
| ldru | 左下 | 右→上 |
| ldur | 左下 | 上→右 |
| ruld | 右上 | 左→下 |
| rudl | 右上 | 下→左 |
| rdlu | 右下 | 左→上 |
| rdul | 右下 | 上→左 |

**冲突检测规则：**
- 输入定式 → 自动检测角位 → 转换到右上角视角
- 与库里定式比较两个方向：
  - **ruld** (左→下)：直接比较存储坐标
  - **rudl** (下→左)：转换后比较
- 任一方向匹配即视为同一定式

## 分类体系

使用路径形式：`/一级/二级/三级/...`

路径层级不限定，可根据需要灵活扩展：
- `/星位/小飞挂/一间低夹`
- `/星位/小飞挂/一间低夹/压长`           （5级分类）
- `/星位/一间高挂/点三三/飞刀定式/大雪崩` （6级分类）
- `/小目/小飞挂/托退/雪崩型/大雪崩/内拐`  （7级分类）
- `/三三/肩冲`

### 分类建议

**一级分类**（按角部位置）：
- `/星位` - 4-4 点
- `/小目` - 3-4 点
- `/三三` - 3-3 点
- `/目外` - 3-5 点
- `/高目` - 4-5 点
- `/五五` - 5-5 点

**二级及以下**（按棋形/变化展开）：
- 挂角方式：小飞挂、一间高挂、二间高挂、大飞挂
- 应对方式：托退、压长、一间低夹、一间高夹
- 变化名称：雪崩型、大雪崩、小雪崩、飞刀定式

分类路径可任意深度，按需细化。

## 脱先定式提取详解

### 什么是脱先定式

脱先（pass）指在局部战斗中暂时不应，转投其他大场。脱先后若双方继续在该角行棋，形成的变化就是**脱先定式**。

**示例定式（joseki_004）：**
```
pd qc pc qd qf qe pe rf tt qg pf qb
```
- 前8手：点三三后的基本定型
- 第9手 `tt`：⚡ **白脱先**（未立即应）
- 第10-12手：黑继续进攻，白应对

### 脱先检测逻辑

**问题场景：**
棋谱中各角着法交错，如：
```
B[pd](右上) W[dp](右下) B[pp](右下) W[dd](左上) B[qf](右上) ...
```

**处理流程：**
1. **角部分类**：将每个着法归类到四角（左上/右上/左下/右下）
2. **脱先检测**：在同一角内，若当前着法颜色与上一手相同，说明对方脱先了
3. **插入标记**：在连续同色棋之间插入 `tt` 标记

**示例处理：**
```
原始棋谱: B[pd] W[dp] B[pp] W[dd] B[qf] W[nc] ...
右上序列: B[pd] B[qf] W[nc] ...
          ↓     ↓
       连续黑子，检测到白脱先

处理后:   B[pd] W[tt] B[qf] W[nc] ...
```

### 实战效果

从KataGo棋谱库提取结果：
- **总定式数**: 60个
- **含脱先定式**: 34个 (56.7%)
- **最长定式**: 31手（第30手脱先）

这说明脱先定式在AI对局中非常常见，是定式库的重要组成部分。

## 依赖

- Python 3.6+
- 无第三方依赖（纯标准库）

## 版本更新

### v1.2.0 (2026-04-10)
- ✅ **代码重构**: 从单文件结构重构为模块化设计，代码更清晰、易于维护
  - `sgf_parser.py` - 独立的SGF解析模块
  - `joseki_extractor.py` - 定式提取逻辑
  - `joseki_db.py` - 定式数据库核心
  - `katago_downloader.py` - KataGo下载器
  - `cli.py` - 统一的命令行入口
- ✅ **向后兼容**: `db.py` 保留作为兼容性入口，原有命令仍然可用
- ✅ **新增命令**: 
  - `export` - 导出定式库到SGF，支持按分类、手数、标签、ID过滤
  - `katago` - 从KataGo Archive自动下载棋谱并提取定式
- ✅ **功能增强**:
  - `8way` 新增 `--direction` 参数，可指定生成特定方向
  - `import` 和 `katago` 新增 `--min-rate` 参数，按出现概率筛选
  - 全局 `--db` 参数，可指定自定义数据库路径
- ✅ **性能优化**: 修复内存溢出问题，优化KataGo下载缓存策略
- ✅ **Bug修复**: 修复8向生成、SGF后缀解析等问题

### v1.1.1 (2026-04-06)
- ✅ **文档修正**: 更新KataGo Archive数据时间范围说明（支持2019-2026年最新数据）
- ✅ **示例更新**: 将示例日期更新为2026年，与实际数据保持一致

### v1.1.0 (2026-03-31)
- ✅ **内存优化**: Hash表统计+前缀累加，支持百万级棋谱处理
- ✅ **概率筛选**: 新增 `--min-rate` 参数，按出现概率筛选定式
- ✅ **KataGo导入**: 支持从KataGo Archive自动下载并提取定式
- ✅ **脱先定式**: 完善脱先检测逻辑，支持"角部-脱先-回角部"完整序列
- ✅ **断点续传**: KataGo导入支持 `--resume` 断点续传
- ✅ **内存控制**: 自动监控内存，超限自动保存进度并退出

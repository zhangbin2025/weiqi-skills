---
name: 围棋定式数据库
description: weiqi-joseki 围棋定式数据库 - 支持定式录入、自动角位识别、8向变化生成、去重、冲突检测、棋谱定式识别。数据存储于 ~/.weiqi-joseki/database.json
tags: ["围棋", "weiqi", "go", "定式", "joseki", "变化图", "SGF", "定式识别"]
---

# 围棋定式数据库

单文件版围棋定式数据库，支持自动角位识别、8向变化生成、冲突检测、定式识别。

## 数据存储

- **数据库路径**: `~/.weiqi-joseki/database.json`
- 自动创建目录和文件

## 核心文件

```
weiqi-joseki/
├── db.py          # 单文件，包含所有功能
└── SKILL.md       # 技能文档
```

## CLI 命令

### 初始化数据库
```bash
python3 db.py init
```

### 添加定式
```bash
# 从坐标添加
python3 db.py add --name "星位小飞挂" --category "/星位/小飞挂" --moves "pd,qf,nc,rd"

# 从SGF添加（自动识别角位并转换为右上角视角）
python3 db.py add --name "定式名" --category "/分类" --sgf "(;B[pd];W[qf]...)"

# 强制添加（跳过冲突检测）
python3 db.py add ... --force
```

**入库流程：**
1. 自动识别定式属于哪个角（左上/右上/左下/右下）
2. 转换到**右上角视角**（ruld 方向）统一存储
3. 检查是否与已有定式冲突（比较 ruld 和 rudl 两个方向）

### 删除定式
```bash
python3 db.py remove joseki_001
```

### 清空数据库
```bash
python3 db.py clear
```

### 列出现式
```bash
python3 db.py list
python3 db.py list --category "/星位"
```

### 生成8向变化SGF ⭐
```bash
# 输出到控制台
python3 db.py 8way joseki_001

# 保存到文件
python3 db.py 8way joseki_001 --output joseki_8way.sgf
```

**8向SGF格式示例：**
```
(;CA[utf-8]FF[4]AP[JosekiDB]SZ[19]GM[1]KM[0]MULTIGOGM[1]C[定式名]
  (C[左上(右→下) lurd];B[dd];W[cf];B[fc]...)
  (C[左上(下→右) ludr];B[dc];W[ce];B[fc]...)
  ...
)
```

### 匹配定式
```bash
# 匹配SGF中的某个角
python3 db.py match --sgf "(;B[pd];W[qf]...)" --corner tr
python3 db.py match --sgf-file game.sgf --corner tl
```

### 识别整盘棋
```bash
python3 db.py identify --sgf-file game.sgf
python3 db.py identify --sgf-file game.sgf --output json
```

### 统计信息
```bash
python3 db.py stats
```

### 从SGF提取定式 ⭐
```bash
# 提取四角定式（输出MULTIGOGM格式）
python3 db.py extract --sgf-file game.sgf

# 只取前N手
python3 db.py extract --sgf-file game.sgf --first-n 50

# 只提取指定角（tl=左上, tr=右上, bl=左下, br=右下）
python3 db.py extract --sgf-file game.sgf --corner tr

# 保存到文件
python3 db.py extract --sgf-file game.sgf --output joseki.sgf
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

**功能说明：**
- 自动从四角提取定式变化
- 所有坐标转换为视觉右上角（便于统一查看）
- 白先定式自动转为黑先（颜色互换）
- 支持脱先检测（用 `tt` 标记）

### 批量导入定式 ⭐（自动提取+统计+入库）
```bash
# 从SGF目录批量导入（自动提取、统计频率、入库）
python3 db.py import /path/to/sgf/dir

# 设置最少出现次数（默认10）
python3 db.py import /path/to/sgf/dir --min-count 5

# 设置最少手数（默认4手）
python3 db.py import /path/to/sgf/dir --min-moves 3

# 设置最小出现概率%（默认0）
python3 db.py import /path/to/sgf/dir --min-rate 1.0

# 设置每谱提取前N手（默认50）
python3 db.py import /path/to/sgf/dir --first-n 80

# 试运行（只统计不真入库）
python3 db.py import /path/to/sgf/dir --dry-run
```

**完整示例：**
```bash
python3 db.py import /path/to/sgf/dir \
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

**算法说明：**
1. **Hash表去重**：使用Hash表统计定式出现次数（`count_map`），大幅减少内存占用（100万定式→1万唯一定式）
2. **前缀频率统计**：排序唯一定式串，遍历检查前缀关系，累加后续定式的次数（如"pd qc"的频率包含所有以它为前缀的定式）
3. **概率筛选**：`--min-rate` 按出现概率筛选（如1%表示只保留出现≥1%的定式）
4. **筛选入库**：频率≥`--min-count`，手数≥`--min-moves`，概率≥`--min-rate`

**脱先定式检测：**
- 检测当前角序列内的连续同色棋（如黑pd后直接黑qf）
- 在连续的同色棋之间插入对方脱先标记 `tt`
- 支持"角部下棋→脱先→其他→回角部继续"的完整序列

### 从KataGo棋谱库导入定式 ⭐⭐

自动从 [KataGo Archive](https://katagoarchive.org/kata1/ratinggames/) 下载棋谱并提取定式。

**KataGo棋谱库信息：**
- 基础URL: https://katagoarchive.org/kata1/ratinggames/
- 文件格式: YYYY-MM-DDrating.tar.bz2（每日一个压缩包，200KB-6MB）
- 每个压缩包包含数百至数千局SGF棋谱
- 数据更新至: 2022年底

**基本用法：**
```bash
# 下载一周的数据并提取定式
python3 db.py katago --start-date 2022-12-17 --end-date 2022-12-23

# 只统计不入库（试运行）
python3 db.py katago --start-date 2022-12-17 --end-date 2022-12-23 --dry-run

# 断点续传（中断后从上次位置继续）
python3 db.py katago --start-date 2022-12-17 --end-date 2022-12-23 --resume
```

**完整参数：**
```bash
python3 db.py katago \
    --start-date 2022-12-17 \           # 起始日期（必需）
    --end-date 2022-12-23 \             # 结束日期（必需）
    --cache-dir ~/.weiqi-joseki/katago-cache \  # 下载缓存目录
    --keep-cache \                      # 保留缓存文件（默认删除）
    --workers 3 \                       # 并行下载线程数（默认3）
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
📅 日期范围: 2022-12-17 至 2022-12-23（共7天）
💾 缓存目录: ~/.weiqi-joseki/katago-cache
📊 进度文件: ~/.weiqi-joseki/katago-progress.json

📥 开始下载（并行3线程）...
📥 下载进度: 7/7 (100.0%) | 当前: 2022-12-23rating.tar.bz2 | 剩余时间: 0s
✅ 下载完成: 7/7 个文件

⚙️ 开始处理棋谱（前100手）...
⚙️ 处理进度: 7/7 | 当前: 2022-12-23   | 棋谱: 2844 | 定式: 3358 | 内存: 0.0MB | 剩余: 0s

⏳ 正在统计前缀频率...

📊 统计结果（次数≥10，手数≥4，概率≥0.5%）：
   总棋谱数: 2844，候选定式: 81
排名     频率       定式
------------------------------------------------------------
1      647      pd qc qd pc od nb                        (6手)
2      632      pd qc pc qd pe rf                        (6手)
3      507      pd qc pc qd qf qe pe rf                  (8手)
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
from db import JosekiDB

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
from db import extract_joseki_from_sgf
sgf = open("game.sgf").read()
result = extract_joseki_from_sgf(sgf, first_n=50)  # 输出MULTIGOGM格式
print(result)
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

### v1.1.0 (2026-03-31)
- ✅ **内存优化**: Hash表统计+前缀累加，支持百万级棋谱处理
- ✅ **概率筛选**: 新增 `--min-rate` 参数，按出现概率筛选定式
- ✅ **KataGo导入**: 支持从KataGo Archive自动下载并提取定式
- ✅ **脱先定式**: 完善脱先检测逻辑，支持"角部-脱先-回角部"完整序列
- ✅ **断点续传**: KataGo导入支持 `--resume` 断点续传
- ✅ **内存控制**: 自动监控内存，超限自动保存进度并退出

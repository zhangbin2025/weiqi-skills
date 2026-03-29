---
name: 围棋定式数据库
description: weiqi-joseki 围棋定式数据库 - 支持定式录入、8向变化生成、去重、冲突检测、棋谱定式识别。数据存储于 ~/.weiqi-joseki/database.json
tags: ["围棋", "weiqi", "go", "定式", "joseki", "变化图", "SGF", "定式识别"]
---

# 围棋定式数据库

单文件版围棋定式数据库，支持8向变化生成、冲突检测、定式识别。

## 数据存储

- **数据库路径**: `~/.weiqi-joseki/database.json`
- 自动创建目录和文件

## 核心文件

```
weiqi-joseki/
├── db.py          # 单文件，包含所有功能
├── SKILL.md       # 技能文档
└── README.md      # 项目说明
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

# 从SGF添加
python3 db.py add --name "定式名" --category "/分类" --sgf "(;B[pd];W[qf]...)"

# 强制添加（跳过冲突检测）
python3 db.py add ... --force
```

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

### 从OGS抓取定式 🌐

支持从 [OGS Joseki Explorer](https://online-go.com/joseki/) 自动抓取定式入库。

```bash
# 抓取5条随机定式（默认）
python3 db.py fetch-ogs

# 指定抓取数量
python3 db.py fetch-ogs --count 10

# 从指定起始节点抓取
python3 db.py fetch-ogs --start-node 15422 --start-node 24140
```

**抓取逻辑：**
1. 从空棋盘（节点15081）开始
2. 随机选择第一手（优先 IDEAL/GOOD 分类）
3. 自动选择后续着法（IDEAL > GOOD 优先级）
4. 过滤 pass 节点，只保留实际落子
5. 生成8向变化并入库

**依赖：** 需要安装 `requests` 库
```bash
pip install requests
```

## Python API

```python
from db import JosekiDB

# 初始化
db = JosekiDB()  # 使用默认路径 ~/.weiqi-joseki/database.json

# 添加定式
joseki_id, conflict = db.add(
    name="星位小飞挂一间低夹",
    category_path="/星位/小飞挂/一间低夹",
    moves=["B[pd]", "W[qf]", "B[nc]", ...]
)

# 检查冲突
conflict = db.check_conflict(moves)
if conflict.has_conflict:
    for s in conflict.similar_joseki:
        print(f"相似: {s['name']} ({s['similarity']})")

# 匹配定式
results = db.match(["pd", "qf", "nc", "rd"], top_k=5)
for r in results:
    print(f"{r.name}: {r.similarity:.2f}")

# 生成8向SGF ⭐
sgf = db.generate_8way_sgf("joseki_001")
with open("output.sgf", "w") as f:
    f.write(sgf)

# 识别棋谱四角
results = db.identify_corners(sgf_data, top_k=3)
for corner, matches in results.items():
    print(f"{corner}: {matches[0].name if matches else '无匹配'}")

# 从OGS抓取定式 🌐
# 抓取1条随机定式
moves, description = db.fetch_ogs_joseki_from_empty()

# 抓取指定节点开始的定式
moves, description = db._fetch_joseki_line("15422", max_moves=15)

# 批量抓取并自动入库
imported_ids = db.import_from_ogs(count=5)
print(f"成功导入 {len(imported_ids)} 条定式")
```

## 数据格式

### 定式条目
```json
{
  "id": "joseki_001",
  "name": "星位小飞挂一间低夹",
  "category_path": "/星位/小飞挂/一间低夹",
  "variations": [
    {"direction": "rdlu", "moves": ["pd", "qf", "nc", ...]},
    {"direction": "lurd", "moves": ["dd", "cf", "fc", ...]},
    ...
  ]
}
```

### 8个方向
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

## 依赖

- Python 3.6+
- 无第三方依赖（纯标准库）

### 可选依赖

- `requests` - 用于从OGS抓取定式（`pip install requests`）

## OGS 定式抓取详解

### 数据来源
数据来自 [OGS (Online-Go.com) Joseki Explorer](https://online-go.com/joseki/) 的开放 API。

### 常用起始节点

| 节点ID | 位置 | 说明 |
|--------|------|------|
| 15081 | root | 空棋盘（默认起始点）|
| 15422 | Q16 | 星位（4-4点）|
| 24140 | R16 | 星位（4-4点）|
| 24132 | D16 | 小目（3-4点）|

### API 响应示例
```json
{
  "node_id": "15422",
  "placement": "Q16",
  "description": "## 4-4 Point...",
  "category": "IDEAL",
  "next_moves": [
    {"placement": "R14", "category": "IDEAL", "node_id": "15467"},
    {"placement": "D16", "category": "IDEAL", "node_id": "24132"}
  ]
}
```

### 抓取策略
- **第一手**：从空棋盘的 `next_moves` 中随机选择（IDEAL/GOOD 优先）
- **后续手**：按 IDEAL > GOOD > 其他 的优先级自动选择
- **pass 处理**：自动过滤 pass 节点，只保留实际落子坐标

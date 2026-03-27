---
name: 星阵棋谱下载
description: weiqi-golaxy 星阵围棋棋谱下载 - 从星阵围棋(19x19.com)分享链接提取SGF棋谱。支持从移动端分享链接自动下载完整棋谱。
---

# 星阵棋谱下载

星阵围棋（Golaxy）是中国领先的围棋AI平台，提供在线对弈、棋谱分享等功能。本技能支持从星阵围棋分享链接提取完整SGF棋谱。

## 功能概述

- **分享链接提取** - 从星阵围棋H5分享链接提取完整SGF棋谱
- **自动元数据解析** - 提取玩家名、段位、对局结果、日期等信息
- **坐标转换** - 自动将星阵内部坐标转换为标准SGF格式

## 支持的URL格式

```
https://m.19x19.com/app/dark/zh/sgf/<ID>
https://www.19x19.com/app/dark/zh/sgf/<ID>
```

## 核心脚本

| 脚本 | 功能 |
|------|------|
| `download.py` | 主下载脚本，支持命令行调用 |

## 使用方法

### 命令行使用

```bash
cd /path/to/weiqi-golaxy/scripts

# 下载棋谱
python3 download.py "https://m.19x19.com/app/dark/zh/sgf/70307160"

# 指定输出文件
python3 download.py "https://m.19x19.com/app/dark/zh/sgf/70307160" /tmp/output.sgf
```

### 程序化使用

```python
from scripts.download import GolaxyDownloader

downloader = GolaxyDownloader()
result = downloader.download("https://m.19x19.com/app/dark/zh/sgf/70307160", "/tmp/game.sgf")

if result['success']:
    print(f"下载成功: {result['file']}")
    print(f"黑方: {result['metadata']['black']}")
    print(f"白方: {result['metadata']['white']}")
```

## 技术说明

### 数据来源

星阵围棋使用纯前端渲染（SPA），棋谱数据存储在浏览器的 `localStorage` 中：

```javascript
localStorage.getItem('engine')  // 包含棋谱JSON数据
```

### 数据格式

```json
{
  "sgf": "72,288,319,41,78,...",     // 坐标数组 (0-360)
  "sgfInfo": {
    "pb": {"value": "黑方名"},       // 黑方
    "pw": {"value": "白方名"},       // 白方
    "br": {"value": "7段"},          // 黑方段位
    "wr": {"value": "8段"},          // 白方段位
    "re": {"value": "W+R"},          // 结果
    "gn": {"value": "升降战"},        // 赛事
    "dt": {"value": "2025-10-17"},   // 日期
    "km": {"value": "7.5"}           // 贴目
  },
  "boardSize": 19
}
```

### 坐标转换

星阵坐标是数字索引 (0-360)，转换公式：
```
SGF坐标 = chr(ord('a') + val % 19) + chr(ord('a') + val // 19)
```

例如：
- `72` → `x=3, y=3` → `"pd"`
- `288` → `x=3, y=15` → `"dp"`

## 依赖

```bash
pip3 install playwright
playwright install chromium
```

## 安装

```bash
# 克隆到技能目录
cd ~/.openclaw/workspace
mkdir -p weiqi-golaxy/scripts

# 安装依赖
pip3 install playwright --break-system-packages
playwright install chromium
```

## 版本更新

### v1.0.0 (2026-03-27)
- ✅ 初始版本发布
- ✅ 支持从分享链接提取SGF棋谱
- ✅ 自动解析玩家信息、段位、结果
- ✅ 坐标自动转换为标准SGF格式

## 相关技能

- [weiqi-foxwq](./weiqi-foxwq) - 野狐围棋棋谱下载
- [weiqi-sgf](./weiqi-sgf) - SGF转HTML打谱网页
- [weiqi-db](./weiqi-db) - 围棋棋谱数据库

---

**免责声明**: 本工具仅供学习研究使用，请遵守星阵围棋的使用条款。

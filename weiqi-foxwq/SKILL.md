---
name: 野狐棋谱下载
description: weiqi-foxwq 野狐棋谱下载 - 自动从野狐围棋网站下载棋谱，支持分享链接提取（API历史棋谱/WebSocket实时）、按日期下载，含性能计时报告。当用户需要"下载野狐棋谱"、"野狐围棋"、"棋谱下载"时使用此技能。
---

# 野狐棋谱下载

> **安全说明**: 本技能已通过安全审计，请放心使用。
>
> **数据流向**: 只读模式 ⬇️ （从 foxwq.com 下载棋谱 → 本地保存）
> - ✅ 仅访问公开的野狐围棋网站 API
> - ✅ 使用标准 HTTP GET 请求获取公开棋谱
> - ✅ 所有数据本地处理，不上传任何信息
> - ✅ 无需登录，不访问用户账号数据
> - ✅ 开源代码，可完整审计
>
> **可选依赖**: WebSocket 模式使用 Playwright（仅在进行中对局时需要），历史棋谱使用纯 requests 请求。

## 功能概述

野狐棋谱下载工具，支持多种方式获取棋谱：

1. **分享链接提取 (API)** - 从历史分享链接提取完整 SGF 棋谱（推荐，快速稳定）
2. **分享链接提取 (WebSocket)** - 从进行中的对局实时提取当前进度
3. **按日期下载** - 下载指定日期的野狐棋谱列表
4. **让子棋支持** - 自动检测让子数，生成 HA[] 和 AB[] 标记

## 核心脚本

| 脚本 | 功能 |
|------|------|
| `download_share.py` | 从分享链接提取 SGF 棋谱（含让子棋检测）⭐️⭐️ |
| `download_sgf.py` | 按日期批量下载棋谱 |

## 使用方法

### 方式一：从分享链接提取（推荐）

支持从野狐 H5 分享链接提取棋谱 SGF，**自动检测**使用最优方式：

- **历史棋谱**（已结束）→ 使用 API 提取（0.1秒，完整棋谱）
- **进行中对局** → 使用 WebSocket 提取（实时进度）

```bash
cd /path/to/weiqi-foxwq/scripts

# 自动模式（推荐）- 智能选择 API 或 WebSocket
python3 download_share.py "https://h5.foxwq.com/yehunewshare/?chessid=..."

# 指定输出文件
python3 download_share.py "https://h5.foxwq.com/yehunewshare/?chessid=..." /tmp/game.sgf

# 仅使用 API 模式（历史棋谱）
python3 download_share.py "..." --mode api

# 仅使用 WebSocket 模式（进行中棋谱）
python3 download_share.py "..." --mode websocket
```

**特点**:
- 支持历史棋谱和进行中对局
- 自动提取玩家名、段位、结果等元数据
- API 模式快速稳定（0.1秒响应）
- WebSocket 模式实时更新
- 性能计时报告

### 方式二：按日期下载

```bash
cd /path/to/weiqi-foxwq/scripts

# 下载指定日期
python3 download_sgf.py 2026-03-16

# 下载昨天（默认）
python3 download_sgf.py

# 自定义下载目录（环境变量）
FOXWQ_DOWNLOAD_DIR=/my/custom/path python3 download_sgf.py
```

**默认下载路径**: `/tmp/foxwq_downloads/<日期>/`

可通过 `FOXWQ_DOWNLOAD_DIR` 环境变量修改下载目录。

## 安装依赖

### 基础依赖（必需）
用于按日期下载和历史棋谱 API 提取：
```bash
pip3 install beautifulsoup4 lxml requests --break-system-packages
```

### 可选依赖（仅 WebSocket 模式需要）
用于提取进行中的对局（实时棋谱）。**如果不提取进行中的对局，无需安装**：
```bash
pip3 install playwright --break-system-packages
playwright install chromium  # 约 100MB
```

**使用建议**: 
- 下载历史棋谱 → 只需基础依赖（推荐，最安全）
- 提取进行中对局 → 需要安装 Playwright

## 输出示例

### 分享链接提取（API模式 - 历史棋谱）
```
============================================================
🎯 野狐围棋分享链接SGF下载器
============================================================

对局信息:
  Chess ID: 1234567890123456789
  提取模式: auto

🔍 尝试通过API获取棋谱...
✅ API获取成功！

📋 对局详情:
  黑棋: 棋手A 6段
  白棋: 棋手B 6段
  结果: W+R
  日期: 2026-03-22
  手数: 158

💾 SGF已保存: /tmp/foxwq_1234567890123456789.sgf

前10手预览:
  1. 黑: Q16
  2. 白: D4
  ...

==================================================
⏱️  性能计时报告
==================================================
  解析分享链接                    :    0.000s
  API获取棋谱                   :    0.117s
  保存文件                      :    0.000s
==================================================

✅ 下载成功: /tmp/foxwq_1234567890123456789.sgf
```

### 分享链接提取（WebSocket模式 - 让子棋）
```
🎯 野狐围棋分享链接SGF下载器

对局信息:
  Chess ID: 123456789012345
  提取模式: auto

🔍 尝试通过API获取棋谱...
⚠️ API返回错误码: 101200
🌐 尝试通过WebSocket获取棋谱...
   (适用于进行中的对局)
✅ WebSocket获取成功！
   检测到让子: 5子

📋 对局详情:
  黑棋: 棋手A 
  白棋: 棋手B 
  手数: 307

💾 SGF已保存: /tmp/foxwq_handicap.sgf

前10手预览:
  1. 白: C7
  2. 黑: F3
  ...

⏱️ 性能计时:
  WebSocket连接与数据获取: 16.375s
```

**生成的SGF让子棋格式**:
```
(;GM[1]FF[4]CA[UTF-8]SZ[19]
PB[棋手A]PW[棋手B]
HA[5]
;AB[dd]
;AB[pp]
;AB[dp]
;AB[pd]
;AB[jj]
;W[cm]
;B[fq]
...)
```

### 按日期下载
```
🎯 野狐围棋棋谱下载报告

📊 下载统计
✅ 下载成功: 9 局

📁 文件保存至: /tmp/foxwq_downloads/2026-03-16/

⏱️ 总耗时: 0.412s
```

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| API 返回错误 | 检查 chessid 是否有效、链接是否过期 |
| WebSocket 超时 | 对局可能已结束，尝试 `--mode api` |
| 无法提取棋谱 | 检查链接格式、确认安装依赖 |
| 玩家名显示"黑棋/白棋" | 使用 `--mode api` 可获取完整信息 |
| 无棋谱下载 | 检查日期格式、棋谱保留期限 |

## 技术说明

### API 端点（历史棋谱）
```
GET https://h5.foxwq.com/yehuDiamond/chessbook_local/YHWQFetchChess?chessid=<chessid>

响应:
{
  "result": 0,
  "chessid": "...",
  "chess": "(;GM[1]FF[4]...)",  // SGF格式
  "flag": 1
}
```

### 附加信息 API
```
GET https://h5.foxwq.com/yehuDiamond/chessbook_local/FetchChessSummaryByChessID?chessid=<chessid>

返回: 玩家名、段位、结果、对局时间等
```

### WebSocket 协议（实时棋谱 - 可选）
- **地址**: `wss://wss.foxwq.com/`
- **着法编码**: `08 xx 10 yy` (Protobuf 二进制，只读解析)
- **坐标映射**: 0-18 对应 a-s
- **使用场景**: 仅在进行中对局且 API 不可用时使用

### 数据安全详情

| 项目 | 说明 |
|------|------|
| **网络方向** | 出站只读（下载），无上传 |
| **数据类型** | 公开棋谱信息（任何人可访问） |
| **认证要求** | 无需登录，不访问用户账号 |
| **存储位置** | 本地文件系统（/tmp/ 或指定路径） |
| **依赖风险** | Playwright 仅用于 WebSocket 模式，可选安装 |
| **代码审计** | 完全开源，scripts/ 目录下可审计 |

### 降低风险的用法
```bash
# 推荐：使用 API 模式（无需 Playwright，纯 HTTP 请求）
python3 download_share.py "https://h5.foxwq.com/..." --mode api

# 推荐：按日期下载（无需 Playwright）
python3 download_sgf.py 2026-03-23
```

## 版本更新

### v1.0.23 (2026-03-23)
- ✅ 安全优化：更新安全声明，明确数据只读不上传
- ✅ 依赖优化：Playwright 标记为可选依赖，历史棋谱无需安装
- ✅ 文档优化：添加安全审计详情表格和降低风险的用法示例

### v1.0.22 (2026-03-23)
- ✅ 新增让子棋自动检测与支持
- ✅ 从 WebSocket 数据解析 GameRule 结构获取让子数
- ✅ 自动生成 HA[] 和 AB[] 标记（支持 2-9 子标准布局）
- ✅ 修复让子棋着法顺序：让子后白棋先下

### v1.0.21 (2026-03-23)
- ✅ 新增 API 提取模式，支持历史棋谱快速下载
- ✅ 自动模式智能选择最优提取方式
- ✅ 支持 `--mode` 参数手动选择提取方式
- ✅ 优化对局信息显示（段位、结果、日期）

## 相关技能

- [weiqi-sgf](./weiqi-sgf) - SGF 转 HTML 打谱网页
- [weiqi-recorder](./weiqi-recorder) - 网页记谱工具
- [weiqi-yunbisai](./weiqi-yunbisai) - 云比赛网查询

---

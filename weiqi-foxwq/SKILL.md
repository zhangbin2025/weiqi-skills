---
name: weiqi-foxwq
description: weiqi-foxwq 野狐棋谱下载 - 自动从野狐围棋网站下载棋谱，支持指定日期下载或从分享链接实时提取，含性能计时报告。当用户需要"下载野狐棋谱"、"野狐围棋"、"棋谱下载"时使用此技能。
---

# 野狐棋谱下载

> **⚠️ 安全提示**: 本技能被 ClawHub 标记为 suspicious（可疑），原因如下：
> 1. **网络连接** - 技能需要连接野狐围棋 WebSocket (`wss://wss.foxwq.com/`)
> 2. **协议解析** - 解析了野狐围棋的 Protobuf 二进制协议
> 3. **外部数据** - 从第三方网站 (foxwq.com) 提取公开棋谱数据
>
> **安全声明**: 本技能仅访问公开的野狐围棋网站，使用标准 HTTP/WebSocket 请求获取公开棋谱信息，不涉及任何敏感操作或未经授权的访问。所有代码开源可审计。

## 功能概述

野狐棋谱下载工具，支持两种方式获取棋谱：

1. **分享链接提取** - 从野狐 H5 分享链接实时提取棋谱（支持进行中的对局）
2. **按日期下载** - 下载指定日期的野狐棋谱列表

## 核心脚本

| 脚本 | 功能 |
|------|------|
| `download_share.py` | 从分享链接提取 SGF 棋谱 ⭐️ |
| `download_sgf.py` | 按日期批量下载棋谱 |

## 使用方法

### 方式一：从分享链接提取（推荐）

支持从野狐 H5 分享链接直接提取棋谱 SGF，**无需对局结束**，实时获取当前进度。

```bash
cd /path/to/weiqi-foxwq/scripts

# 基本用法
python3 download_share.py "https://h5.foxwq.com/yehunewshare/?roomid=..."

# 指定输出文件
python3 download_share.py "https://h5.foxwq.com/yehunewshare/?roomid=..." /tmp/game.sgf
```

**特点**:
- 实时提取进行中的对局
- 自动提取玩家名、头像等元数据
- 性能计时报告

### 方式二：按日期下载

```bash
cd /path/to/weiqi-foxwq/scripts

# 下载指定日期
python3 download_sgf.py 2026-03-16

# 下载昨天（默认）
python3 download_sgf.py
```

## 安装依赖

```bash
# 基础依赖（按日期下载）
pip3 install beautifulsoup4 lxml requests --break-system-packages

# 分享链接提取需要 Playwright
pip3 install playwright --break-system-packages
playwright install chromium  # 约 100MB
```

## 输出示例

### 分享链接提取
```
🎯 野狐围棋分享链接SGF提取器
对局信息:
  Room ID: 12345
  Chess ID: 123456789012345

✅ 成功提取棋谱!
  总手数: 186 手
  黑棋: 棋手A
  白棋: 棋手B

💾 SGF已保存: /tmp/foxwq_12345.sgf

⏱️ 性能计时:
  WebSocket连接与数据获取: 16.345s
```

### 按日期下载
```
🎯 野狐围棋棋谱下载报告

📊 下载统计
✅ 下载成功: 9 局

📁 文件保存至: ./downloads/2026-03-16/

⏱️ 总耗时: 0.412s
```

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| 无法提取棋谱 | 检查链接格式、确认安装 Playwright |
| WebSocket 超时 | 增加 `--timeout 30` 参数 |
| 玩家名显示"黑棋/白棋" | 不影响使用，SGF 文件正常 |
| 无棋谱下载 | 检查日期格式、棋谱保留期限 |

## 技术说明

- **WebSocket 协议**: `wss://wss.foxwq.com/`
- **着法编码**: `08 xx 10 yy` (Protobuf 二进制)
- **坐标映射**: 0-18 对应 a-s
- **数据安全**: 仅读取公开数据，不上传任何信息

## 相关技能

- [weiqi-sgf](./weiqi-sgf) - SGF 转 HTML 打谱网页
- [weiqi-recorder](./weiqi-recorder) - 网页记谱工具
- [weiqi-yunbisai](./weiqi-yunbisai) - 云比赛网查询

---

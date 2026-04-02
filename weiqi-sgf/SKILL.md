---
name: 围棋打谱工具
description: weiqi-sgf SGF围棋棋谱转HTML打谱工具 - 将棋谱文件生成可在浏览器中交互回放的网页，支持播放/暂停/手数跳转/变化图查看。当用户需要"SGF转网页"、"打谱"、"棋谱查看"时使用此技能。
tags: ["围棋", "weiqi", "go", "棋谱", "SGF", "打谱", "HTML", "网页"]
---

# SGF 围棋打谱网页生成器

## 🔒 安全说明

本技能是一个**纯本地离线工具**，具有以下安全特性：

| 安全项 | 说明 |
|--------|------|
| **网络访问** | ❌ 无任何网络请求，完全离线运行 |
| **文件系统** | 仅读取输入的SGF文件，写入输出的HTML文件到指定目录 |
| **依赖项** | 仅使用Python标准库 (`sys`, `re`, `os`, `json`, `html`) |
| **XSS防护** | ✅ 所有SGF元数据（棋手名、棋局名、赛果等）均使用 `html.escape()` 转义 |
| **JS注入防护** | ✅ 嵌入JavaScript的JSON数据经 `json.dumps()` + `html.escape()` 双重转义 |

**代码审计要点**：
- 脚本中没有任何 `import urllib`、`import http`、`import socket` 等网络相关导入
- 所有用户输入数据（SGF内容）在嵌入HTML模板前均经过转义处理
- 生成的HTML为单文件静态页面，不包含任何外部资源引用


## 功能描述
根据 SGF 格式的围棋棋谱数据，生成一个单文件 HTML 网页，支持本地浏览器打开进行交互式打谱。

## 依赖
**无第三方依赖** - 使用 Python 标准库（sys, re, os, json, html）

## 核心文件

| 文件 | 功能 |
|------|------|
| `scripts/replay.py` | SGF 转 HTML 主脚本 ⭐️ |
| `scripts/sgf_parser.py` | SGF 解析模块（支持多种格式） |
| `scripts/templates/replay.html` | HTML 页面模板 |

## 网页功能

### 基础功能
- [x] 可视化 19路围棋棋盘
- [x] 黑白双方棋子显示（立体渐变效果）
- [x] 完整的围棋规则实现（提子、气数计算）
- [x] **响应式设计，支持手机/平板/桌面端**
- [x] 坐标标签显示（A-T横向，1-19纵向）

### 打谱控制
- [x] 播放 / 暂停（自动播放，0.8秒/手）
- [x] 上一手 / 下一手（方向键支持，触屏滑动支持）
- [x] 进度条滑动跳转（任意手数定位）
- [x] **AI变化图浏览**（支持野狐围棋的多分支变化图）

### 显示选项
- [x] 手数显示开关（默认关闭）
- [x] 最后一步标识（不显示手数时显示圆点标记）
- [x] 提子数量统计

### 音效系统 🆕
- [x] 落子音效 - 清脆的"嗒"声
- [x] 吃子音效 - 提子时的"啪"声
- [x] 多颗提子音效 - 连珠炮般的回响效果
- [x] 音效开关 - 可随时开启/关闭

### 导出功能
- [x] SGF 文件下载按钮

## 使用方法

### 1. 使用脚本生成网页（推荐）
```bash
cd scripts
python3 replay.py <输入.sgf> [输出.html]
```

**示例**：
```bash
python3 replay.py game.sgf
python3 replay.py game.sgf mygame.html
```

### 2. 本地查看
直接用浏览器打开生成的 HTML 文件即可。

### 3. 操作方式

**桌面端：**
- `←` / `→`：上一手 / 下一手
- `空格`：播放 / 暂停

**移动端：**
- 在棋盘上**向左滑动**：下一手
- 在棋盘上**向右滑动**：上一手
- 点击按钮控制播放

## 界面说明

### 主控制面板

| 按钮 | 功能 |
|------|------|
| ◀ | 上一手 |
| 滑动条 | 进度跳转（0 ~ 总手数） |
| ▶ | 下一手 |
| 🔊/🔇 | 音效开关 |
| 1️⃣ | 手数显示开关 |
| 💾 | 下载SGF |
| 播/⏸ | 播放 / 暂停 |

### 变化图面板（如有AI变化图）

当棋谱包含AI变化图时（如野狐围棋棋谱），当前手有变化图会显示：

- **变化图列表**：显示胜率按钮（如"黑62%"），点击进入该变化
- **变化图控制面板**：
  - ◀ 变化图上一步
  - ✕ 退出变化图
  - ▶ 变化图下一步

**变化图浏览特性：**
- 进入变化图默认显示第一手变化
- 变化图棋子显示手数标记（1, 2, 3...）
- 变化图模式下主分支棋子不显示手数，避免混淆

## 技术实现

### SGF解析（支持野狐围棋格式）
使用 `sgf_parser.py` 模块解析多种SGF格式：

**支持的格式：**
- 标准单分支格式: `(;GM...;B[pd];W[pp]...)`
- 嵌套格式（野狐原始）：多行，每行一个分支
- 平面格式（已清理）：所有着法在一行，用分号分隔
- 多变化图格式 (MULTIGOGM): `(;GM... (;变化1)(;变化2)...)`

**使用方法：**
```python
from sgf_parser import parse_sgf

main_moves, variations, game_info, parse_info = parse_sgf(sgf_content)
```

**返回数据：**
- `main_moves`: 主分支着法列表
- `variations`: 变化图数据（按手数索引）
- `game_info`: 棋局信息（棋手、日期、结果等）
- `parse_info`: 解析元数据（使用的解析器、警告、错误等）

### 变化图处理
- 自动检测野狐围棋的AI变化图分支
- 提取胜率信息作为变化图名称
- 支持在变化图内独立浏览

### 响应式适配
- 棋盘尺寸根据屏幕宽度自动调整
- 手机端（<768px）：最大化棋盘，紧凑控制面板
- 平板端（768-900px）：适中布局
- 桌面端（>900px）：标准布局

### 触摸优化
- 禁用双击缩放
- 触控滑动切换手数（左滑下一手，右滑上一手）
- 按钮点击反馈

### 核心算法
```javascript
// 棋串检测
getGroup(board, x, y, color)

// 气数计算
getLiberties(board, x, y, color)

// 提子执行
captureStones(board, x, y, moveColor)
```

### 棋盘渲染
- Canvas 2D 绘图
- 径向渐变实现棋子立体感
- 动态重绘支持任意手数跳转

### 音效系统
使用 Web Audio API 实时生成音效，无需外部音频文件：

```javascript
// 落子音效 - 短促的"嗒"声
oscillator.frequency.setValueAtTime(800, audioCtx.currentTime);
oscillator.frequency.exponentialRampToValueAtTime(400, audioCtx.currentTime + 0.05);

// 吃子音效 - 清脆的"啪"声  
oscillator.frequency.setValueAtTime(1200, audioCtx.currentTime);
oscillator.frequency.exponentialRampToValueAtTime(600, audioCtx.currentTime + 0.08);

// 多颗提子音效 - 连珠炮效果
for (let i = 0; i < count; i++) {
    // 依次触发多个音调递减的短音
}
```

**特点：**
- 纯浏览器生成，无需网络加载音频文件
- 响应式触发：前进时播放，后退时不播放
- 区分音效：落子、提子、多颗提子各有不同音效

## 使用指令
> "把 xxx.sgf 生成打谱网页"
> "用 replay.html 查看这盘棋"
> "生成一个围棋打谱页面"

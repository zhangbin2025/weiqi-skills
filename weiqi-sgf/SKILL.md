---
name: 围棋打谱工具
description: weiqi-sgf SGF围棋棋谱转HTML打谱工具 - 将棋谱文件生成可在浏览器中交互回放的网页，支持播放/暂停/手数跳转/变化图查看。当用户需要"SGF转网页"、"打谱"、"棋谱查看"时使用此技能。
tags: ["围棋", "weiqi", "go", "棋谱", "SGF", "打谱", "HTML", "网页"]
---

# SGF 围棋打谱网页生成器

> **🔒 安全说明**: 本技能为纯本地处理工具，将 SGF 棋谱文件转换为 HTML 网页。无需网络连接，所有处理在本地完成，不涉及任何外部请求或数据传输。SGF 是开放标准格式。
>
> **v1.1.2 安全更新**: 已修复潜在 XSS 漏洞，所有 SGF 元数据（棋手名、棋局名等）在嵌入 HTML 前均进行转义处理。建议使用可信来源的 SGF 文件。


## 功能描述
根据 SGF 格式的围棋棋谱数据，生成一个单文件 HTML 网页，支持本地浏览器打开进行交互式打谱。

## 依赖
**无第三方依赖** - 使用 Python 标准库（sys, re, os, json）

## 核心文件

| 文件 | 功能 |
|------|------|
| `scripts/replay.py` | SGF 转 HTML 脚本 ⭐️ |

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

## 技术实现

### SGF解析（支持野狐围棋格式）
野狐围棋的SGF使用线性嵌套格式保存变化图：
```
(;B[qd](;W[pp](;B[dc]...   主分支
         (;W[dd]...       变例1
         (;W[de]...))      变例2
```

**解析逻辑：**
```python
# 1. 计算每手深度
for match in re.finditer(r';([BW])\[([a-z]{2})\]', sgf):
    pos = match.start()
    depth = 0
    for j in range(pos):
        if sgf[j] == '(': depth += 1
        elif sgf[j] == ')': depth -= 1

# 2. 按深度分组
depth_groups = {}
for m in moves:
    depth_groups.setdefault(m['depth'], []).append(m)

# 3. 提取主分支：depth连续递增，每个depth只有一个着法
main_moves = []
prev_depth = 0
for d in sorted(depth_groups.keys()):
    group = depth_groups[d]
    if d == prev_depth + 1:
        main_moves.append(group[0])  # 取第一个
        prev_depth = d
        if len(group) > 1:  # 有多个着法，后续都是变化图
            break

# 4. 重要：不去重！
# 围棋中棋子可被提掉，同一位置可再次下子
```

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

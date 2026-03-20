---
name: weiqi-sgf
description: SGF围棋棋谱转HTML打谱工具 - 将棋谱文件生成可在浏览器中交互回放的网页，支持播放/暂停/手数跳转。当用户需要"SGF转网页"、"打谱"、"棋谱查看"时使用此技能。
---

# SGF 围棋打谱网页生成器

## 功能描述
根据 SGF 格式的围棋棋谱数据，生成一个单文件 HTML 网页，支持本地浏览器打开进行交互式打谱。

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

### 打谱控制
- [x] 播放 / 暂停（自动播放）
- [x] 上一手 / 下一手（方向键支持，触屏滑动支持）
- [x] 跳到开头 / 结尾
- [x] 播放速度调节（0.2~2.0秒/手）

### 显示选项
- [x] 手数显示开关（默认关闭）
- [x] 最后一步标识（黑棋显示白点，白棋显示黑点）
- [x] 提子数量统计

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

按钮采用**纯图标设计**，无文字说明：

| 图标 | 功能 |
|------|------|
| ⏮ | 跳到开头 |
| ◀ | 上一手 |
| ▶ / ⏸ | 播放 / 暂停 |
| ▶ | 下一手 |
| ⏭ | 跳到结尾 |
| 💾 | 下载SGF |

## 技术实现

### SGF解析（支持野狐围棋格式）
野狐围棋的SGF使用线性嵌套格式保存变化图：
```
(;B[qd](;W[pp](;B[dc]...   主分支
         (;W[dd]...       变例1
         (;W[de]...))      变例2
```

**解析逻辑（关键改进）：**
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

**学到的要点：**
- 主分支判断：depth连续递增 + 每个depth只有一个着法
- 最后一手：当某个depth有多个着法时，取第一个后停止
- 不硬编码手数限制（不同棋局手数不同：188手、249手等）

### 响应式适配
- 棋盘尺寸根据屏幕宽度自动调整
- 手机端（<600px）：紧凑布局，大触控按钮
- 平板端（600-900px）：适中布局
- 桌面端（>900px）：标准布局

### 触摸优化
- 禁用双击缩放
- 触控滑动切换手数
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

## 示例棋谱
当前内置棋谱：示例比赛对局
- 黑方：棋手A (9段)
- 白方：棋手B (6段)
- 结果：白中盘胜

## 使用指令
> "把 xxx.sgf 生成打谱网页"
> "用 replay.html 查看这盘棋"
> "生成一个围棋打谱页面"
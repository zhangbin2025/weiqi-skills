---
name: KataGo围棋分析
description: weiqi-katago KataGo围棋AI分析工具 - 零捆绑、硬件自适应的围棋复盘分析技能包。支持棋谱评估、胜率分析、恶手检测。用户需自行安装KataGo和模型。
tags: ["围棋", "weiqi", "go", "KataGo", "AI分析", "胜率", "恶手检测", "复盘"]
---

# weiqi-katago

KataGo 围棋分析工具 - 零捆绑、硬件自适应的围棋AI分析技能包。

## 设计原则

- **零捆绑**：不携带任何可执行文件、模型或配置
- **用户自主**：用户自行安装 KataGo 和模型，技能包负责检测和调用
- **硬件自适应**：自动检测硬件配置，推荐合适的模型并预估运行时间

## 前置要求

### 1. 安装 KataGo

技能包会自动检测并提供最新版本的下载链接。

**Linux:**
```bash
# 运行检测获取最新版本下载链接
weiqi-katago setup

# 或使用以下命令下载（链接会自动更新到最新版）
wget "https://github.com/lightvector/KataGo/releases/download/v1.16.4/katago-v1.16.4-eigenavx2-linux-x64.zip" -O katago.zip
unzip katago.zip
sudo mv katago /usr/local/bin/
rm katago.zip

# 验证安装
katago version
```

> **注意**: 如果下载失败，请检查网络连接或稍后再试。技能包**只通过 GitHub 官方渠道**获取 KataGo。

**macOS:**
```bash
brew install katago
```

**Windows:**
```powershell
scoop install katago
```

### 2. 下载模型

**根据硬件配置选择模型：**

| 硬件配置 | 最大模型大小 | 推荐模型 | 大小 | 下载命令 |
|---------|-------------|---------|------|---------|
| 低配 (2核/4GB) | 50MB | Lionffen b6c64 | **2.1MB** | `wget "https://media.katagotraining.org/uploaded/networks/models_extra/lionffen_b6c64_3x3_v10.txt.gz"` |
| 低配 (2核/4GB) | 50MB | g170 b6c96 | **3.8MB** | `wget "https://katagoarchive.org/g170/neuralnets/g170-b6c96-s175395328-d26788732.bin.gz"` |
| 中配 (4核/8GB) | 300MB | g170 b10c128 | 11MB | `wget "https://katagoarchive.org/g170/neuralnets/g170-b10c128-s197428736-d67404019.bin.gz"` |
| 高配 (8核+/16GB+) | 1000MB | b18c384/b28c512 | 300MB+ | 需从 katagotraining.org/networks/ 下载 |

**⚠️ 重要提示**: 
- 模型过大会导致分析缓慢或内存不足
- 技能包会自动检测模型大小并警告不适合的模型
- **低端CPU环境强烈推荐使用轻量模型 (≤50MB)**

**模型来源说明：**
- **katagotraining.org/extra_networks/** - 实验性轻量模型（Lionffen 等）
- **katagoarchive.org/g170/** - KataGo 历史版本（g170 代，有官方轻量模型）
- **katagotraining.org/networks/** - 当前标准模型（较大，适合高配）

**快速下载（低配推荐）:**
```bash
# 方案1: Lionffen b6c64 (2.1MB，19x19专用优化)
wget "https://media.katagotraining.org/uploaded/networks/models_extra/lionffen_b6c64_3x3_v10.txt.gz" -O lionffen_b6c64.txt.gz

# 方案2: g170 b6c96 (3.8MB，KataGo官方历史版本)
wget "https://katagoarchive.org/g170/neuralnets/g170-b6c96-s175395328-d26788732.bin.gz"

# 方案3: g170 b10c128 (11MB，质量稍好)
wget "https://katagoarchive.org/g170/neuralnets/g170-b10c128-s197428736-d67404019.bin.gz"
```

### 3. 检测环境

```bash
weiqi-katago setup
```

## 硬件与模型选择

| 硬件配置 | 模型大小限制 | 推荐模型 | 大小 | 预估速度 | 质量 | 适用性 |
|---------|-------------|---------|------|---------|------|-------|
| GPU 6GB+ VRAM | 1000MB | b28c512nbt | 1.0GB | ~5秒/手 | ★★★★★ | 深度分析 |
| GPU 4GB VRAM | 300MB | b18c384nbt | 300MB | ~3秒/手 | ★★★★☆ | 平衡选择 |
| CPU 8核 16GB | 300MB | b18c384nbt | 300MB | ~15秒/手 | ★★★★☆ | 标准分析 |
| CPU 4核 8GB | 50MB | **Lionffen b6c64** | **2.1MB** | **~2秒/手** | ★★☆☆☆ | **低端首选** |
| 低配CPU (2核/4GB) | 50MB | **Lionffen b6c64** | **2.1MB** | **~2秒/手** | ★★☆☆☆ | **低端首选** |

> **重要**: 模型超过硬件限制时，技能包会发出警告。超大模型在低端配置下可能导致分析时间超过 10 分钟/手或内存溢出。

### 预估时间公式

```
200手棋谱 + b18c384nbt + CPU 8核 ≈ 50分钟
使用 --interval 5 可缩短至 10分钟
```

## 命令参考

### setup - 环境检测

检测 KataGo 安装状态，输出硬件信息和安装指引。

```bash
weiqi-katago setup
```

生成优化配置：
```bash
weiqi-katago setup --generate-config
```

### eval - 单局面评估

评估指定局面，输出胜率、目差、推荐点。

```bash
# 评估最后一手后的局面
weiqi-katago eval game.sgf

# 评估第50手后的局面
weiqi-katago eval game.sgf --move 50

# 输出JSON格式
weiqi-katago eval game.sgf --quiet
```

**输出示例：**
```
第 50 手评估 (白棋落子)
==================================================
当前胜率: 48.2% (黑棋稍优)
目差: B+1.5

白棋推荐点 Top 5:
--------------------------------------------------
✓ 1. K4     (54.3%, B-0.5) → Q16 → D4 → R4
  2. C10    (53.1%, B-0.2)
  3. R12    (52.8%, B-0.1)
```

### analyze - 完整棋谱分析

分析整盘棋，生成胜率曲线和HTML报告。

```bash
# 完整分析（默认输出文本摘要）
weiqi-katago analyze game.sgf

# 每5手分析一次（加快整体速度）
weiqi-katago analyze game.sgf --interval 5

# 生成HTML可视化报告
weiqi-katago analyze game.sgf --output html

# 指定范围分析
weiqi-katago analyze game.sgf --start 20 --end 100

# 输出JSON
weiqi-katago analyze game.sgf --output json --output-file result.json
```

**HTML报告包含：**
- 胜率变化曲线图
- 棋盘关键手数标注
- 恶手列表
- 推荐变化图

### mistakes - 恶手检测

自动标记胜率骤降点。

```bash
# 默认阈值 5%
weiqi-katago mistakes game.sgf

# 自定义阈值
weiqi-katago mistakes game.sgf --threshold 10

# 显示前20个恶手
weiqi-katago mistakes game.sgf --top 20
```

**输出示例：**
```
发现 3 处恶手 (胜率下降 >5%)
==================================================

1. 🔴 严重 第47手 黑棋[QF]
   胜率变化: 52% → 44% (-8%)
   AI推荐: QG

2. 🟠 重大 第89手 白棋[NC]
   胜率变化: 48% → 36% (-12%)
   AI推荐: ND
```

## 典型工作流

### 1. 快速评估局面

```bash
weiqi-katago eval game.sgf
```

### 2. 完整复盘分析

```bash
# 生成可视化报告
weiqi-katago analyze game.sgf --output html

# 浏览器打开生成的 HTML 文件
```

### 3. 重点查看失误

```bash
weiqi-katago mistakes game.sgf --threshold 5
```

### 4. 批量处理

```bash
for f in *.sgf; do
    weiqi-katago analyze "$f" --interval 10 --output html
done
```

## 与其他技能包集成

```bash
# 下载野狐棋谱 → 分析
weiqi-foxwq download --date yesterday
weiqi-katago analyze qipu/*.sgf --output html

# 分析后查看
weiqi-sgf view analysis.html
```

## 模型效果对比

| 模型 | 推荐一致性 | 胜率准确度 | 变化图深度 | 适用场景 |
|------|-----------|-----------|-----------|---------|
| b28c512 | 基准 | 基准 | 20+手 | 深度复盘 |
| b18c384 | 95% | ±2% | 15手 | 日常分析 |
| b10c128 | 75% | ±5% | 8手 | 快速分析 |
| b6c64 | 60% | ±12% | 5手 | 教学演示 |

## 常见问题

### Q: KataGo 未检测到
A: 确保 `katago` 命令在 PATH 中，或放在以下位置：
- `/usr/local/bin/katago`
- `/usr/bin/katago`
- `~/.local/bin/katago`
- `~/katago`

### Q: 模型下载慢
A: 可使用镜像或下载工具：
```bash
# 使用 axel 多线程下载
axel -n 10 https://katago-training.ubuntu.com/networks/kata1-b18c384nbt-s9996604416-d4316490686.bin.gz
```

### Q: 分析速度慢 / 内存不足
A: 模型可能太大，请检查模型大小：

```bash
# 查看模型大小
ls -lh ~/lionffen*.txt.gz

# 如果模型超过 50MB（低配）或 300MB（中配），请下载小模型：
wget "https://media.katagotraining.org/uploaded/networks/models_extra/lionffen_b6c64_3x3_v10.txt.gz"

# 或降低分析密度
weiqi-katago analyze game.sgf --interval 5
```

### Q: KataGo 下载失败
A: 技能包只通过 GitHub 官方渠道下载。如果失败：
1. 检查网络连接
2. 稍后再试
3. 或手动从 https://github.com/lightvector/KataGo/releases/latest 下载

### Q: GPU 无法使用
A: 检查 CUDA 安装：
```bash
nvidia-smi
```
如无法使用，将自动降级到 CPU 模式。

## 技术细节

### KataGo 调用方式

使用 Analysis Engine（JSON 输入输出）：
```bash
katago analysis -config analysis.cfg -model model.bin.gz
```

### 胜率计算

- KataGo 输出为黑棋视角胜率
- 白棋胜率 = 100% - 黑棋胜率
- 胜率变化计算考虑当前执子方

### 恶手判定

- 胜率下降超过阈值（默认 5%）
- 严重程度分级：
  - minor: 5-10%
  - significant: 10-15%
  - critical: >15%

## 版本信息

- 技能包: weiqi-katago
- 支持 KataGo: v1.12+
- 推荐模型: kata1 系列

## 相关链接

- KataGo 官方: https://github.com/lightvector/KataGo
- 模型下载: https://katago-training.ubuntu.com/
- 其他围棋技能: weiqi-sgf, weiqi-db, weiqi-joseki

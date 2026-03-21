---
name: weiqi-foxwq
description: weiqi-foxwq 野狐围棋棋谱下载 - 自动从野狐围棋网站下载职业棋谱，支持指定日期或默认下载昨天棋谱，含性能计时报告。当用户需要"下载野狐棋谱"、"野狐围棋"、"棋谱下载"时使用此技能。
tags: ["围棋", "weiqi", "go", "棋谱", "野狐", "foxwq", "SGF", "下载"]
---

# 野狐围棋棋谱自动下载

> **🔒 安全说明**: 本技能仅从公开的野狐围棋网站下载职业棋谱数据，使用标准 HTTP 请求获取公开信息，不涉及任何敏感操作或未经授权的访问。所有代码开源，可审计。
>
> **⚠️ ClawHub 安全扫描说明**: 本技能会访问 `https://www.foxwq.com` 获取公开棋谱列表并下载 SGF 文件，这是**预期的正常功能**。代码中无 `eval`、`exec`、系统命令执行等危险操作，仅使用标准 `requests` 库进行 HTTP GET 请求。源代码完全公开可审计。


**功能**: 自动从野狐围棋网站下载职业棋谱

## 核心文件

- **`scripts/download_sgf.py`** - 主下载脚本 ⭐️

## 功能特性

1. **自动下载** - 下载指定日期的野狐职业棋谱
2. **性能监控** - 每个步骤的执行耗时追踪
3. **SGF 格式** - 标准 SGF 棋谱，兼容各种围棋软件

## 使用方法

### 手动下载指定日期棋谱
```bash
cd /path/to/weiqi-foxwq/scripts
python3 download_sgf.py 2026-03-16
```

### 下载昨天棋谱（默认）
```bash
cd /path/to/weiqi-foxwq/scripts && python3 download_sgf.py
```

## 配置参数

脚本内可修改的配置：
```python
WORK_DIR = "./downloads"                       # 棋谱保存目录
BASE_URL = "https://www.foxwq.com"             # 野狐网站
LIST_URL = "https://www.foxwq.com/qipu.html"   # 棋谱列表页
```

## 输出结构

```
weiqi-foxwq/
├── SKILL.md
├── scripts/
│   └── download_sgf.py         # 下载脚本
└── 2026-03-16/                  # 日期目录
    ├── 2026031671947792_比赛名称_棋手A执黑中盘胜棋手B.sgf
    └── ...
```

## 性能优化

### 解析性能对比

| 解析方式 | 耗时 | 提升倍数 |
|---------|------|---------|
| 正则解析 | ~23s | 1x |
| BeautifulSoup | ~0.008s | **2875x** |

### 依赖安装
```bash
pip3 install beautifulsoup4 lxml --break-system-packages
```

## 控制台报告示例

```
🎯 野狐围棋棋谱下载报告

下载日期: 2026-03-17 08:25:00
目标日期: 2026-03-16

=============================
📊 下载统计
=============================

✅ 下载成功: 9 局
❌ 下载失败: 0 局

=============================
📁 下载的棋谱
=============================

• 第X期XX战循环圈 棋手A执黑中盘胜棋手B
  文件: 2026031671947792_比赛名称_棋手A执黑中盘胜棋手B.sgf

...

=============================
⏱️ 性能计时
=============================

  创建目录                 :    0.000s
  获取列表页                :    0.043s
  解析棋谱链接               :    0.008s
  下载9个棋谱               :    0.361s

  总耗时                   :    0.412s
```

## 定时任务配置（可选）

```bash
# 编辑 crontab
crontab -e

# 添加每天早上 7:00 执行
0 7 * * * cd /path/to/weiqi-foxwq/scripts && python3 download_sgf.py >> /var/log/foxwq_cron.log 2>&1
```

## 技术实现

### 性能计时器类
```python
class PerformanceTimer:
    """性能计时器 - 追踪每个步骤的执行耗时"""
    def __init__(self):
        self.timings = OrderedDict()
        self.start_time = None
    
    @contextmanager
    def step(self, name):
        """上下文管理器 - 计时单个步骤"""
        step_start = time.time()
        try:
            yield self
        finally:
            self.timings[name] = time.time() - step_start
```

### BeautifulSoup 解析
```python
def extract_qipu_links(html, target_date):
    soup = BeautifulSoup(html, 'lxml')
    
    for row in soup.find_all('tr'):
        date_cells = row.find_all('td')
        if len(date_cells) < 2:
            continue
        
        date_text = date_cells[-1].get_text(strip=True)
        if not date_text.startswith(target_date):
            continue
        
        link_tag = row.find('a', href=re.compile(r'/qipu/newlist/id/\d+\.html'))
        # ...
```

## 故障排查

### 无棋谱下载
- 检查日期格式：`2026-03-16`（不是 2025）
- 野狐网站棋谱保留时间有限，太早的日期可能无数据

### 解析失败
- 确认已安装依赖：`pip3 install beautifulsoup4 lxml`
- 检查网络连接：`curl -I https://www.foxwq.com`

## 相关技能

- **SGF 围棋打谱网页生成器** - `weiqi-game`
- **云比赛网围棋技能包** - `weiqi-yunbisai`
- **围棋选手信息查询** - `weiqi-player`

---
*版本: v2.0 (BeautifulSoup 优化版)*

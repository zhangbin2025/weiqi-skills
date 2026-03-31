# 围棋技能包集合 (Weiqi Skills)

一个围棋相关的 OpenClaw Agent Skills 集合，包含棋谱下载、棋手查询、记谱工具等功能。

## 技能包列表

| 技能包 | 功能 | 版本 |
|--------|------|------|
| [weiqi-db](weiqi-db/) | 围棋棋谱数据库 | 1.0.1 |
| [weiqi-fetcher](weiqi-fetcher/) | 分享棋谱下载器 | 1.1.1 |
| [weiqi-foxwq](weiqi-foxwq/) | 野狐棋谱下载 | 1.1.1 |
| [weiqi-joseki](weiqi-joseki/) | 围棋定式数据库 | 1.1.0 |
| [weiqi-player](weiqi-player/) | 棋手等级分/段位查询 | 1.0.9 |
| [weiqi-recorder](weiqi-recorder/) | 网页记谱工具 | 1.0.6 |
| [weiqi-sgf](weiqi-sgf/) | SGF转HTML打谱网页 | 1.2.2 |
| [weiqi-yunbisai](weiqi-yunbisai/) | 云比赛网比赛查询 | 1.1.2 |

## 快速开始

每个技能包都是独立的，可以直接使用。进入对应目录查看 `SKILL.md` 获取详细使用说明。

### 安装方式

通过 [ClawHub](https://clawhub.ai) 安装：

```bash
clawhub install weiqi-db
clawhub install weiqi-fetcher
clawhub install weiqi-foxwq
clawhub install weiqi-joseki
clawhub install weiqi-player
clawhub install weiqi-recorder
clawhub install weiqi-sgf
clawhub install weiqi-yunbisai
```

## 功能详解

### 🗄️ weiqi-db - 围棋棋谱数据库
- 本地棋谱管理工具，统一收纳野狐、本地SGF等来源的棋谱
- 支持SGF导入、元数据编辑、标签管理
- 全文搜索、JSON查询语法，AI友好接口
- 数据存储于 `~/.weiqi-db/database.json` 单文件

### 🔽 weiqi-fetcher - 分享棋谱下载器
从各大围棋平台分享链接自动下载SGF棋谱，支持10个平台：
- OGS、野狐围棋、101围棋网
- 弈客围棋、元萝卜围棋、星阵围棋
- 隐智智能棋盘、弈客少儿版
- 弈城围棋、腾讯围棋
- 自动解析各种链接格式，一键下载SGF文件

### 🔽 weiqi-foxwq - 野狐棋谱下载
- 按日期批量下载野狐围棋棋谱
- 支持从分享链接实时提取棋谱（WebSocket协议解析）
- 支持进行中/已结束对局

### 📚 weiqi-joseki - 围棋定式数据库
- 定式录入与管理，支持8向对称变化自动生成
- 从棋谱批量提取定式，自动检测脱先（PASS）定式
- KataGo Archive 自动导入，支持断点续传和内存保护
- 定式冲突检测与棋谱定式匹配识别
- 数据存储于 `~/.weiqi-joseki/database.json`

### 🔍 weiqi-player - 棋手查询
- 查询手谈等级分（dzqzd.com）
- 查询业余段位（yichafen.com）
- 批量查询支持

### 📝 weiqi-recorder - 记谱工具
- 单文件网页版记谱工具
- 支持黑白轮流落子、提子、打劫规则、悔棋
- 无需安装，浏览器直接打开使用

### 🎮 weiqi-sgf - SGF打谱工具
- 将SGF棋谱转换为交互式HTML网页
- 支持播放/暂停/手数跳转
- 支持让子棋

### 🏆 weiqi-yunbisai - 比赛查询
- 查询云比赛网围棋比赛列表
- 获取分组信息和选手名单
- 计算完整排名（积分/对手分/累进分）

## 依赖

- Python 3.8+
- OpenClaw 环境

部分技能包可能需要额外依赖，详见各技能包的 `SKILL.md`。

## 许可证

MIT License - 详见各技能包目录下的 `LICENSE` 文件。

## 相关链接

- [OpenClaw](https://github.com/openclaw/openclaw)
- [ClawHub](https://clawhub.ai)

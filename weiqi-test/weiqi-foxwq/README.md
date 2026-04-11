# weiqi-foxwq 测试套件

野狐围棋棋谱下载技能包的完整测试套件。

## 测试结构

```
weiqi-foxwq/
├── conftest.py              # 测试 fixtures 和工具函数
├── test_share_link.py       # 分享链接提取功能测试 (42 个测试)
├── test_nickname_download.py # 昵称下载功能测试 (34 个测试)
├── test_date_download.py    # 按日期下载功能测试 (37 个测试)
├── fixtures/                # 测试数据文件
│   ├── sample_api_response.json
│   ├── sample_chess_list.json
│   ├── sample_user_info.json
│   └── sample_html_page.html
└── README.md               # 本文件
```

## 测试覆盖

### test_share_link.py
- **URL 解析**: 有效链接、无效链接、带 roomid 的链接
- **API 提取**: 成功响应、错误码处理 (101200)、超时
- **WebSocket 提取**: 着法提取、玩家名提取、让子检测
- **SGF 创建**: 普通对局、让子棋 (2-9子)、HA/AB 标记
- **集成测试**: auto 模式优先 API，失败时回退 WebSocket

### test_nickname_download.py
- **用户查询**: 昵称查 UID、段位格式化 (职业/业余/级位)
- **棋谱列表**: 成功获取、空列表、分页、API 错误
- **SGF 下载**: 成功下载、API 错误、空响应
- **结果解析**: 黑胜/白胜/和棋/超时/认输/数子

### test_date_download.py
- **HTML 解析**: BeautifulSoup 解析、正则备选、空日期
- **SGF 提取**: 从 HTML 提取、未找到、特殊字符
- **下载流程**: 成功下载、网络错误、标题清理
- **性能计时**: 计时器启动、步骤计时、报告格式化

## 运行测试

```bash
# 运行所有 weiqi-foxwq 测试
cd /root/.openclaw/workspace/weiqi-test
make test SKILL=weiqi-foxwq

# 运行指定测试文件
make test SKILL=weiqi-foxwq FILE=test_share_link

# 运行指定测试类
python3 -m pytest weiqi-foxwq/test_share_link.py::TestApiExtraction -v

# 运行指定测试函数（模糊匹配）
make test SKILL=weiqi-foxwq FILE=test_share_link FUNC=handicap

# 显示测试覆盖率
python3 -m pytest weiqi-foxwq/ --cov=weiqi-foxwq --cov-report=term-missing
```

## Mock 策略

所有网络请求使用 `unittest.mock` 模拟，不实际调用野狐服务器：

- `mock_api_response`: 模拟 API 成功响应
- `mock_websocket_binary_data`: 模拟 WebSocket 二进制数据
- `mock_user_info_response`: 模拟用户信息查询响应
- `mock_chess_list_response`: 模拟棋谱列表响应

## 异步测试说明

WebSocket 相关测试使用 `pytest.mark.asyncio` 标记，需要安装 pytest-asyncio 插件才能运行：

```bash
pip3 install pytest-asyncio
```

未安装时，这些测试会被自动跳过。

## 测试统计

- 总测试数: 116
- 通过: 113
- 跳过: 3 (异步 WebSocket 测试)
- 失败: 0

## 维护说明

当修改 `download_share.py`、`download_by_name.py` 或 `download_sgf.py` 时，请同步更新对应的测试文件。

新增功能时，请遵循以下原则：
1. 每个函数至少一个测试用例
2. 包含正常情况和边界情况
3. 使用 mock 隔离外部依赖
4. 测试方法必须有文档字符串说明测试目的

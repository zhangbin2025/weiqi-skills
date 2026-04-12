"""
weiqi-yunbisai 测试配置和 Fixtures
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# 添加技能包脚本路径 (从 weiqi-test/weiqi-yunbisai 指向 workspace/weiqi-yunbisai/scripts)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "weiqi-yunbisai" / "scripts"))


@pytest.fixture
def mock_session():
    """创建 mock requests session"""
    session = MagicMock()
    session.headers = {}
    return session


@pytest.fixture
def sample_match_data():
    """样本对阵数据 - 完整比赛"""
    return [
        # 第1轮
        {"p1id": "1", "p1": "选手A", "p1_teamname": "一队", "p1_score": 2.0,
         "p2id": "2", "p2": "选手B", "p2_teamname": "二队", "p2_score": 0.0,
         "seatnum": 1, "bout": 1},
        {"p1id": "3", "p1": "选手C", "p1_teamname": "一队", "p1_score": 2.0,
         "p2id": "4", "p2": "选手D", "p2_teamname": "三队", "p2_score": 0.0,
         "seatnum": 2, "bout": 1},
        # 第2轮
        {"p1id": "1", "p1": "选手A", "p1_teamname": "一队", "p1_score": 2.0,
         "p2id": "3", "p2": "选手C", "p2_teamname": "一队", "p2_score": 0.0,
         "seatnum": 1, "bout": 2},
        {"p1id": "2", "p1": "选手B", "p1_teamname": "二队", "p1_score": 2.0,
         "p2id": "4", "p2": "选手D", "p2_teamname": "三队", "p2_score": 0.0,
         "seatnum": 2, "bout": 2},
    ]


@pytest.fixture
def sample_match_with_bye():
    """样本对阵数据 - 包含轮空"""
    return [
        # 第1轮 - 选手A轮空
        {"p1id": "1", "p1": "选手A", "p1_teamname": "一队", "p1_score": 2.0,
         "p2id": None, "p2": None, "p2_teamname": None, "p2_score": 0.0,
         "seatnum": 1, "bout": 1},
        {"p1id": "2", "p1": "选手B", "p1_teamname": "二队", "p1_score": 2.0,
         "p2id": "3", "p2": "选手C", "p2_teamname": "三队", "p2_score": 0.0,
         "seatnum": 2, "bout": 1},
    ]


@pytest.fixture
def sample_match_with_draw():
    """样本对阵数据 - 包含和棋"""
    return [
        {"p1id": "1", "p1": "选手A", "p1_teamname": "一队", "p1_score": 1.0,
         "p2id": "2", "p2": "选手B", "p2_teamname": "二队", "p2_score": 1.0,
         "seatnum": 1, "bout": 1},
        {"p1id": "3", "p1": "选手C", "p1_teamname": "三队", "p1_score": 2.0,
         "p2id": "4", "p2": "选手D", "p2_teamname": "四队", "p2_score": 0.0,
         "seatnum": 2, "bout": 1},
    ]


@pytest.fixture
def incomplete_match_data():
    """未完成轮次的对阵数据"""
    return [
        # 第1轮 - 已完成
        {"p1id": "1", "p1": "选手A", "p1_score": 2.0,
         "p2id": "2", "p2": "选手B", "p2_score": 0.0, "bout": 1},
        # 第2轮 - 未完成（所有 score 都是 0.0）
        {"p1id": "1", "p1": "选手A", "p1_score": 0.0,
         "p2id": "3", "p2": "选手C", "p2_score": 0.0, "bout": 2},
    ]


@pytest.fixture
def sample_events_data():
    """样本比赛列表数据"""
    return {
        "error": 0,
        "datArr": {
            "rows": [
                {"event_id": 12345, "title": "2026年测试比赛", "city_name": "广州市", 
                 "max_time": "2026-03-29T00:00:00", "play_num": 100},
                {"event_id": 12346, "title": "2026年另一场比赛", "city_name": "深圳市",
                 "max_time": "2026-03-21T00:00:00", "play_num": 50},
            ],
            "TotalPage": 1
        }
    }


@pytest.fixture
def sample_groups_data():
    """样本分组数据"""
    return {
        "error": 0,
        "datArr": {
            "rows": [
                {"group_id": 1001, "groupname": "5段及以上组", "event_id": 12345},
                {"group_id": 1002, "groupname": "4段组", "event_id": 12345},
            ]
        }
    }


@pytest.fixture
def sample_against_plan():
    """样本对阵表数据"""
    return {
        "error": 0,
        "datArr": {
            "total_bout": 5,
            "rows": [
                {"p1id": "1", "p1": "选手A", "p1_score": 2.0,
                 "p2id": "2", "p2": "选手B", "p2_score": 0.0,
                 "seatnum": 1},
                {"p1id": "3", "p1": "选手C", "p1_score": 0.0,
                 "p2id": "4", "p2": "选手D", "p2_score": 2.0,
                 "seatnum": 2},
            ]
        }
    }


@pytest.fixture
def complex_ranking_data():
    """复杂排名数据 - 用于测试同分排序（每个对局只出现一次）"""
    return [
        # 第1轮: A胜B, D胜C
        {"p1id": "1", "p1": "选手A", "p1_score": 2.0,
         "p2id": "2", "p2": "选手B", "p2_score": 0.0, "bout": 1},
        {"p1id": "3", "p1": "选手C", "p1_score": 0.0,
         "p2id": "4", "p2": "选手D", "p2_score": 2.0, "bout": 1},
        # 第2轮: A胜C, B胜D
        {"p1id": "1", "p1": "选手A", "p1_score": 2.0,
         "p2id": "3", "p2": "选手C", "p2_score": 0.0, "bout": 2},
        {"p1id": "2", "p1": "选手B", "p1_score": 2.0,
         "p2id": "4", "p2": "选手D", "p2_score": 0.0, "bout": 2},
    ]


@pytest.fixture
def client_class():
    """导入并返回 YunbisaiClient 类"""
    from query import YunbisaiClient
    return YunbisaiClient


@pytest.fixture
def perf_timer_class():
    """导入并返回 PerfTimer 类"""
    from query import PerfTimer
    return PerfTimer


@pytest.fixture
def perf_report_class():
    """导入并返回 PerfReport 类"""
    from query import PerfReport
    return PerfReport

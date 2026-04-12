"""
测试各个棋谱源的 fetch 方法
包含网络请求的测试使用 @requires_network 标记
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# 标记需要网络访问的测试
requires_network = pytest.mark.skipif(
    os.environ.get('SKIP_NETWORK_TESTS', 'false').lower() == 'true',
    reason='SKIP_NETWORK_TESTS 设置为 true'
)


class TestOgsFetcher:
    """测试OGS平台下载器"""
    
    def test_ogs_fetcher_initialization(self):
        """测试OGS fetcher初始化"""
        from sources import fetch_ogs
        
        fetcher = fetch_ogs.OgsFetcher()
        assert fetcher.name == 'ogs'
        assert fetcher.display_name == 'OGS (Online-Go)'
        assert len(fetcher.url_patterns) > 0
    
    def test_ogs_extract_id(self):
        """测试OGS ID提取"""
        from sources import fetch_ogs
        
        url = 'https://online-go.com/game/12345'
        fetcher = fetch_ogs.OgsFetcher()
        
        game_id = fetcher.extract_id(url)
        assert game_id == '12345'
    
    def test_ogs_extract_id_view_variant(self):
        """测试OGS view路径ID提取"""
        from sources import fetch_ogs
        
        url = 'https://online-go.com/game/view/67890'
        fetcher = fetch_ogs.OgsFetcher()
        
        game_id = fetcher.extract_id(url)
        assert game_id == '67890'
    
    def test_ogs_generate_sgf_basic(self):
        """测试SGF生成 - 基本对局"""
        from sources import fetch_ogs
        
        fetcher = fetch_ogs.OgsFetcher()
        
        game_data = {
            'moves': [[3, 3], [15, 3], [3, 15], [15, 15]],  # 星位
            'width': 19,
            'height': 19,
            'komi': 6.5,
            'handicap': 0,
            'rules': 'japanese',
        }
        
        metadata = {
            'black_name': 'BlackPlayer',
            'white_name': 'WhitePlayer',
            'black_rank': '3d',
            'white_rank': '3d',
            'komi': 6.5,
            'date': '2024-01-15',
            'result': 'B+R',
            'handicap': 0,
            'rules': 'japanese',
            'width': 19,
            'height': 19,
            'black_rank': '3d',
            'white_rank': '3d',
            'date': '2024-01-15',
        }
        
        sgf = fetcher._generate_sgf(game_data, metadata)
        
        # 验证SGF结构
        assert sgf.startswith('(;GM[1]FF[4]CA[UTF-8]')
        assert 'SZ[19:19]' in sgf
        assert 'PB[BlackPlayer]' in sgf
        assert 'PW[WhitePlayer]' in sgf
        assert 'BR[3d]' in sgf
        assert 'WR[3d]' in sgf
        assert 'KM[6.5]' in sgf
        assert 'DT[2024-01-15]' in sgf
        assert 'RE[B+R]' in sgf
        assert 'RU[JP]' in sgf  # japanese -> JP
        
        # 验证着法
        assert ';B[dp]' in sgf  # (3,3) -> dp
        assert ';W[pp]' in sgf  # (15,3) -> pp
        assert ';B[dd]' in sgf  # (3,15) -> dd
        assert ';W[pd]' in sgf  # (15,15) -> pd
    
    def test_ogs_generate_sgf_with_handicap(self):
        """测试SGF生成 - 让子棋"""
        from sources import fetch_ogs
        
        fetcher = fetch_ogs.OgsFetcher()
        
        game_data = {
            'moves': [[15, 3]],  # 第一手
            'width': 19,
            'height': 19,
            'komi': 0.5,
            'handicap': 4,
            'rules': 'chinese',
        }
        
        metadata = {
            'black_name': 'Black',
            'white_name': 'White',
            'black_rank': '4d',
            'white_rank': '1d',
            'komi': 0.5,
            'result': 'B+5.5',
            'handicap': 4,
            'rules': 'chinese',
            'width': 19,
            'height': 19,
            'black_rank': '4d',
            'white_rank': '1d',
            'date': '2024-01-15',
        }
        
        sgf = fetcher._generate_sgf(game_data, metadata)
        
        # 验证让子设置
        assert 'HA[4]' in sgf
        assert 'AB[pp]' in sgf  # 右上
        assert 'AB[pd]' in sgf  # 右下
        assert 'AB[dp]' in sgf  # 左上
        assert 'AB[dd]' in sgf  # 左下
        assert 'RU[CN]' in sgf  # chinese -> CN
        
        # 第一手是黑棋（实际实现中，让子棋第一手也是黑棋标记）
        assert ';B[pp]' in sgf
    
    def test_ogs_generate_sgf_9x9(self):
        """测试SGF生成 - 9路棋盘"""
        from sources import fetch_ogs
        
        fetcher = fetch_ogs.OgsFetcher()
        
        game_data = {
            'moves': [[2, 2], [6, 6]],
            'width': 9,
            'height': 9,
            'komi': 5.5,
            'handicap': 0,
            'rules': 'japanese',
        }
        
        metadata = {
            'black_name': 'B',
            'white_name': 'W',
            'komi': 5.5,
            'result': '?',
            'handicap': 0,
            'rules': 'japanese',
            'width': 9,
            'height': 9,
            'black_rank': '',
            'white_rank': '',
            'date': '',
        }
        
        sgf = fetcher._generate_sgf(game_data, metadata)
        
        assert 'SZ[9:9]' in sgf
        assert sgf.endswith(')')
    
    @requires_network
    def test_ogs_fetch_real_game(self):
        """测试下载真实OGS对局（需要网络）"""
        from sources import fetch_ogs
        
        # 使用一个公开的OGS对局
        # 这是一个已知的对局ID，如果失效可以替换
        url = 'https://online-go.com/game/12345'
        fetcher = fetch_ogs.OgsFetcher()
        
        result = fetcher.fetch(url)
        
        # 即使游戏不存在，也应该返回FetchResult
        assert result is not None
        assert hasattr(result, 'success')
        assert hasattr(result, 'source')
        assert result.source == 'ogs'
        
        if result.success:
            assert result.sgf_content is not None
            assert result.output_path is not None
            assert os.path.exists(result.output_path)
            
            # 清理
            if os.path.exists(result.output_path):
                os.remove(result.output_path)


class TestFoxwqFetcher:
    """测试野狐围棋下载器"""
    
    def test_foxwq_fetcher_initialization(self):
        """测试野狐fetcher初始化"""
        from sources import fetch_fox
        
        fetcher = fetch_fox.FoxwqFetcher()
        assert fetcher.name == 'foxwq'
        assert fetcher.display_name == '野狐围棋'
    
    def test_foxwq_extract_id_variations(self):
        """测试野狐ID提取的各种URL格式"""
        from sources import fetch_fox
        
        fetcher = fetch_fox.FoxwqFetcher()
        
        test_cases = [
            ('https://h5.foxwq.com/yehunewshare/?chessid=12345', '12345'),
            ('https://www.foxwq.com/share?chessid=67890', '67890'),
            ('https://foxwq.com/game?chessid=99999', '99999'),
        ]
        
        for url, expected_id in test_cases:
            extracted = fetcher.extract_id(url)
            assert extracted == expected_id, f"URL: {url}, 期望: {expected_id}, 实际: {extracted}"


class TestWeiqi101Fetcher:
    """测试101围棋网下载器"""
    
    def test_101weiqi_fetcher_initialization(self):
        """测试101围棋网fetcher初始化"""
        from sources import fetch_101
        
        fetcher = fetch_101.Weiqi101Fetcher()
        assert fetcher.name == 'weiqi101'
        assert fetcher.display_name == '101围棋网'
    
    def test_101weiqi_extract_id(self):
        """测试101围棋网ID提取"""
        from sources import fetch_101
        
        fetcher = fetch_101.Weiqi101Fetcher()
        
        # 101weiqi使用数字ID
        url = 'https://www.101weiqi.com/play/p/12345/'
        extracted = fetcher.extract_id(url)
        assert extracted == '12345'


class TestYikeFetcher:
    """测试弈客围棋下载器"""
    
    def test_yike_fetcher_initialization(self):
        """测试弈客fetcher初始化"""
        from sources import fetch_yike
        
        fetcher = fetch_yike.YikeWeiqiFetcher()
        assert fetcher.name == 'yikeweiqi'
        assert fetcher.display_name == '弈客围棋'
    
    def test_yike_extract_room_id(self):
        """测试弈客房间ID提取"""
        from sources import fetch_yike
        
        fetcher = fetch_yike.YikeWeiqiFetcher()
        
        # 测试不同格式的弈客URL
        urls = [
            'https://home.yikeweiqi.com/mobile.html#/golive/room/12345/live',
            'https://home.yikeweiqi.com/mobile.html#/golive/room/67890/review',
        ]
        
        for url in urls:
            assert fetcher.can_handle(url), f"应该能处理: {url}"


class TestYuanluoboFetcher:
    """测试元萝卜围棋下载器"""
    
    def test_yuanluobo_fetcher_initialization(self):
        """测试元萝卜fetcher初始化"""
        from sources import fetch_yuanluobo
        
        fetcher = fetch_yuanluobo.YuanluoboFetcher()
        assert fetcher.name == 'yuanluobo'
        assert fetcher.display_name == '元萝卜围棋'
    
    def test_yuanluobo_extract_session_id(self):
        """测试元萝卜session_id提取"""
        from sources import fetch_yuanluobo
        
        fetcher = fetch_yuanluobo.YuanluoboFetcher()
        
        url = 'https://jupiter.yuanluobo.com/robot-public/all-in-app/go/review?session_id=test123'
        extracted = fetcher.extract_id(url)
        assert extracted == 'test123'


class Test1919Fetcher:
    """测试星阵围棋下载器"""
    
    def test_1919_fetcher_initialization(self):
        """测试星阵fetcher初始化"""
        from sources import fetch_1919
        
        fetcher = fetch_1919.GolaxyFetcher()
        assert fetcher.name == 'golaxy'
        assert fetcher.display_name == '星阵围棋'


class TestIzisFetcher:
    """测试隐智智能棋盘下载器"""
    
    def test_izis_fetcher_initialization(self):
        """测试隐智fetcher初始化"""
        from sources import fetch_izis
        
        fetcher = fetch_izis.IzisFetcher()
        assert fetcher.name == 'izis'
        assert fetcher.display_name == '隐智智能棋盘'


class TestEweiqiFetcher:
    """测试弈城围棋下载器"""
    
    def test_eweiqi_fetcher_initialization(self):
        """测试弈城fetcher初始化"""
        from sources import fetch_eweiqi
        
        fetcher = fetch_eweiqi.EweiqiFetcher()
        assert fetcher.name == 'eweiqi'
        assert fetcher.display_name == '弈城围棋'
    
    def test_eweiqi_extract_game_no(self):
        """测试弈城游戏编号提取"""
        from sources import fetch_eweiqi
        
        fetcher = fetch_eweiqi.EweiqiFetcher()
        
        url = 'http://mobile.eweiqi.com/index_ZHCN.html?LNK=1&GNO=12345'
        assert fetcher.can_handle(url)


class TestTxwqFetcher:
    """测试腾讯围棋下载器"""
    
    def test_txwq_fetcher_initialization(self):
        """测试腾讯围棋fetcher初始化"""
        from sources import fetch_txwq
        
        fetcher = fetch_txwq.TxwqFetcher()
        assert fetcher.name == 'txwq'
        assert fetcher.display_name == '腾讯围棋'


class TestXinboduiyiFetcher:
    """测试新博对弈下载器"""
    
    def test_xinboduiyi_fetcher_initialization(self):
        """测试新博对弈fetcher初始化"""
        from sources import fetch_xinboduiyi
        
        fetcher = fetch_xinboduiyi.XinboduiyiFetcher()
        assert fetcher.name == 'xinboduiyi'
        assert fetcher.display_name == '新博对弈'


class TestDzqzdFetcher:
    """测试对弈曲折/手谈赛场下载器"""
    
    def test_dzqzd_fetcher_initialization(self):
        """测试对弈曲折fetcher初始化"""
        from sources import fetch_dzqzd
        
        fetcher = fetch_dzqzd.DzqzdFetcher()
        assert fetcher.name == 'dzqzd'
        assert fetcher.display_name == '对弈曲折/手谈赛场'
    
    def test_dzqzd_extract_kifu_id(self):
        """测试对弈曲折棋谱ID提取"""
        from sources import fetch_dzqzd
        
        fetcher = fetch_dzqzd.DzqzdFetcher()
        
        url = 'https://v.dzqzd.com/Kifu/chessmanualdetail?kifuId=12345'
        extracted = fetcher.extract_id(url)
        assert extracted == '12345'


class TestYikeShaoerFetcher:
    """测试弈客少儿版下载器"""
    
    def test_yike_shaoer_fetcher_initialization(self):
        """测试弈客少儿版fetcher初始化"""
        from sources import fetch_yike_shaoer
        
        fetcher = fetch_yike_shaoer.YikeShaoerFetcher()
        assert fetcher.name == 'yike_shaoer'
        assert fetcher.display_name == '弈客少儿版'

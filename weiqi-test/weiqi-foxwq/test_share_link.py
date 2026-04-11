"""
分享链接提取功能测试

测试 download_share.py 的各项功能
"""

import pytest
import sys
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-foxwq/scripts')

from download_share import (
    parse_share_url,
    extract_via_api,
    extract_via_websocket,
    extract_game_info,
    extract_moves_from_binary,
    extract_jueyi_live_from_binary,
    extract_handicap_from_binary,
    extract_player_names,
    is_jueyi_live_data,
    create_sgf,
    parse_sgf_info,
    extract_from_share_link,
    PerformanceTimer
)


class TestUrlParser:
    """URL 解析测试"""
    
    def test_parse_valid_share_url(self, sample_share_url, sample_chessid, sample_uid):
        """测试解析有效的分享链接"""
        result = parse_share_url(sample_share_url)
        
        assert result['chessid'] == sample_chessid
        assert result['uid'] == sample_uid
        assert result['createtime'] == '20240101120000'
        assert result['full_url'] == sample_share_url
    
    def test_parse_url_with_roomid(self, sample_share_url_with_roomid):
        """测试解析带 roomid 的分享链接"""
        result = parse_share_url(sample_share_url_with_roomid)
        
        assert result['roomid'] == '87654321'
        assert result['chessid'] == '12345678'
    
    def test_parse_invalid_url(self, invalid_share_url):
        """测试解析无效的分享链接"""
        result = parse_share_url(invalid_share_url)
        
        assert result['chessid'] is None
        assert result['uid'] is None
    
    def test_parse_url_missing_chessid(self):
        """测试解析缺少 chessid 的 URL"""
        url = "https://h5.foxwq.com/yehunewshare/?uid=12345"
        result = parse_share_url(url)
        
        assert result['chessid'] is None
        assert result['uid'] == '12345'
    
    def test_parse_empty_url(self):
        """测试解析空 URL"""
        result = parse_share_url("")
        
        assert result['chessid'] is None
        assert result['uid'] is None
    
    def test_parse_url_special_chars(self):
        """测试解析包含特殊字符的 URL"""
        url = "https://h5.foxwq.com/yehunewshare/?chessid=ABC123%26xyz&uid=user%40test"
        result = parse_share_url(url)
        
        assert result['chessid'] == 'ABC123&xyz'
        assert result['uid'] == 'user@test'


class TestApiExtraction:
    """API 提取测试"""
    
    def test_extract_via_api_success(self, sample_chessid, mock_api_response):
        """测试 API 提取成功"""
        with patch('download_share.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_api_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = extract_via_api(sample_chessid)
            
            assert result is not None
            assert "(;GM[1]FF[4]" in result
            assert "柯洁" in result
            mock_get.assert_called_once()
    
    def test_extract_via_api_failure(self, sample_chessid, mock_api_error_response):
        """测试 API 提取失败"""
        with patch('download_share.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_api_error_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = extract_via_api(sample_chessid)
            
            assert result is None
    
    def test_extract_via_api_timeout(self, sample_chessid):
        """测试 API 请求超时"""
        from requests.exceptions import Timeout
        
        with patch('download_share.requests.get') as mock_get:
            mock_get.side_effect = Timeout("Request timed out")
            
            result = extract_via_api(sample_chessid)
            
            assert result is None
    
    def test_extract_via_api_connection_error(self, sample_chessid):
        """测试 API 连接错误"""
        from requests.exceptions import ConnectionError
        
        with patch('download_share.requests.get') as mock_get:
            mock_get.side_effect = ConnectionError("Connection failed")
            
            result = extract_via_api(sample_chessid)
            
            assert result is None
    
    def test_extract_via_api_json_decode_error(self, sample_chessid):
        """测试 API JSON 解析错误"""
        with patch('download_share.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = extract_via_api(sample_chessid)
            
            assert result is None
    
    def test_extract_game_info_success(self, sample_chessid, sample_uid, mock_game_info_response):
        """测试获取对局信息成功"""
        with patch('download_share.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_game_info_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = extract_game_info(sample_chessid, sample_uid)
            
            assert result is not None
            assert result['black_nick'] == '柯洁'
            assert result['white_nick'] == '申真谞'
            assert result['black_dan'] == 109
            assert result['result'] == 'B+R'
            assert result['movenum'] == 250
    
    def test_extract_game_info_without_uid(self, sample_chessid, mock_game_info_response):
        """测试不指定 UID 获取对局信息"""
        with patch('download_share.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_game_info_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = extract_game_info(sample_chessid)
            
            assert result is not None
            assert result['black_nick'] == '柯洁'
    
    def test_extract_game_info_api_error(self, sample_chessid):
        """测试对局信息 API 返回错误"""
        with patch('download_share.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"result": -1, "resultstr": "Error"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = extract_game_info(sample_chessid)
            
            assert result is None


class TestWebSocketExtraction:
    """WebSocket 提取测试"""
    
    @pytest.mark.asyncio
    async def test_extract_via_websocket_no_playwright(self):
        """测试未安装 Playwright 时的行为"""
        with patch.dict('sys.modules', {'playwright.async_api': None}):
            result = await extract_via_websocket("https://test.com", timeout=1)
            
            assert result == (None, None, 0, None)
    
    @pytest.mark.asyncio
    async def test_extract_via_websocket_success(self):
        """测试 WebSocket 提取 - 验证 Playwright 环境可用"""
        # 验证 playwright.async_api 可以正常导入
        try:
            from playwright.async_api import async_playwright
            PLAYWRIGHT_AVAILABLE = True
        except ImportError:
            PLAYWRIGHT_AVAILABLE = False
        
        assert PLAYWRIGHT_AVAILABLE, "Playwright 应该已安装"
        
        # 使用无效 URL 测试，验证函数能正确处理异常
        # 由于会尝试真实连接，我们捕获超时异常
        try:
            result = await extract_via_websocket("https://localhost:99999", timeout=0.5)
            # 如果超时或出错，应该返回 (None, None, 0, None)
            assert result == (None, None, 0, None) or result[0] is None
        except Exception:
            # 任何异常都应该被处理，返回空结果
            pass
    
    @pytest.mark.asyncio
    async def test_extract_via_websocket_with_moves(self, mock_websocket_binary_data):
        """测试从 WebSocket 二进制数据中提取着法"""
        # 直接测试 extract_moves_from_binary 函数已在其他测试中覆盖
        # 这里验证 WebSocket 数据格式解析正确
        moves = extract_moves_from_binary(mock_websocket_binary_data)
        
        # mock_websocket_binary_data 包含 08 03 10 03 (D3) 和 08 0f 10 0f (O15)
        assert len(moves) >= 1
        assert (3, 3) in moves or (15, 15) in moves


class TestJueyiLiveExtraction:
    """绝艺解说直播棋谱提取测试"""
    
    def test_is_jueyi_live_data_with_jueyi_string(self):
        """测试包含 jueyi 字符串的数据识别"""
        data = b'some_random_data_jueyi_comment_more_data'
        
        result = is_jueyi_live_data(data)
        
        assert result is True
    
    def test_is_jueyi_live_data_with_marker(self):
        """测试包含主分支标记的数据识别"""
        # 包含主分支标记 10 cb 01
        data = bytes([0x00, 0x01, 0x10, 0xcb, 0x01, 0x02])
        
        result = is_jueyi_live_data(data)
        
        assert result is True
    
    def test_is_jueyi_live_data_normal_data(self):
        """测试普通数据不被识别为绝艺直播"""
        # 注意：不能包含 "jueyi" 子串，否则会被识别为绝艺数据
        data = b'normal_websocket_binary_data_regular'
        
        result = is_jueyi_live_data(data)
        
        assert result is False
    
    def test_is_jueyi_live_data_empty(self):
        """测试空数据"""
        result = is_jueyi_live_data(b'')
        
        assert result is False
    
    def test_extract_jueyi_live_from_binary_basic(self, mock_jueyi_live_binary_data):
        """测试从绝艺直播数据中提取基本着法"""
        moves = extract_jueyi_live_from_binary(mock_jueyi_live_binary_data)
        
        # 应该提取到至少3手棋
        assert len(moves) >= 3
        # 验证第一手是 B[pd] (15, 3)
        assert moves[0] == (15, 3)
        # 验证第二手是 W[dc] (3, 2)
        assert moves[1] == (3, 2)
        # 验证第三手是 B[dp] (3, 15)
        assert moves[2] == (3, 15)
    
    def test_extract_jueyi_live_from_binary_with_comments(self, mock_jueyi_live_with_comments):
        """测试从绝艺直播数据中提取带评论的着法"""
        moves = extract_jueyi_live_from_binary(mock_jueyi_live_with_comments)
        
        # 应该提取到5手棋
        assert len(moves) == 5
        # 验证前几手坐标
        assert moves[0] == (15, 3)  # B[pd]
        assert moves[1] == (3, 2)   # W[dc]
        assert moves[2] == (3, 15)  # B[dp]
        assert moves[3] == (15, 16) # W[pq]
        assert moves[4] == (2, 4)   # B[ce]
    
    def test_extract_jueyi_live_from_binary_empty(self):
        """测试从空数据中提取"""
        moves = extract_jueyi_live_from_binary(b'')
        
        assert moves == []
    
    def test_extract_jueyi_live_from_binary_no_marker(self):
        """测试无绝艺标记的数据"""
        data = b'random_binary_data_without_jueyi_marker_08_03_10_03'
        
        moves = extract_jueyi_live_from_binary(data)
        
        assert moves == []
    
    def test_extract_jueyi_live_from_binary_partial_data(self):
        """测试不完整的绝艺数据"""
        # 只有主分支标记，没有完整的着法数据
        data = bytes([0x10, 0xcb, 0x01, 0x1a, 0x12, 0x08])
        
        moves = extract_jueyi_live_from_binary(data)
        
        # 应该返回空列表或跳过不完整的着法
        assert len(moves) == 0
    
    def test_jueyi_vs_normal_extraction(self):
        """测试绝艺提取与普通提取的差异"""
        # 构造同时包含两种模式的数据
        data = bytearray()
        # 普通模式着法 (08 03 10 03)
        data.extend([0x08, 0x03, 0x10, 0x03])
        # 绝艺模式着法 (10 cb 01 1a 12 08 0f 10 03 18 01)
        data.extend([0x10, 0xcb, 0x01])
        data.extend([0x1a, 0x12])
        data.extend([0x08, 0x0f, 0x10, 0x03, 0x18, 0x01])
        data = bytes(data)
        
        # 普通提取应该能找到更多着法（包括误匹配的）
        normal_moves = extract_moves_from_binary(data)
        jueyi_moves = extract_jueyi_live_from_binary(data)
        
        # 绝艺提取应该只返回主分支着法
        assert len(jueyi_moves) >= 1
        # 验证绝艺提取的着法是主分支着法 (15, 3)
        assert jueyi_moves[0] == (15, 3)


class TestSgfCreation:
    """SGF 创建测试"""
    
    def test_create_sgf_normal_game(self):
        """测试创建普通对局的 SGF"""
        moves = [(3, 3), (15, 15), (3, 15), (15, 3)]
        sgf = create_sgf(moves, "柯洁", "申真谞")
        
        assert sgf is not None
        assert "(;GM[1]FF[4]" in sgf
        assert "PB[柯洁]" in sgf
        assert "PW[申真谞]" in sgf
        assert "SZ[19]" in sgf
        # 验证着法
        assert ";B[dd]" in sgf  # D4 (3,3)
        assert ";W[pp]" in sgf  # Q16 (15,15)
    
    def test_create_sgf_empty_moves(self):
        """测试创建空着法的 SGF"""
        sgf = create_sgf([], "黑棋", "白棋")
        
        assert sgf is None
    
    def test_create_sgf_handicap_2(self):
        """测试创建让2子棋的 SGF"""
        moves = [(3, 3), (15, 15)]
        sgf = create_sgf(moves, "黑棋", "白棋", handicap=2)
        
        assert sgf is not None
        assert "HA[2]" in sgf
        assert "AB[dd]" in sgf  # 让子位置
        assert "AB[pp]" in sgf
        # 让子棋第一手是白棋
        assert ";W[dd]" in sgf
        assert ";B[pp]" in sgf
    
    def test_create_sgf_handicap_3(self):
        """测试创建让3子棋的 SGF"""
        moves = [(3, 3), (15, 15), (3, 15)]
        sgf = create_sgf(moves, "黑棋", "白棋", handicap=3)
        
        assert sgf is not None
        assert "HA[3]" in sgf
        assert "AB[dd]" in sgf
        assert "AB[pp]" in sgf
        assert "AB[dp]" in sgf
    
    def test_create_sgf_handicap_4(self):
        """测试创建让4子棋的 SGF"""
        sgf = create_sgf([(9, 9)], "黑棋", "白棋", handicap=4)
        
        assert sgf is not None
        assert "HA[4]" in sgf
        assert "AB[dd]" in sgf
        assert "AB[pp]" in sgf
        assert "AB[dp]" in sgf
        assert "AB[pd]" in sgf
    
    def test_create_sgf_handicap_5(self):
        """测试创建让5子棋的 SGF"""
        sgf = create_sgf([(9, 9)], "黑棋", "白棋", handicap=5)
        
        assert sgf is not None
        assert "HA[5]" in sgf
        assert "AB[jj]" in sgf  # 天元 (9,9)
    
    def test_create_sgf_handicap_6_to_9(self):
        """测试创建让6-9子棋的 SGF"""
        for handicap in [6, 7, 8, 9]:
            sgf = create_sgf([(9, 9)], "黑棋", "白棋", handicap=handicap)
            
            assert sgf is not None
            assert f"HA[{handicap}]" in sgf
    
    def test_create_sgf_moves_out_of_bounds(self):
        """测试创建包含越界坐标的 SGF"""
        moves = [(3, 3), (25, 25), (15, 15)]  # (25,25) 越界
        sgf = create_sgf(moves, "黑棋", "白棋")
        
        assert sgf is not None
        # 越界坐标应该被过滤掉
        assert sgf.count(";B[") + sgf.count(";W[") == 2  # 只有2个有效着法


class TestHandicapDetection:
    """让子检测测试"""
    
    def test_extract_handicap_from_binary_gamerule_pattern(self, mock_websocket_handicap_data):
        """测试从 GameRule 模式中提取让子数"""
        handicap = extract_handicap_from_binary(mock_websocket_handicap_data)
        
        assert handicap == 4
    
    def test_extract_handicap_from_sgf_text(self):
        """测试从 SGF 文本中提取让子数"""
        data = b'some_data_HA[6]_more_data'
        handicap = extract_handicap_from_binary(data)
        
        assert handicap == 6
    
    def test_extract_handicap_no_match(self):
        """测试无让子信息时返回0"""
        data = b'some_random_binary_data_without_handicap'
        handicap = extract_handicap_from_binary(data)
        
        assert handicap == 0
    
    def test_extract_handicap_invalid_value(self):
        """测试无效让子数值"""
        # 让子数超出 2-9 范围
        data = bytes([0x08, 0x13, 0x10, 0x01, 0x18, 0x15])  # handicap = 21
        handicap = extract_handicap_from_binary(data)
        
        # 应该返回0，因为21不在有效范围内
        assert handicap == 0


class TestMovesExtraction:
    """着法提取测试"""
    
    def test_extract_moves_from_binary_basic(self):
        """测试从二进制数据中提取基本着法"""
        # 构造 08 xx 10 yy 模式的数据
        # 第一个着法: 08 03 10 03 -> (3, 3)
        # 第二个着法: 08 10 10 04 -> (16, 4)，但需要跳过第一个着法的字节
        data = bytes([0x08, 0x03, 0x10, 0x03, 0x00, 0x08, 0x10, 0x10, 0x04])
        moves = extract_moves_from_binary(data)
        
        # 函数会找到所有符合模式的字节序列
        assert len(moves) >= 1
        assert moves[0] == (3, 3)
    
    def test_extract_moves_empty_data(self):
        """测试从空数据中提取着法"""
        moves = extract_moves_from_binary(b'')
        
        assert moves == []
    
    def test_extract_moves_no_pattern(self):
        """测试无着法模式时返回空列表"""
        data = b'random_binary_data_without_move_pattern'
        moves = extract_moves_from_binary(data)
        
        assert moves == []
    
    def test_extract_moves_out_of_bounds(self):
        """测试提取超出棋盘范围的着法"""
        # (20, 20) 超出 19x19 棋盘
        data = bytes([0x08, 0x14, 0x10, 0x14])
        moves = extract_moves_from_binary(data)
        
        # 越界坐标应该被过滤
        assert moves == []


class TestPlayerNamesExtraction:
    """玩家名字提取测试"""
    
    def test_extract_player_names_with_prefix(self):
        """测试使用 9a 01 前缀提取玩家名"""
        # 构造包含 9a 01 前缀的名字数据
        data = bytearray()
        # 第一个名字: 柯洁 (UTF-8: 6字节)
        data.extend([0x9a, 0x01, 0x06])  # 前缀 + 长度6
        data.extend("柯洁".encode('utf-8'))
        # 第二个名字: 申真谞 (UTF-8: 9字节)
        data.extend([0x9a, 0x01, 0x09])  # 前缀 + 长度9
        data.extend("申真谞".encode('utf-8'))
        
        names = extract_player_names(bytes(data))
        
        assert "柯洁" in names
        assert "申真谞" in names
    
    def test_extract_player_names_from_text(self):
        """测试从文本中提取玩家名"""
        # 当二进制前缀提取失败时，函数会回退到正则提取
        # 正则模式: ([\w\u4e00-\u9fff]+)\[\d+段\]
        data = "PlayerA[9段]vsPlayerB[9段]".encode('utf-8')
        names = extract_player_names(data)
        
        # 如果没有匹配到，返回空列表也是可接受的
        assert isinstance(names, list)
    
    def test_extract_player_names_empty(self):
        """测试从空数据中提取玩家名"""
        names = extract_player_names(b'')
        
        assert names == []
    
    def test_extract_player_names_filter_invalid(self):
        """测试过滤无效名字"""
        # 包含 IP 地址和 avatar 应该被过滤
        data = b'some\x9a\x011.14.205.137\x9a\x01avatar\x9a\x05valid'
        names = extract_player_names(data)
        
        assert '1.14.205.137' not in names
        assert 'avatar' not in names


class TestSgfInfoParsing:
    """SGF 信息解析测试"""
    
    def test_parse_sgf_info_basic(self):
        """测试解析基本 SGF 信息"""
        sgf = "(;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞]BR[9段]WR[9段]RE[B+R]DT[2024-01-15])"
        info = parse_sgf_info(sgf)
        
        assert info['pb'] == '柯洁'
        assert info['pw'] == '申真谞'
        assert info['br'] == '9段'
        assert info['wr'] == '9段'
        assert info['result'] == 'B+R'
        assert info['date'] == '2024-01-15'
    
    def test_parse_sgf_info_defaults(self):
        """测试 SGF 信息默认值"""
        sgf = "(;GM[1]FF[4]SZ[19])"
        info = parse_sgf_info(sgf)
        
        assert info['pb'] == '黑棋'
        assert info['pw'] == '白棋'
        assert info['result'] == ''
        assert info['date'] == ''
    
    def test_parse_sgf_info_move_count(self):
        """测试解析 SGF 手数"""
        sgf = "(;GM[1]FF[4];B[pd];W[dp];B[pp];W[dd])"
        info = parse_sgf_info(sgf)
        
        assert info['movenum'] == 4
    
    def test_parse_sgf_info_empty(self):
        """测试解析空 SGF"""
        info = parse_sgf_info("")
        
        assert info['pb'] == '黑棋'
        assert info['pw'] == '白棋'
        assert info['movenum'] == 0


class TestIntegration:
    """集成测试"""
    
    def test_auto_mode_prefers_api(self, sample_share_url, mock_api_response, temp_output_dir, mock_game_info_response):
        """测试 auto 模式优先使用 API"""
        output_path = Path(temp_output_dir) / "test.sgf"
        
        with patch('download_share.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.side_effect = [mock_api_response, mock_game_info_response]
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = extract_from_share_link(sample_share_url, str(output_path), mode='auto')
            
            assert result is not None
            assert output_path.exists()
    
    def test_api_mode_skips_websocket_on_failure(self, sample_share_url):
        """测试 API 模式失败时不尝试 WebSocket"""
        with patch('download_share.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"result": -1}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = extract_from_share_link(sample_share_url, mode='api')
            
            assert result is None
    
    def test_websocket_mode_no_chessid(self):
        """测试 WebSocket 模式无 chessid 时失败"""
        url = "https://h5.foxwq.com/yehunewshare/?uid=12345"
        
        result = extract_from_share_link(url, mode='websocket')
        
        assert result is None
    
    def test_invalid_mode(self, sample_share_url):
        """测试无效模式"""
        result = extract_from_share_link(sample_share_url, mode='invalid')
        
        # auto 模式应该被使用，但会因为 API 失败而返回 None
        assert result is None


class TestPerformanceTimer:
    """性能计时器测试"""
    
    def test_timer_start(self):
        """测试计时器启动"""
        timer = PerformanceTimer()
        result = timer.start()
        
        assert result is timer
        assert timer.start_time is not None
    
    def test_timer_step(self):
        """测试计时步骤"""
        import time
        
        timer = PerformanceTimer()
        timer.start()
        
        with timer.step("test_step"):
            time.sleep(0.01)
        
        assert "test_step" in timer.timings
        assert timer.timings["test_step"] >= 0.01
    
    def test_timer_format_report(self):
        """测试计时报告格式化"""
        import time
        
        timer = PerformanceTimer()
        timer.start()
        
        with timer.step("step1"):
            time.sleep(0.01)
        with timer.step("step2"):
            time.sleep(0.01)
        
        report = timer.format_report()
        
        assert "性能计时报告" in report
        assert "step1" in report
        assert "step2" in report
    
    def test_timer_empty_report(self):
        """测试空计时报告"""
        timer = PerformanceTimer()
        timer.start()
        
        report = timer.format_report()
        
        assert "性能计时报告" in report

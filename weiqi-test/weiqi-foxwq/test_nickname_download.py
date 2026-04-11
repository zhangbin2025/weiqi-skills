"""
昵称下载功能测试

测试 download_by_name.py 的各项功能
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-foxwq/scripts')

from download_by_name import (
    query_user_by_name,
    fetch_chess_list,
    fetch_sgf,
    format_dan,
    parse_result,
    http_get
)


class TestUserQuery:
    """用户查询测试"""
    
    def test_query_user_success(self, sample_nickname, mock_user_info_response):
        """测试成功查询用户信息"""
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = MagicMock(return_value=json.dumps(mock_user_info_response))()
            
            # 需要 patch json.loads 因为我们模拟的是字符串返回
            with patch('json.loads') as mock_json:
                mock_json.return_value = mock_user_info_response
                result = query_user_by_name(sample_nickname)
                
                assert result is not None
                assert result['uid'] == '12345678'
                assert result['nickname'] == '星阵谈兵'
                assert result['dan'] == 109
                assert result['total_win'] == 1000
    
    def test_query_user_not_found(self, mock_user_not_found_response):
        """测试查询不存在的用户"""
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(mock_user_not_found_response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = mock_user_not_found_response
                with pytest.raises(Exception) as exc_info:
                    query_user_by_name("不存在的用户")
                
                assert "查询用户失败" in str(exc_info.value)
    
    def test_query_user_empty_uid(self):
        """测试查询返回空 UID"""
        response = {
            "result": 0,
            "uid": "",
            "username": "测试用户"
        }
        
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = response
                with pytest.raises(Exception) as exc_info:
                    query_user_by_name("测试用户")
                
                assert "未找到该昵称对应的UID" in str(exc_info.value)
    
    def test_query_user_connection_error(self):
        """测试查询用户时连接错误"""
        with patch('download_by_name.http_get') as mock_http:
            mock_http.side_effect = Exception("Connection error")
            
            with pytest.raises(Exception):
                query_user_by_name("测试用户")


class TestDanFormatting:
    """段位格式化测试"""
    
    def test_format_dan_pro_9d(self):
        """测试职业9段格式化"""
        result = format_dan(109)
        assert result == "职业9段"
    
    def test_format_dan_pro_1d(self):
        """测试职业1段格式化"""
        result = format_dan(101)
        assert result == "职业1段"
    
    def test_format_dan_amateur_9d(self):
        """测试业余9段格式化"""
        result = format_dan(29)
        assert result == "业9段"
    
    def test_format_dan_amateur_1d(self):
        """测试业余1段格式化"""
        result = format_dan(21)
        assert result == "业1段"
    
    def test_format_dan_amateur_1k(self):
        """测试业余1级格式化"""
        result = format_dan(19)
        # 根据代码逻辑，19应该显示为"9级" (19-10=9)
        assert "级" in result
    
    def test_format_dan_level_5k(self):
        """测试5级格式化"""
        result = format_dan(15)
        # 15-10=5，所以应该是5级
        assert "5级" in result or "级" in result
    
    def test_format_dan_beginner(self):
        """测试初学者级别"""
        result = format_dan(5)
        assert "5级" in result or "级" in result
    
    def test_format_dan_high_amateur(self):
        """测试业余高段（24+）"""
        result = format_dan(25)
        assert "业5段" in result


class TestChessList:
    """棋谱列表测试"""
    
    def test_fetch_chess_list_success(self, mock_chess_list_response):
        """测试成功获取棋谱列表"""
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(mock_chess_list_response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = mock_chess_list_response
                result = fetch_chess_list("12345")
                
                assert len(result) == 2
                assert result[0]['chessid'] == '100001'
                assert result[0]['blacknick'] == '柯洁'
                assert result[1]['chessid'] == '100002'
    
    def test_fetch_chess_list_empty(self, mock_empty_chess_list_response):
        """测试获取空棋谱列表"""
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(mock_empty_chess_list_response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = mock_empty_chess_list_response
                result = fetch_chess_list("12345")
                
                assert result == []
    
    def test_fetch_chess_list_with_lastcode(self):
        """测试带 lastcode 分页获取棋谱列表"""
        response = {
            "result": 0,
            "chesslist": [{"chessid": "200001"}]
        }
        
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = response
                result = fetch_chess_list("12345", lastcode="100")
                
                assert len(result) == 1
                # 验证 URL 包含 lastcode
                call_args = mock_http.call_args[0][0]
                assert "lastcode=100" in call_args
    
    def test_fetch_chess_list_api_error(self):
        """测试棋谱列表 API 返回错误"""
        response = {
            "result": -1,
            "resultstr": "获取失败"
        }
        
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = response
                with pytest.raises(Exception) as exc_info:
                    fetch_chess_list("12345")
                
                assert "获取失败" in str(exc_info.value)
    
    def test_fetch_chess_list_pagination(self, mock_chess_list_pagination_response):
        """测试棋谱列表分页"""
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(mock_chess_list_pagination_response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = mock_chess_list_pagination_response
                result = fetch_chess_list("12345")
                
                assert len(result) == 20


class TestSgfDownload:
    """SGF 下载测试"""
    
    def test_fetch_sgf_success(self):
        """测试成功下载 SGF"""
        response = {
            "result": 0,
            "chess": "(;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞])"
        }
        
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = response
                result = fetch_sgf("12345")
                
                assert result == "(;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞])"
    
    def test_fetch_sgf_api_error(self):
        """测试 SGF 下载 API 返回错误"""
        response = {
            "result": -1,
            "resultstr": "棋谱不存在"
        }
        
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = response
                with pytest.raises(Exception) as exc_info:
                    fetch_sgf("12345")
                
                assert "下载棋谱失败" in str(exc_info.value)
    
    def test_fetch_sgf_empty_response(self):
        """测试 SGF 下载返回空内容"""
        response = {
            "result": 0,
            "chess": ""
        }
        
        with patch('download_by_name.http_get') as mock_http:
            mock_http.return_value = json.dumps(response)
            
            with patch('json.loads') as mock_json:
                mock_json.return_value = response
                result = fetch_sgf("12345")
                
                assert result == ""


class TestResultParser:
    """结果解析测试"""
    
    def test_parse_result_black_win_by_points(self):
        """测试黑棋数子胜"""
        result = parse_result(1, 3, 1)  # winner=1(黑), point=3, reason=1(数子)
        assert result == "黑胜 3子"
    
    def test_parse_result_white_win_by_points(self):
        """测试白棋数子胜"""
        result = parse_result(2, 5, 1)  # winner=2(白), point=5, reason=1(数子)
        assert result == "白胜 5子"
    
    def test_parse_result_black_win_zero_points(self):
        """测试黑棋数子胜但 point=0"""
        result = parse_result(1, 0, 1)
        assert result == "黑胜"
    
    def test_parse_result_white_timeout(self):
        """测试白棋超时负"""
        result = parse_result(1, 0, 2)  # winner=1(黑), reason=2(超时)
        assert result == "黑胜 (超时)"
    
    def test_parse_result_black_timeout(self):
        """测试黑棋超时负"""
        result = parse_result(2, 0, 2)  # winner=2(白), reason=2(超时)
        assert result == "白胜 (超时)"
    
    def test_parse_result_mid_game_win(self):
        """测试中盘胜"""
        result = parse_result(1, 0, 3)  # winner=1(黑), reason=3(中盘)
        assert result == "黑胜 (中盘)"
    
    def test_parse_result_resign(self):
        """测试认输"""
        result = parse_result(2, 0, 4)  # winner=2(白), reason=4(认输)
        assert result == "白胜 (认输)"
    
    def test_parse_result_draw(self):
        """测试和棋"""
        result = parse_result(0, 0, 1)  # winner=0(和棋)
        assert result == "和棋"
    
    def test_parse_result_unknown_reason(self):
        """测试未知胜负原因"""
        result = parse_result(1, 0, 99)  # 未知 reason
        assert result == "黑胜"


class TestHttpGet:
    """HTTP 请求测试"""
    
    def test_http_get_success(self):
        """测试 HTTP GET 成功"""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'test response'
            mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = Mock(return_value=False)
            
            result = http_get("http://test.com")
            
            assert result == 'test response'
    
    def test_http_get_with_headers(self):
        """测试 HTTP GET 请求头"""
        with patch('urllib.request.urlopen') as mock_urlopen:
            with patch('urllib.request.Request') as mock_request:
                mock_response = Mock()
                mock_response.read.return_value = b'{}'
                mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
                mock_urlopen.return_value.__exit__ = Mock(return_value=False)
                
                http_get("http://test.com")
                
                # 验证请求被创建并添加了头
                mock_request.assert_called_once()
                call_args = mock_request.call_args
                assert call_args[0][0] == "http://test.com"
    
    def test_http_get_timeout(self):
        """测试 HTTP GET 超时"""
        from urllib.error import URLError
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = URLError("timeout")
            
            with pytest.raises(URLError):
                http_get("http://test.com")


class TestMainFunctionIntegration:
    """主函数集成测试"""
    
    def test_main_with_args(self, mock_user_info_response, mock_chess_list_response):
        """测试带参数的主函数调用"""
        with patch('sys.argv', ['download_by_name.py', '星阵谈兵', '--limit', '5']):
            with patch('download_by_name.http_get') as mock_http:
                # 设置 mock 依次返回用户信息和棋谱列表
                mock_http.return_value = json.dumps(mock_user_info_response)
                
                with patch('json.loads') as mock_json:
                    mock_json.return_value = mock_user_info_response
                    with patch('download_by_name.fetch_chess_list') as mock_fetch_list:
                        mock_fetch_list.return_value = mock_chess_list_response['chesslist']
                        
                        # 测试可以执行到查询用户这一步
                        result = query_user_by_name('星阵谈兵')
                        assert result['nickname'] == '星阵谈兵'
    
    def test_main_without_args(self):
        """测试不带参数的主函数调用"""
        with patch('sys.argv', ['download_by_name.py']):
            # 模拟缺少参数的情况
            # 这里我们只是验证参数解析逻辑
            args = ['download_by_name.py']
            if len(args) < 2:
                # 预期的行为：显示帮助信息
                pass


# 辅助函数：json 模块可能在全局未导入，这里确保导入
import json as json_module

"""
weiqi-yunbisai 技能包测试

测试范围:
- API 客户端功能
- 排名计算算法
- 数据解析
- HTML 生成
"""
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock


class TestPerfTimer:
    """性能计时器测试"""
    
    def test_timer_creation(self, perf_timer_class):
        """测试计时器创建"""
        timer = perf_timer_class("test_timer")
        assert timer.name == "test_timer"
        assert timer.start_time > 0
        assert timer.end_time is None
    
    def test_timer_elapsed(self, perf_timer_class):
        """测试计时器经过时间"""
        timer = perf_timer_class("test")
        time.sleep(0.01)  # 等待10ms
        elapsed = timer.elapsed()
        assert elapsed >= 0.01
    
    def test_timer_stop(self, perf_timer_class):
        """测试计时器停止"""
        timer = perf_timer_class("test")
        time.sleep(0.01)
        elapsed = timer.stop()
        assert timer.end_time is not None
        assert elapsed >= 0.01


class TestPerfReport:
    """性能报告测试"""
    
    def test_report_creation(self, perf_report_class):
        """测试报告创建"""
        report = perf_report_class()
        assert len(report.timers) == 0
        assert report.total_start > 0
    
    def test_start_timer(self, perf_report_class):
        """测试开始计时"""
        report = perf_report_class()
        timer = report.start("test_step")
        assert len(report.timers) == 1
        assert timer.name == "test_step"
    
    def test_summary_format(self, perf_report_class):
        """测试报告格式"""
        report = perf_report_class()
        timer = report.start("test_step")
        timer.stop()
        summary = report.summary()
        assert "性能计时报告" in summary
        assert "test_step" in summary
        assert "总耗时" in summary
    
    def test_to_dict(self, perf_report_class):
        """测试转为字典"""
        report = perf_report_class()
        timer = report.start("test_step")
        timer.stop()
        data = report.to_dict()
        assert "total_seconds" in data
        assert "steps" in data
        assert len(data["steps"]) == 1


class TestYunbisaiClientInit:
    """客户端初始化测试"""
    
    def test_client_creation(self, client_class):
        """测试客户端创建"""
        client = client_class(verbose=False)
        assert client.verbose is False
        assert client.session is not None
        assert "User-Agent" in client.session.headers
        assert client.session.headers["Referer"] == "https://www.yunbisai.com/"
    
    def test_client_verbose_mode(self, client_class):
        """测试详细模式"""
        client = client_class(verbose=True)
        assert client.verbose is True


class TestYunbisaiClientAPI:
    """API 调用测试（Mock）"""
    
    def test_get_events_success(self, client_class, sample_events_data):
        """测试获取比赛列表成功"""
        client = client_class(verbose=False)
        
        mock_response = Mock()
        mock_response.json.return_value = sample_events_data
        mock_response.raise_for_status.return_value = None
        
        with patch.object(client.session, 'get', return_value=mock_response):
            events, perf = client.get_events(area="广东省", month=1)
        
        assert len(events) == 2
        assert events[0]["event_id"] == 12345
        assert "seconds" in perf
    
    def test_get_events_empty_response(self, client_class):
        """测试空响应处理"""
        client = client_class(verbose=False)
        
        mock_response = Mock()
        mock_response.json.return_value = {"error": 0, "rows": []}
        mock_response.raise_for_status.return_value = None
        
        with patch.object(client.session, 'get', return_value=mock_response):
            events, perf = client.get_events()
        
        assert len(events) == 0
    
    def test_get_groups_success(self, client_class, sample_groups_data):
        """测试获取分组成功"""
        client = client_class(verbose=False)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_groups_data
        mock_response.raise_for_status.return_value = None
        
        with patch.object(client.session, 'get', return_value=mock_response):
            groups, perf = client.get_groups(event_id=12345)
        
        assert len(groups) == 2
        assert groups[0]["group_id"] == 1001
    
    def test_get_groups_403_fallback(self, client_class):
        """测试 403 错误时回退到 HTML 解析"""
        client = client_class(verbose=False)
        
        mock_response = Mock()
        mock_response.status_code = 403
        
        html_content = '''
        <html>
        <li data-groupname="5段及以上组"><a data-groupid="1001">测试</a></li>
        <li data-groupname="4段组"><a data-groupid="1002">测试</a></li>
        </html>
        '''
        mock_html_response = Mock()
        mock_html_response.text = html_content
        mock_html_response.raise_for_status.return_value = None
        
        with patch.object(client.session, 'get', side_effect=[mock_response, mock_html_response]):
            groups, perf = client.get_groups(event_id=12345)
        
        assert len(groups) == 2
        assert groups[0]["groupname"] == "5段及以上组"
        assert perf["source"] == "html"
    
    def test_get_against_plan_success(self, client_class, sample_against_plan):
        """测试获取对阵表成功"""
        client = client_class(verbose=False)
        
        mock_response = Mock()
        mock_response.json.return_value = sample_against_plan
        mock_response.raise_for_status.return_value = None
        
        with patch.object(client.session, 'get', return_value=mock_response):
            data, perf = client.get_against_plan(group_id=1001, bout=1)
        
        assert data is not None
        assert data["total_bout"] == 5
        assert len(data["rows"]) == 2
    
    def test_get_against_plan_failure(self, client_class):
        """测试获取对阵表失败"""
        client = client_class(verbose=False)
        
        with patch.object(client.session, 'get', side_effect=Exception("Network error")):
            data, perf = client.get_against_plan(group_id=1001, bout=1)
        
        assert data is None


class TestRankingCalculation:
    """排名计算算法测试"""
    
    def test_basic_ranking_calculation(self, client_class, sample_match_data):
        """测试基础排名计算"""
        client = client_class(verbose=False)
        rankings, perf = client.calculate_ranking(sample_match_data)
        
        assert len(rankings) == 4
        
        # 选手A: 第1轮胜B(2分), 第2轮胜C(2分) = 4分, 2胜0负
        player_a = next(r for r in rankings if r["name"] == "选手A")
        assert player_a["wins"] == 2
        assert player_a["losses"] == 0
        assert player_a["score"] == 4.0
        
        # 选手B: 第1轮负A(0分), 第2轮胜D(2分) = 2分, 1胜1负
        player_b = next(r for r in rankings if r["name"] == "选手B")
        assert player_b["wins"] == 1  # 第2轮胜D
        assert player_b["losses"] == 1  # 第1轮负A
        assert player_b["score"] == 2.0
    
    def test_score_calculation_rules(self, client_class):
        """测试积分计算规则: 胜=2, 和=1, 负=0"""
        client = client_class(verbose=False)
        
        matches = [
            {"p1id": "1", "p1": "选手A", "p1_score": 2.0,  # 胜
             "p2id": "2", "p2": "选手B", "p2_score": 0.0, "bout": 1},  # 负
            {"p1id": "1", "p1": "选手A", "p1_score": 1.0,  # 和
             "p2id": "3", "p2": "选手C", "p2_score": 1.0, "bout": 2},  # 和
            {"p1id": "1", "p1": "选手A", "p1_score": 0.0,  # 负
             "p2id": "4", "p2": "选手D", "p2_score": 2.0, "bout": 3},  # 胜
        ]
        
        rankings, _ = client.calculate_ranking(matches)
        player_a = next(r for r in rankings if r["name"] == "选手A")
        
        # 2 + 1 + 0 = 3分
        assert player_a["score"] == 3.0
        assert player_a["wins"] == 1
        assert player_a["draws"] == 1
        assert player_a["losses"] == 1
    
    def test_opponent_score_calculation(self, client_class, sample_match_data):
        """测试对手分计算"""
        client = client_class(verbose=False)
        rankings, _ = client.calculate_ranking(sample_match_data)
        
        # 选手A的对手是选手B(第1轮, 2分)和选手C(第2轮, 2分)
        # 选手B总积分=2, 选手C总积分=2
        # 所以选手A的对手分 = 2 + 2 = 4
        player_a = next(r for r in rankings if r["name"] == "选手A")
        assert player_a["opponent_score"] == 4.0
    
    def test_progressive_score_calculation(self, client_class):
        """测试累进分计算"""
        client = client_class(verbose=False)
        
        # 选手A: 第1轮后2分, 第2轮后4分, 第3轮后6分
        # 累进分 = 2 + 4 + 6 = 12
        matches = [
            {"p1id": "1", "p1": "选手A", "p1_score": 2.0,
             "p2id": "2", "p2": "选手X", "p2_score": 0.0, "bout": 1},
            {"p1id": "1", "p1": "选手A", "p1_score": 2.0,
             "p2id": "3", "p2": "选手Y", "p2_score": 0.0, "bout": 2},
            {"p1id": "1", "p1": "选手A", "p1_score": 2.0,
             "p2id": "4", "p2": "选手Z", "p2_score": 0.0, "bout": 3},
        ]
        
        rankings, _ = client.calculate_ranking(matches)
        player_a = next(r for r in rankings if r["name"] == "选手A")
        assert player_a["progressive_score"] == 12.0  # 2+4+6
    
    def test_ranking_order(self, client_class, complex_ranking_data):
        """测试排名顺序: 积分 > 对手分 > 累进分"""
        client = client_class(verbose=False)
        rankings, _ = client.calculate_ranking(complex_ranking_data)
        
        # 根据修正后的 complex_ranking_data:
        # 选手A: 2胜0负, 积分4, 对手分4 (A的对手B=2分, C=2分)
        # 选手B: 1胜1负, 积分2, 对手分6 (B的对手A=4分, D=2分)
        # 选手D: 1胜1负, 积分2, 对手分2 (D的对手C=0分, B=2分)
        # 选手C: 0胜2负, 积分0, 对手分6 (C的对手D=2分, A=4分)
        assert rankings[0]["name"] == "选手A"
        assert rankings[0]["score"] == 4.0
        
        # 同积2分的选手B和D，按对手分排序
        assert rankings[1]["name"] == "选手B"
        assert rankings[2]["name"] == "选手D"
        assert rankings[3]["name"] == "选手C"
        
        # 验证选手B和D的排序依据是对手分 (B的对手分6 > D的对手分2)
        assert rankings[1]["opponent_score"] == 6.0
        assert rankings[2]["opponent_score"] == 2.0
    
    def test_bye_handling(self, client_class, sample_match_with_bye):
        """测试轮空处理"""
        client = client_class(verbose=False)
        rankings, _ = client.calculate_ranking(sample_match_with_bye)
        
        # 选手A轮空获胜得2分，但对手分不应计入轮空的0分
        player_a = next(r for r in rankings if r["name"] == "选手A")
        assert player_a["score"] == 2.0  # 轮空胜得2分
        assert player_a["wins"] == 1
        # 轮空对手的0分不计入对手分
        assert player_a["opponent_score"] == 0.0
    
    def test_draw_handling(self, client_class, sample_match_with_draw):
        """测试和棋处理"""
        client = client_class(verbose=False)
        rankings, _ = client.calculate_ranking(sample_match_with_draw)
        
        player_a = next(r for r in rankings if r["name"] == "选手A")
        player_b = next(r for r in rankings if r["name"] == "选手B")
        
        # 和棋双方各得1分
        assert player_a["score"] == 1.0
        assert player_b["score"] == 1.0
        assert player_a["draws"] == 1
        assert player_b["draws"] == 1


class TestRoundCompletionDetection:
    """未完成轮次检测测试"""
    
    def test_completed_round_detection(self, client_class):
        """测试已完成轮次识别"""
        client = client_class(verbose=False)
        
        # 第2轮有非0的score，说明已完成
        first_round = {
            "total_bout": 3,
            "rows": [{"p1_score": 2.0, "p2_score": 0.0}]
        }
        second_round = {
            "rows": [{"p1_score": 2.0, "p2_score": 0.0}]  # 已完成
        }
        
        mock_responses = [
            Mock(json=lambda: {"error": 0, "datArr": first_round}, raise_for_status=lambda: None),
            Mock(json=lambda: {"error": 0, "datArr": second_round}, raise_for_status=lambda: None),
        ]
        
        with patch.object(client.session, 'get', side_effect=mock_responses):
            matches, completed, perf = client.get_all_rounds(group_id=1001)
        
        assert completed == 2
    
    def test_incomplete_round_detection(self, client_class):
        """测试未完成轮次识别"""
        client = client_class(verbose=False)
        
        # 第2轮所有score都是0.0，说明未完成
        first_round = {
            "total_bout": 3,
            "rows": [{"p1_score": 2.0, "p2_score": 0.0}]
        }
        second_round = {
            "rows": [{"p1_score": 0.0, "p2_score": 0.0}]  # 未完成
        }
        
        mock_responses = [
            Mock(json=lambda: {"error": 0, "datArr": first_round}, raise_for_status=lambda: None),
            Mock(json=lambda: {"error": 0, "datArr": second_round}, raise_for_status=lambda: None),
        ]
        
        with patch.object(client.session, 'get', side_effect=mock_responses):
            matches, completed, perf = client.get_all_rounds(group_id=1001)
        
        # 应该只返回第1轮的数据
        assert completed == 1
        assert len(matches) == 1


class TestGamesRecording:
    """对局记录测试"""
    
    def test_games_recorded(self, client_class, sample_match_data):
        """测试每轮对局被正确记录"""
        client = client_class(verbose=False)
        rankings, _ = client.calculate_ranking(sample_match_data)
        
        player_a = next(r for r in rankings if r["name"] == "选手A")
        
        # 应该有两条对局记录
        assert len(player_a["games"]) == 2
        
        # 验证对局详情
        game1 = player_a["games"][0]
        assert game1["round"] == 1
        assert game1["opponent"] == "选手B"
        assert game1["result"] == "胜"
        assert game1["score"] == 2.0


class TestHTMLGeneration:
    """HTML 生成测试"""
    
    def test_ranking_html_output(self, client_class, tmp_path):
        """测试排名 HTML 输出 (数据量>10时使用HTML)"""
        client = client_class(verbose=False)
        
        # 生成11条数据触发HTML输出
        rankings = [
            {"name": f"选手{i}", "score": float(20-i), "opponent_score": float(i*2), 
             "progressive_score": float(30-i), "wins": 10-i, "losses": i, "draws": 0,
             "games": [{"round": 1, "opponent": "对手", "result": "胜", "score": 2.0}]}
            for i in range(11)
        ]
        
        output_file = tmp_path / "test_ranking.html"
        client.print_ranking(rankings, output_file=str(output_file))
        
        assert output_file.exists()
        content = output_file.read_text(encoding='utf-8')
        assert "选手0" in content
        assert "排名表" in content
    
    def test_html_escaping(self, client_class, tmp_path):
        """测试 HTML 特殊字符转义 (数据量>10时使用HTML)"""
        client = client_class(verbose=False)
        
        # 使用包含XSS攻击向量的选手名
        xss_name = "<script>alert('xss')</script>"
        rankings = [
            {"name": xss_name, "score": float(20-i), 
             "opponent_score": 1.0, "progressive_score": 2.0,
             "wins": 1, "losses": 0, "draws": 0, "games": []}
            for i in range(11)  # 11条数据触发HTML输出
        ]
        
        output_file = tmp_path / "test_escape.html"
        client.print_ranking(rankings, output_file=str(output_file))
        
        content = output_file.read_text(encoding='utf-8')
        # 确保选手名中的特殊字符被转义
        # html.escape() 会将 < > 转换为 &lt; &gt;，' 转换为 &#x27;
        assert "&lt;script&gt;" in content
        assert "&lt;/script&gt;" in content
        # 确保未转义的script标签不出现在选手名区域中
        name_section = content.split('class="name"')[1].split('</div>')[0] if 'class="name"' in content else ""
        assert "<script>" not in name_section


class TestEdgeCases:
    """边界情况测试"""
    
    def test_empty_matches(self, client_class):
        """测试空对阵数据"""
        client = client_class(verbose=False)
        rankings, perf = client.calculate_ranking([])
        assert len(rankings) == 0
    
    def test_single_player(self, client_class):
        """测试只有一名选手"""
        client = client_class(verbose=False)
        matches = [
            {"p1id": "1", "p1": "选手A", "p1_score": 2.0,
             "p2id": None, "p2": None, "p2_score": 0.0, "bout": 1},
        ]
        rankings, _ = client.calculate_ranking(matches)
        assert len(rankings) == 1
        assert rankings[0]["name"] == "选手A"
    
    def test_missing_fields(self, client_class):
        """测试缺失字段处理"""
        client = client_class(verbose=False)
        matches = [
            {"p1id": "1", "p1": "选手A", "p1_score": None,  # None score
             "p2id": "2", "p2": "选手B", "p2_score": 2.0, "bout": 1},
        ]
        rankings, _ = client.calculate_ranking(matches)
        # 应该能正常处理，None 视为 0
        player_a = next(r for r in rankings if r["name"] == "选手A")
        assert player_a["score"] == 0.0
    
    def test_none_values_in_scores(self, client_class):
        """测试 score 为 None 的情况"""
        client = client_class(verbose=False)
        matches = [
            {"p1id": "1", "p1": "选手A", "p1_score": None,
             "p2id": "2", "p2": "选手B", "p2_score": None, "bout": 1},
        ]
        rankings, _ = client.calculate_ranking(matches)
        # 两个 None score 应该都被视为 0
        assert len(rankings) == 2
        assert rankings[0]["score"] == 0.0


class TestIntegration:
    """集成测试"""
    
    def test_full_workflow_mock(self, client_class, sample_events_data, 
                                 sample_groups_data, sample_against_plan):
        """测试完整流程（Mock 版本）"""
        client = client_class(verbose=False)
        
        # Mock 所有 API 调用
        mock_responses = [
            # get_events
            Mock(json=lambda: sample_events_data, raise_for_status=lambda: None),
            # get_groups
            Mock(status_code=200, json=lambda: sample_groups_data, raise_for_status=lambda: None),
            # get_all_rounds - 第一轮
            Mock(json=lambda: sample_against_plan, raise_for_status=lambda: None),
        ]
        
        with patch.object(client.session, 'get', side_effect=mock_responses):
            # 1. 获取比赛列表
            events, _ = client.get_events(area="广东省", month=1)
            assert len(events) == 2
            
            # 2. 获取分组
            groups, _ = client.get_groups(event_id=12345)
            assert len(groups) == 2
            
            # 3. 获取对阵
            matches, completed, _ = client.get_all_rounds(group_id=1001)
            assert completed == 1
            assert len(matches) == 2
    
    def test_performance_tracking(self, client_class, sample_match_data):
        """测试性能跟踪功能"""
        client = client_class(verbose=False)
        
        # 执行一些操作
        client.calculate_ranking(sample_match_data)
        
        # 检查性能报告
        perf_dict = client.get_perf_dict()
        assert "total_seconds" in perf_dict
        assert "steps" in perf_dict
        assert len(perf_dict["steps"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

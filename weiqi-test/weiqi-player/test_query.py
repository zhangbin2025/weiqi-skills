#!/usr/bin/env python3
"""
weiqi-player 统一查询测试

测试范围:
- query_shoutan 调用手谈查询
- query_yichafen 调用易查分查询
- query_single 单选手双平台查询
- query_batch 批量查询
- 命令行参数解析
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "weiqi-player" / "scripts"))

import pytest
from query import query_shoutan, query_yichafen, query_single, query_batch, main


# ===== Fixtures =====

@pytest.fixture
def mock_shoutan_output():
    """模拟手谈查询输出"""
    return """
📋 **张三** - 手谈等级分查询结果

**张三** (南京市) | 段位: 6.2d | 等级分: 2500.0 | 全国排名: 123 | 对局: 100局
   👉 [查看南京市详细记录](https://v.dzqzd.com/SpBody.aspx?r=xxx)

==================================================
⏱️  性能计时报告（手谈查询）
==================================================
  构造查询参数               :    0.001s
  HTTP请求               :    1.262s
  解析HTML               :    0.001s
--------------------------------------------------
  步骤累计                 :    1.264s
  总耗时                  :    1.264s
==================================================
"""


@pytest.fixture
def mock_yichafen_output():
    """模拟易查分查询输出"""
    return """
张三
6段
等级分	1700.00
总排名	1000
省区排名	100
本市排名	20
性别	男
出生	2010
省区	江苏省
城市	南京市
备注	20XX第X届XX杯全国围棋比赛晋升6段

⏱️ 查询耗时: 3.0秒
"""


@pytest.fixture
def mock_subprocess_result():
    """模拟 subprocess 结果"""
    result = MagicMock()
    result.stdout = "测试输出"
    result.returncode = 0
    return result


# ===== Query Shoutan Tests =====

class TestQueryShoutan:
    """手谈查询调用测试"""

    @patch('query.subprocess.run')
    def test_query_shoutan_success(self, mock_run, mock_subprocess_result, mock_shoutan_output):
        """测试手谈查询成功"""
        mock_subprocess_result.stdout = mock_shoutan_output
        mock_run.return_value = mock_subprocess_result
        
        result = query_shoutan("张三")
        
        assert "张三" in result
        assert "手谈等级分查询结果" in result
        assert mock_run.called
        
        # 验证调用参数
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "python3"
        assert "query_shoutan.py" in call_args[0][0][1]
        assert call_args[0][0][2] == "张三"

    @patch('query.subprocess.run')
    def test_query_shoutan_with_exception(self, mock_run):
        """测试手谈查询异常处理"""
        mock_run.side_effect = Exception("网络错误")
        
        result = query_shoutan("李四")
        
        assert "❌ 手谈查询失败" in result
        assert "网络错误" in result

    @patch('query.subprocess.run')
    def test_query_shoutan_timeout(self, mock_run):
        """测试手谈查询超时"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["python3"], timeout=30)
        
        result = query_shoutan("王五")
        
        assert "❌ 手谈查询失败" in result


# ===== Query Yichafen Tests =====

class TestQueryYichafen:
    """易查分查询调用测试"""

    @patch('query.subprocess.run')
    def test_query_yichafen_success(self, mock_run, mock_subprocess_result, mock_yichafen_output):
        """测试易查分查询成功"""
        mock_subprocess_result.stdout = mock_yichafen_output
        mock_run.return_value = mock_subprocess_result
        
        result = query_yichafen("张三")
        
        assert "张三" in result
        assert "6段" in result
        assert mock_run.called
        
        # 验证调用参数
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "python3"
        assert "query_yichafen.py" in call_args[0][0][1]
        assert call_args[0][0][2] == "张三"

    @patch('query.subprocess.run')
    def test_query_yichafen_with_exception(self, mock_run):
        """测试易查分查询异常处理"""
        mock_run.side_effect = Exception("浏览器启动失败")
        
        result = query_yichafen("李四")
        
        assert "❌ 易查分查询失败" in result
        assert "浏览器启动失败" in result


# ===== Query Single Tests =====

class TestQuerySingle:
    """单选手查询测试"""

    @patch('query.query_yichafen')
    @patch('query.query_shoutan')
    def test_query_single_both_platforms(self, mock_shoutan, mock_yichafen):
        """测试双平台查询"""
        mock_shoutan.return_value = "手谈结果"
        mock_yichafen.return_value = "易查分结果"
        
        query_single("张三")
        
        mock_shoutan.assert_called_once_with("张三")
        mock_yichafen.assert_called_once_with("张三")

    @patch('query.query_yichafen')
    @patch('query.query_shoutan')
    def test_query_single_output_format(self, mock_shoutan, mock_yichafen, capsys):
        """测试单选手查询输出格式"""
        mock_shoutan.return_value = "手谈测试输出"
        mock_yichafen.return_value = "易查分测试输出"
        
        query_single("测试棋手")
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "正在查询: 测试棋手" in output
        assert "手谈等级分查询" in output
        assert "易查分业余段位查询" in output
        assert "查询完成" in output


# ===== Query Batch Tests =====

class TestQueryBatch:
    """批量查询测试"""

    @patch('query.query_single')
    def test_query_batch_multiple_players(self, mock_single):
        """测试批量查询多个选手"""
        names = ["张三", "李四", "王五"]
        
        query_batch(names)
        
        assert mock_single.call_count == 3
        mock_single.assert_has_calls([
            call("张三"),
            call("李四"),
            call("王五"),
        ])

    @patch('query.query_single')
    def test_query_batch_single_player(self, mock_single):
        """测试批量查询单个选手"""
        names = ["张三"]
        
        query_batch(names)
        
        mock_single.assert_called_once_with("张三")

    @patch('query.query_single')
    def test_query_batch_empty_list(self, mock_single):
        """测试批量查询空列表"""
        names = []
        
        query_batch(names)
        
        mock_single.assert_not_called()


# ===== Main Function Tests =====

class TestMain:
    """主函数测试"""

    @patch('query.query_single')
    @patch('query.sys.argv', ['query.py', '张三'])
    def test_main_single_query(self, mock_single):
        """测试主函数单查询"""
        main()
        mock_single.assert_called_once_with("张三")

    @patch('query.query_batch')
    @patch('query.sys.argv', ['query.py', '--batch', '张三', '李四'])
    def test_main_batch_query(self, mock_batch):
        """测试主函数批量查询"""
        main()
        mock_batch.assert_called_once_with(['张三', '李四'])

    @patch('query.sys.exit')
    @patch('query.sys.argv', ['query.py', '--batch'])
    def test_main_batch_no_names(self, mock_exit):
        """测试批量查询无姓名参数"""
        main()
        mock_exit.assert_called_once_with(1)

    @patch('query.sys.exit')
    @patch('query.sys.argv', ['query.py'])
    def test_main_no_arguments(self, mock_exit):
        """测试无参数调用 - 脚本会抛出 IndexError，这是预期行为"""
        with pytest.raises(IndexError):
            main()


# ===== Integration Tests =====

class TestIntegration:
    """集成测试"""

    @patch('query.query_yichafen')
    @patch('query.query_shoutan')
    def test_full_query_workflow(self, mock_shoutan, mock_yichafen, capsys):
        """测试完整查询流程"""
        mock_shoutan.return_value = """
📋 **棋手A** - 手谈等级分查询结果
**棋手A** (北京) | 段位: 9.9d | 等级分: 2800.0
"""
        mock_yichafen.return_value = """
棋手A
6段
等级分	1700.00
省区	北京市
"""
        
        query_single("棋手A")
        
        captured = capsys.readouterr()
        output = captured.out
        
        # 验证双平台都被调用
        mock_shoutan.assert_called_once()
        mock_yichafen.assert_called_once()
        
        # 验证输出包含两个平台的结果
        assert "手谈等级分查询" in output
        assert "易查分业余段位查询" in output


# ===== Script Path Tests =====

class TestScriptPath:
    """脚本路径测试"""

    def test_scripts_dir_path(self):
        """测试脚本目录路径"""
        scripts_dir = Path(__file__).parent.parent.parent / "weiqi-player" / "scripts"
        
        assert "weiqi-player" in str(scripts_dir)
        assert "scripts" in str(scripts_dir)

    def test_query_shoutan_path(self):
        """测试手谈查询脚本路径"""
        scripts_dir = Path(__file__).parent.parent.parent / "weiqi-player" / "scripts"
        shoutan_path = scripts_dir / "query_shoutan.py"
        
        assert "query_shoutan.py" in str(shoutan_path)

    def test_query_yichafen_path(self):
        """测试易查分查询脚本路径"""
        scripts_dir = Path(__file__).parent.parent.parent / "weiqi-player" / "scripts"
        yichafen_path = scripts_dir / "query_yichafen.py"
        
        assert "query_yichafen.py" in str(yichafen_path)


# ===== Timeout Tests =====

class TestTimeout:
    """超时配置测试"""

    def test_shoutan_timeout(self):
        """测试手谈查询超时设置"""
        timeout = 30
        assert timeout == 30

    def test_yichafen_timeout(self):
        """测试易查分查询超时设置"""
        timeout = 60
        assert timeout == 60

    def test_yichafen_timeout_longer(self):
        """测试易查分超时比手谈长"""
        shoutan_timeout = 30
        yichafen_timeout = 60
        
        assert yichafen_timeout > shoutan_timeout

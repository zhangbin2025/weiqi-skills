"""
weiqi-sgf 测试配置

仅保留 SGF Parser 单元测试
"""

import pytest
import sys
import os

# 添加 weiqi-sgf 脚本路径
sys.path.insert(0, '/root/.openclaw/workspace/weiqi-sgf/scripts')


# 测试用的 SGF 数据
SIMPLE_SGF = """(;GM[1]FF[4]SZ[19]PB[黑棋]PW[白棋];B[pd];W[dp];B[pp];W[dd];B[pj];W[nc];B[pf];W[kc])"""

VARIATIONS_SGF = """(;GM[1]FF[4]SZ[19]PB[柯洁]PW[申真谞]EV[第28届LG杯决赛];B[pd]C[jueyi黑62%]
  (;W[dp]C[jueyi黑58%];B[pp];W[dd])
  (;W[dd]C[jueyi黑65%]N[小雪崩];B[dp];W[cc])
  (;W[pp]C[jueyi黑38%]N[超高目];B[dp]))"""

HANDICAP_SGF = """(;GM[1]FF[4]SZ[19]PB[黑棋]PW[白棋]HA[4]AB[dd][pd][dp][pp];W[qf])"""

EMPTY_SGF = """(;GM[1]FF[4]SZ[19]PB[黑棋]PW[白棋])"""


@pytest.fixture
def simple_sgf():
    """简单棋谱（无变化图）"""
    return SIMPLE_SGF


@pytest.fixture
def variations_sgf():
    """带变化图的棋谱"""
    return VARIATIONS_SGF


@pytest.fixture
def handicap_sgf():
    """让子棋谱"""
    return HANDICAP_SGF


@pytest.fixture
def empty_sgf():
    """空棋谱"""
    return EMPTY_SGF

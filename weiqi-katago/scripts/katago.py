#!/usr/bin/env python3
"""
KataGo 引擎封装 - 提供简洁的分析接口
"""

import json
import subprocess
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import threading
import time


@dataclass
class AnalysisResult:
    """分析结果"""
    move: str                      # 坐标，如 "pd"
    winrate: float                 # 胜率 (0-100)
    score: float                   # 目差 (负数表示黑棋落后)
    visits: int                    # 搜索次数
    best_moves: List[Dict]         # 推荐点列表
    pv: List[str]                  # 主变化序列


@dataclass
class MoveAnalysis:
    """单步分析结果"""
    move_num: int                  # 手数
    player: str                    # 执子方 B/W
    coord: str                     # 坐标
    winrate: float                 # 这手后的胜率
    score: float                   # 这手后的目差
    winrate_delta: float           # 胜率变化 (与上一手相比)
    score_delta: float             # 目差变化
    best_move: str                 # AI推荐点
    best_winrate: float            # AI推荐后的胜率
    is_mistake: bool               # 是否恶手
    mistake_severity: str          # 严重程度 (minor/significant/critical)


class SGFParser:
    """SGF解析器"""
    
    COORD_MAP = {}
    
    @classmethod
    def _init_coord_map(cls):
        """初始化坐标映射"""
        if cls.COORD_MAP:
            return
        letters = 'abcdefghijklmnopqrstuvwxyz'
        for i in range(19):
            for j in range(19):
                cls.COORD_MAP[letters[i] + letters[j]] = (i, j)
    
    @staticmethod
    def parse(sgf_content: str) -> List[Tuple[str, str]]:
        """
        解析SGF，返回主分支着法列表 [(player, coord), ...]
        自动排除变化图（Variation）中的着法
        coord格式: 如 "pd" 表示小目
        """
        SGFParser._init_coord_map()
        
        # 方法1: 提取所有着法，然后取最长的黑白交替序列（主分支）
        all_moves = []
        pattern = r';([BW])\[([a-z]{0,2})\]'
        
        for match in re.finditer(pattern, sgf_content):
            player = match.group(1)
            coord = match.group(2)
            all_moves.append((player, coord))
        
        # 找到主分支：最长的黑白交替序列
        # 棋谱中变化图的着法会重复颜色（如连续两个黑棋）
        main_branch = []
        prev_player = None
        
        for player, coord in all_moves:
            if prev_player is None or player != prev_player:
                main_branch.append((player, coord))
                prev_player = player
            else:
                # 出现连续同色，说明进入变化图，停止
                break
        
        return main_branch
    
    @staticmethod
    def to_gtp_coord(sgf_coord: str) -> str:
        """SGF坐标转GTP坐标 (如 "pd" -> "Q16")"""
        if not sgf_coord or len(sgf_coord) != 2:
            return "pass"
        
        x = ord(sgf_coord[0]) - ord('a')
        y = ord(sgf_coord[1]) - ord('a')
        
        # GTP: 列字母(A-T, 无I) + 行数字(19-1)
        if x >= 8:  # 跳过 I
            x += 1
        col = chr(ord('A') + x)
        row = 19 - y
        
        return f"{col}{row}"
    
    @staticmethod
    def to_sgf_coord(gtp_coord: str) -> str:
        """GTP坐标转SGF坐标 (如 "Q16" -> "pd")"""
        if gtp_coord.lower() == "pass":
            return ""
        
        match = re.match(r'([A-T])(\d+)', gtp_coord.upper())
        if not match:
            return ""
        
        col = match.group(1)
        row = int(match.group(2))
        
        x = ord(col) - ord('A')
        if x >= 9:  # 跳过了 I
            x -= 1
        y = 19 - row
        
        return chr(ord('a') + x) + chr(ord('a') + y)


class KataGoEngine:
    """KataGo分析引擎"""
    
    def __init__(self, bin_path: str, model_path: str, config_path: str):
        self.bin_path = bin_path
        self.model_path = model_path
        self.config_path = config_path
        self.process = None
        self.lock = threading.Lock()
    
    def start(self) -> bool:
        """启动分析引擎"""
        try:
            cmd = [
                self.bin_path,
                "analysis",
                "-config", self.config_path,
                "-model", self.model_path
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # 等待引擎启动
            time.sleep(1)
            
            if self.process.poll() is not None:
                stderr = self.process.stderr.read()
                raise RuntimeError(f"KataGo启动失败: {stderr}")
            
            return True
            
        except Exception as e:
            print(f"启动KataGo失败: {e}")
            return False
    
    def stop(self):
        """停止引擎"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
    
    def analyze_position(self, moves: List[Tuple[str, str]], 
                        komi: float = 7.5,
                        max_visits: int = 500,
                        analyze_turn: Optional[str] = None) -> Optional[AnalysisResult]:
        """
        分析当前局面
        
        Args:
            moves: 已进行的着法列表 [(B, "pd"), (W, "dp"), ...]
            komi: 贴目
            max_visits: 最大搜索次数
            analyze_turn: 分析哪一方的视角 (None表示当前轮到的一方)
        
        Returns:
            AnalysisResult 或 None
        """
        if not self.process or self.process.poll() is not None:
            if not self.start():
                return None
        
        # 构建请求 - 将 SGF 坐标转换为 GTP 坐标
        def sgf_to_gtp(sgf_coord: str) -> str:
            if not sgf_coord or len(sgf_coord) != 2:
                return "pass"
            x = ord(sgf_coord[0]) - ord('a')
            y = ord(sgf_coord[1]) - ord('a')
            if x >= 8:  # 跳过 I
                x += 1
            col = chr(ord('A') + x)
            row = 19 - y
            return f"{col}{row}"
        
        request = {
            "id": f"analysis_{int(time.time() * 1000)}",
            "moves": [[p, sgf_to_gtp(c)] for p, c in moves],
            "rules": "chinese",
            "komi": komi,
            "maxVisits": max_visits,
            "includePolicy": False,
            "includeOwnership": False,
            "boardXSize": 19,
            "boardYSize": 19,
        }
        
        if analyze_turn:
            request["analyzeTurns"] = [analyze_turn]
        
        try:
            with self.lock:
                # 发送请求
                request_json = json.dumps(request)
                self.process.stdin.write(request_json + "\n")
                self.process.stdin.flush()
                
                # 读取响应
                response_line = self.process.stdout.readline()
                if not response_line:
                    return None
                
                response = json.loads(response_line)
                
                return self._parse_analysis_response(response)
                
        except Exception as e:
            print(f"分析失败: {e}")
            return None
    
    def _parse_analysis_response(self, response: Dict) -> Optional[AnalysisResult]:
        """解析分析响应"""
        try:
            root_info = response.get("rootInfo", {})
            move_infos = response.get("moveInfos", [])
            
            if not move_infos:
                return None
            
            # 当前局面信息
            current_move = response.get("turnNumber", 0)
            
            # 胜率转换：KataGo输出的是黑棋视角
            winrate = root_info.get("winrate", 0.5) * 100
            score = root_info.get("scoreLead", 0)
            visits = root_info.get("visits", 0)
            
            # 推荐点
            best_moves = []
            for info in move_infos[:5]:  # 取前5个
                move = info.get("move", "")
                move_winrate = info.get("winrate", 0.5) * 100
                move_score = info.get("scoreLead", 0)
                move_visits = info.get("visits", 0)
                
                # 主变化
                pv = info.get("pv", [])
                
                best_moves.append({
                    "move": move,
                    "winrate": move_winrate,
                    "score": move_score,
                    "visits": move_visits,
                    "pv": pv
                })
            
            # 主变化序列
            pv = move_infos[0].get("pv", []) if move_infos else []
            
            return AnalysisResult(
                move="",
                winrate=winrate,
                score=score,
                visits=visits,
                best_moves=best_moves,
                pv=pv
            )
            
        except Exception as e:
            print(f"解析响应失败: {e}")
            return None
    
    def analyze_game(self, sgf_content: str,
                    start_move: int = 0,
                    end_move: Optional[int] = None,
                    interval: int = 1,
                    progress_callback = None) -> List[MoveAnalysis]:
        """
        分析整盘棋
        
        Args:
            sgf_content: SGF内容
            start_move: 开始分析的手数
            end_move: 结束分析的手数
            interval: 间隔几手分析一次
            progress_callback: 进度回调函数(current, total)
        
        Returns:
            每手的分析结果列表
        """
        moves = SGFParser.parse(sgf_content)
        total_moves = len(moves)
        
        if end_move is None or end_move > total_moves:
            end_move = total_moves
        
        results = []
        prev_winrate = 50.0  # 初始胜率
        
        for i in range(start_move, end_move, interval):
            if progress_callback:
                progress_callback(i - start_move, end_move - start_move)
            
            # 分析到第i手后的局面
            current_moves = moves[:i+1]
            if not current_moves:
                continue
            
            result = self.analyze_position(current_moves)
            if not result:
                continue
            
            player, coord = moves[i]
            
            # 计算胜率变化
            winrate_delta = result.winrate - prev_winrate
            # 如果当前是白棋回合，胜率应该从白棋视角计算
            if player == "W":
                winrate_delta = (100 - result.winrate) - (100 - prev_winrate)
            
            # 判断是否为恶手（胜率下降超过阈值）
            is_mistake = False
            severity = ""
            threshold = 5.0  # 5%阈值
            
            if abs(winrate_delta) > threshold:
                is_mistake = True
                if abs(winrate_delta) > 15:
                    severity = "critical"
                elif abs(winrate_delta) > 10:
                    severity = "significant"
                else:
                    severity = "minor"
            
            # 获取AI推荐
            best_move = ""
            best_winrate = result.winrate
            if result.best_moves:
                best = result.best_moves[0]
                best_move = best["move"]
                best_winrate = best["winrate"]
            
            analysis = MoveAnalysis(
                move_num=i + 1,
                player=player,
                coord=coord,
                winrate=result.winrate if player == "B" else 100 - result.winrate,
                score=result.score if player == "B" else -result.score,
                winrate_delta=winrate_delta,
                score_delta=0,  # 暂不计算
                best_move=best_move,
                best_winrate=best_winrate,
                is_mistake=is_mistake,
                mistake_severity=severity
            )
            
            results.append(analysis)
            prev_winrate = result.winrate if player == "B" else 100 - result.winrate
        
        return results
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


class KataGoManager:
    """KataGo管理器 - 简化调用"""
    
    def __init__(self):
        self.engine = None
        self._find_paths()
    
    def _find_paths(self):
        """查找KataGo路径"""
        # 搜索KataGo
        self.katago_path = self._find_katago()
        # 搜索模型
        self.model_path = self._find_model()
        # 搜索配置
        self.config_path = self._find_config()
    
    def _find_katago(self) -> Optional[str]:
        """查找KataGo可执行文件"""
        paths = [
            "katago",
            "/usr/local/bin/katago",
            "/usr/bin/katago",
            os.path.expanduser("~/.local/bin/katago"),
            os.path.expanduser("~/katago"),
        ]
        
        for path in paths:
            try:
                result = subprocess.run([path, "version"], 
                                      capture_output=True, timeout=3)
                if result.returncode == 0:
                    return path
            except:
                continue
        return None
    
    def _find_model(self) -> Optional[str]:
        """查找模型文件"""
        search_paths = [
            Path("."),
            Path.home(),
            Path.home() / "katago",
            Path.home() / ".katago",
        ]
        
        for path in search_paths:
            if not path.exists():
                continue
            # 优先查找小模型（轻量级）
            for pattern in ["*.txt.gz", "*.bin.gz"]:
                models = sorted(path.glob(pattern), 
                               key=lambda x: x.stat().st_size)
                if models:
                    # 返回最小的模型（轻量级优先）
                    return str(models[0])
        return None
    
    def _find_config(self) -> Optional[str]:
        """查找配置文件"""
        paths = [
            "analysis.cfg",
            "katago.cfg",
            "/usr/local/etc/katago/analysis.cfg",
            os.path.expanduser("~/.katago.cfg"),
            os.path.expanduser("~/analysis.cfg"),
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
        return None
    
    def is_ready(self) -> bool:
        """检查是否就绪"""
        return all([self.katago_path, self.model_path, self.config_path])
    
    def get_status(self) -> Dict:
        """获取状态信息"""
        return {
            "katago": self.katago_path or "未找到",
            "model": self.model_path or "未找到",
            "config": self.config_path or "未找到",
            "ready": self.is_ready()
        }
    
    def create_engine(self) -> Optional[KataGoEngine]:
        """创建引擎实例"""
        if not self.is_ready():
            return None
        
        return KataGoEngine(
            self.katago_path,
            self.model_path,
            self.config_path
        )


if __name__ == "__main__":
    # 测试
    manager = KataGoManager()
    print("KataGo状态:", manager.get_status())
    
    # 测试SGF解析
    test_sgf = "(;GM[1]SZ[19];B[pd];W[dp];B[pp];W[dd])"
    moves = SGFParser.parse(test_sgf)
    print(f"解析到 {len(moves)} 手:", moves)

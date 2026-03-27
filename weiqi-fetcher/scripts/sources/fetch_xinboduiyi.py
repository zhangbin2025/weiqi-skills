"""
新博对弈 (xinboduiyi.com) 棋谱下载器
使用 Playwright 抓取 WebSocket 数据
"""

import json
import re
import time
from urllib.parse import urlparse, parse_qs
from typing import Optional, List, Tuple

from .base import BaseSourceFetcher, FetchResult, register_fetcher


@register_fetcher
class XinboduiyiFetcher(BaseSourceFetcher):
    """新博对弈棋谱下载器"""
    
    name = "xinboduiyi"
    display_name = "新博对弈"
    
    url_patterns = [
        r'xinboduiyi\.com.*?[?&]gameid=(\d+)',
        r'xinboduiyi\.com/play-room.*?[?&]id=(\d+)',
        r'xinboduiyi\.com.*?[?&]gamekey=([^&]+)',
    ]
    
    url_examples = [
        "https://www.xinboduiyi.com/play-room?id={GAME_ID}",
        "https://weiqi.xinboduiyi.com/golive/index.html#/?gamekey={GAME_KEY}",
    ]
    
    def fetch(self, url: str, output_path: str = None) -> FetchResult:
        """下载棋谱"""
        start_time = time.time()
        
        game_id = self.extract_id(url)
        if not game_id:
            return FetchResult(
                success=False,
                source=self.name,
                url=url,
                sgf_content=None,
                output_path=None,
                metadata={},
                error="无法从URL提取对局ID"
            )
        
        try:
            # 使用 Playwright 抓取 WebSocket 数据
            result = self._fetch_with_playwright(url, game_id)
            
            if not result:
                return FetchResult(
                    success=False,
                    source=self.name,
                    url=url,
                    sgf_content=None,
                    output_path=None,
                    metadata={},
                    error="Playwright 抓取数据失败"
                )
            
            # 解析分谱数据
            sgf_content, metadata = self._parse_game_data(result, game_id)
            
            if not sgf_content:
                return FetchResult(
                    success=False,
                    source=self.name,
                    url=url,
                    sgf_content=None,
                    output_path=None,
                    metadata=result,
                    error="解析棋谱数据失败"
                )
            
            # 保存文件
            if not output_path:
                output_path = self.get_default_output_path(game_id.replace('/', '_'))
            
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(sgf_content)
            
            elapsed = time.time() - start_time
            
            return FetchResult(
                success=True,
                source=self.name,
                url=url,
                sgf_content=sgf_content,
                output_path=output_path,
                metadata=metadata,
                timing={"total_seconds": elapsed}
            )
            
        except Exception as e:
            import traceback
            return FetchResult(
                success=False,
                source=self.name,
                url=url,
                sgf_content=None,
                output_path=None,
                metadata={},
                error=f"获取失败: {str(e)}\\n{traceback.format_exc()}"
            )
    
    def _fetch_with_playwright(self, url: str, game_id: str) -> Optional[dict]:
        """使用 Playwright 抓取 WebSocket 数据"""
        try:
            from playwright.sync_api import sync_playwright
            
            ws_messages = []
            game_data = None
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                # 监听 WebSocket
                def handle_ws(ws):
                    print(f"WebSocket opened: {ws.url}")
                    
                    def handle_message(msg):
                        try:
                            data = json.loads(msg)
                            ws_messages.append(data)
                            print(f"WS msg: cmd={data.get('cmd')}")
                            
                            # 检查是否是游戏数据 (cmd:6)
                            if data.get('cmd') == '6' and data.get('data'):
                                nonlocal game_data
                                game_data = data['data']
                        except:
                            pass
                    
                    ws.on("framereceived", handle_message)
                
                page = context.new_page()
                page.on("websocket", handle_ws)
                
                # 访问页面
                print(f"Navigating to {url}")
                page.goto(url, wait_until="domcontentloaded")
                
                # 等待 WebSocket 数据
                for i in range(30):  # 最多等待30秒
                    if game_data:
                        break
                    time.sleep(1)
                
                browser.close()
            
            return game_data
            
        except Exception as e:
            print(f"Playwright error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_game_data(self, data: dict, game_id: str) -> Tuple[Optional[str], dict]:
        """
        解析游戏数据生成 SGF
        """
        try:
            # 提取元数据
            metadata = {
                'game_id': game_id,
                'black_name': data.get('black_name', '黑方'),
                'white_name': data.get('white_name', '白方'),
                'black_rank': data.get('black_level', ''),
                'white_rank': data.get('white_level', ''),
                'result': data.get('result', ''),
                'date': data.get('date', ''),
                'game_name': data.get('game_name', ''),
            }
            
            # 获取分谱数据
            part_qipu = data.get('part_qipu', [])
            if not part_qipu:
                # 尝试其他字段
                part_qipu = data.get('qipu', [])
            
            if not part_qipu:
                print(f"No part_qipu found. Available keys: {list(data.keys())}")
                return None, metadata
            
            print(f"Found {len(part_qipu)} parts")
            
            # 解析所有着法
            moves = self._parse_moves_from_parts(part_qipu)
            
            if not moves:
                return None, metadata
            
            print(f"Parsed {len(moves)} moves")
            
            # 生成 SGF
            sgf = self._generate_sgf(metadata, moves)
            
            return sgf, metadata
            
        except Exception as e:
            print(f"Parse error: {e}")
            import traceback
            traceback.print_exc()
            return None, {}
    
    def _parse_moves_from_parts(self, part_qipu: List[dict]) -> List[Tuple[str, str]]:
        """从分谱解析着法 - 只取 part_id=0 的分谱"""
        # 只使用 part_id=0 的分谱
        for part in part_qipu:
            part_id = part.get('part_id', 0)
            if part_id == 0:
                qipu_str = part.get('latest_full_qipu', '')
                if qipu_str:
                    print(f"Using Part 0: {len(qipu_str)} chars")
                    return self._parse_qipu_string(qipu_str)
        
        return []
    
    def _parse_qipu_string(self, qipu_str: str) -> List[Tuple[str, str]]:
        """
        解析着法字符串 (part_id=0)
        
        格式: B[CD];W[QR];B[RD];... (分号分隔的SGF-like格式)
        每个坐标两个字母：第一个是纵坐标，第二个是横坐标
        """
        moves = []
        
        # 分割成单独的着法
        # 格式: B[CD] 或 W[QR]
        pattern = r'([BW])\[([A-Z]{2})\]'
        matches = re.findall(pattern, qipu_str)
        
        for color, coord in matches:
            sgf_coord = self._convert_coord(coord)
            if sgf_coord:
                moves.append((color, sgf_coord))
        
        return moves
    
    def _convert_coord(self, coord: str) -> Optional[str]:
        """
        将新博对弈坐标转换为 SGF 坐标
        
        新博格式: 两个字母，第一个字母是纵坐标，第二个是横坐标
        例: B[CD] -> C是纵坐标，D是横坐标
        
        坐标映射规则:
        第一个字母(纵坐标 -> SGF y): A=a, B=b, C=c, D=d, E=e, F=f, G=g, H=h, J=i, K=j, 
                                   L=k, M=l, N=m, O=n, P=o, Q=p, R=q, S=r, T=s
        第二个字母(横坐标 -> SGF x): T=a, S=b, R=c, Q=d, P=e, O=f, N=g, M=h, L=i, K=j, 
                                   J=k, H=l, G=m, F=n, E=o, D=p, C=q, B=r, A=s
        """
        if len(coord) != 2:
            return None
        
        try:
            c1, c2 = coord[0].upper(), coord[1].upper()
            
            # 第一个字母是纵坐标 -> SGF y
            vert_map = {
                'A': 'a', 'B': 'b', 'C': 'c', 'D': 'd', 'E': 'e',
                'F': 'f', 'G': 'g', 'H': 'h', 'J': 'i', 'K': 'j',
                'L': 'k', 'M': 'l', 'N': 'm', 'O': 'n', 'P': 'o',
                'Q': 'p', 'R': 'q', 'S': 'r', 'T': 's'
            }
            
            # 第二个字母是横坐标 -> SGF x
            horiz_map = {
                'T': 'a', 'S': 'b', 'R': 'c', 'Q': 'd', 'P': 'e',
                'O': 'f', 'N': 'g', 'M': 'h', 'L': 'i', 'K': 'j',
                'J': 'k', 'H': 'l', 'G': 'm', 'F': 'n', 'E': 'o',
                'D': 'p', 'C': 'q', 'B': 'r', 'A': 's'
            }
            
            sgf_y = vert_map.get(c1)  # 第一个字母 -> y
            sgf_x = horiz_map.get(c2)  # 第二个字母 -> x
            
            if not sgf_x or not sgf_y:
                return None
            
            return sgf_x + sgf_y
            
        except Exception as e:
            print(f"Coord conversion error: {coord} - {e}")
            return None
    
    def _generate_sgf(self, metadata: dict, moves: List[Tuple[str, str]]) -> str:
        """生成 SGF 文件内容"""
        lines = [
            "(;GM[1]FF[4]",
            f"SZ[19]",
            f"PB[{metadata.get('black_name', '黑方')}]",
            f"PW[{metadata.get('white_name', '白方')}]",
        ]
        
        if metadata.get('black_rank'):
            lines.append(f"BR[{metadata['black_rank']}]")
        if metadata.get('white_rank'):
            lines.append(f"WR[{metadata['white_rank']}]")
        if metadata.get('result'):
            lines.append(f"RE[{metadata['result']}]")
        if metadata.get('date'):
            lines.append(f"DT[{metadata['date']}]")
        
        lines.append(f"EV[新博对弈]")
        
        # 添加着法
        for color, coord in moves:
            lines.append(f";{color}[{coord}]")
        
        lines.append(")")
        
        return "\n".join(lines)

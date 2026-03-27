"""野狐围棋棋谱下载器"""

import requests
import re
from .base import BaseSourceFetcher, FetchResult, register_fetcher

@register_fetcher
class FoxwqFetcher(BaseSourceFetcher):
    name = "foxwq"
    display_name = "野狐围棋"
    url_patterns = [
        r'h5\.foxwq\.com/yehunewshare.*chessid=(\d+)',
        r'www\.foxwq\.com/.*chessid=(\d+)',
        r'foxwq\.com.*chessid=(\d+)',
    ]
    url_examples = [
        "https://h5.foxwq.com/yehunewshare/?chessid={CHESS_ID}",
    ]
    
    def fetch(self, url: str, output_path: str = None) -> FetchResult:
        import time
        timing = {}
        
        t0 = time.time()
        chess_id = self.extract_id(url)
        timing['extract_id'] = time.time() - t0
        
        if not chess_id:
            return FetchResult(
                success=False,
                source=self.name,
                url=url,
                sgf_content=None,
                output_path=None,
                error="无法从URL提取对局ID",
                timing=timing
            )
        
        # 尝试API模式（历史棋谱）
        t0 = time.time()
        result = self._fetch_api(chess_id)
        timing['api_fetch'] = time.time() - t0
        
        if result:
            # 保存文件
            if not output_path:
                output_path = self.get_default_output_path(chess_id)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result['sgf'])
            
            return FetchResult(
                success=True,
                source=self.name,
                url=url,
                sgf_content=result['sgf'],
                output_path=output_path,
                metadata=result['metadata'],
                timing=timing
            )
        
        return FetchResult(
            success=False,
            source=self.name,
            url=url,
            sgf_content=None,
            output_path=None,
            error="API获取失败，可能需要WebSocket模式（进行中对局）",
            timing=timing
        )
    
    def _fetch_api(self, chess_id: str) -> dict:
        """通过API获取历史棋谱"""
        # 获取棋谱数据
        api_url = f"https://h5.foxwq.com/yehuDiamond/chessbook_local/YHWQFetchChess?chessid={chess_id}"
        
        try:
            resp = requests.get(api_url, timeout=30)
            data = resp.json()
        except Exception as e:
            return None
        
        if data.get('result') != 0:
            return None
        
        sgf = data.get('chess', '')
        if not sgf:
            return None
        
        # 获取附加信息
        metadata = self._fetch_metadata(chess_id)
        
        return {
            'sgf': sgf,
            'metadata': metadata
        }
    
    def _fetch_metadata(self, chess_id: str) -> dict:
        """获取对局元数据"""
        url = f"https://h5.foxwq.com/yehuDiamond/chessbook_local/FetchChessSummaryByChessID?chessid={chess_id}"
        
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
        except:
            return {}
        
        if data.get('result') != 0:
            return {}
        
        info = data.get('data', {})
        return {
            'game_id': chess_id,
            'black_name': info.get('blackname', ''),
            'white_name': info.get('whitename', ''),
            'black_rank': info.get('blacklevel', ''),
            'white_rank': info.get('whitelevel', ''),
            'result': info.get('result', ''),
            'date': info.get('gamedate', ''),
            'moves_count': info.get('stepcount', 0),
        }

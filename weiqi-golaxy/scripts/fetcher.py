"""星阵围棋棋谱下载器 - 用于weiqi-fetcher集成"""

import re
import os
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from download import GolaxyDownloader

# 如果作为weiqi-fetcher的模块使用
try:
    from ..base import BaseSourceFetcher, FetchResult, register_fetcher
except ImportError:
    # 独立运行时的占位符
    class BaseSourceFetcher:
        name = ""
        display_name = ""
        url_patterns = []
        
        def fetch(self, url: str, output_path: str = None) -> 'FetchResult':
            raise NotImplementedError
    
    class FetchResult:
        def __init__(self, success, source, url, sgf_content, output_path, 
                     metadata=None, error=None, timing=None):
            self.success = success
            self.source = source
            self.url = url
            self.sgf_content = sgf_content
            self.output_path = output_path
            self.metadata = metadata or {}
            self.error = error
            self.timing = timing or {}
    
    def register_fetcher(cls):
        return cls


@register_fetcher
class GolaxyFetcher(BaseSourceFetcher):
    """星阵围棋棋谱下载器"""
    
    name = "golaxy"
    display_name = "星阵围棋"
    url_patterns = [
        r'19x19\.com.*sgf/(\d+)',
        r'golaxy.*sgf/(\d+)',
    ]
    url_examples = [
        "https://m.19x19.com/app/dark/zh/sgf/70307160",
        "https://www.19x19.com/app/dark/zh/sgf/70307160",
    ]
    
    def fetch(self, url: str, output_path: str = None) -> FetchResult:
        """提取SGF棋谱"""
        import time
        timing = {'start': time.time()}
        
        downloader = GolaxyDownloader()
        
        if not output_path:
            game_id = downloader.extract_id(url)
            output_path = f'/tmp/golaxy_{game_id}.sgf' if game_id else '/tmp/golaxy_download.sgf'
        
        timing['init'] = time.time() - timing['start']
        
        t0 = time.time()
        result = downloader.download(url, output_path)
        timing['download'] = time.time() - t0
        
        if not result['success']:
            return FetchResult(
                success=False,
                source=self.name,
                url=url,
                sgf_content=None,
                output_path=None,
                error=result['error'],
                timing=timing
            )
        
        # 读取生成的SGF
        t0 = time.time()
        with open(result['file'], 'r', encoding='utf-8') as f:
            sgf_content = f.read()
        timing['read'] = time.time() - t0
        
        timing['total'] = time.time() - timing['start']
        
        return FetchResult(
            success=True,
            source=self.name,
            url=url,
            sgf_content=sgf_content,
            output_path=result['file'],
            metadata=result['metadata'],
            timing=timing
        )


if __name__ == '__main__':
    # 测试
    fetcher = GolaxyFetcher()
    result = fetcher.fetch("https://m.19x19.com/app/dark/zh/sgf/70307160")
    
    if result.success:
        print(f"✅ 成功: {result.output_path}")
        print(f"元数据: {result.metadata}")
    else:
        print(f"❌ 失败: {result.error}")

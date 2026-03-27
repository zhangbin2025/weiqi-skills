#!/usr/bin/env python3
"""
星阵围棋棋谱下载器
从星阵围棋(19x19.com)分享链接提取SGF棋谱
"""

import re
import sys
import json
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class GolaxyDownloader:
    """星阵围棋棋谱下载器"""
    
    name = "golaxy"
    display_name = "星阵围棋"
    
    def __init__(self):
        self.timeout = 30000
        self.wait_time = 8000  # 等待页面加载时间(ms)
    
    def extract_id(self, url: str) -> Optional[str]:
        """从URL提取棋谱ID"""
        patterns = [
            r'/sgf/(\d+)',
            r'sgf/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def download(self, url: str, output_path: str = None) -> Dict:
        """
        下载棋谱
        
        Args:
            url: 星阵围棋分享链接
            output_path: 输出文件路径(可选)
            
        Returns:
            {
                'success': bool,
                'file': str,
                'metadata': dict,
                'error': str
            }
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {
                'success': False,
                'file': None,
                'metadata': None,
                'error': 'Playwright未安装。请运行: pip3 install playwright && playwright install chromium'
            }
        
        game_id = self.extract_id(url)
        if not game_id:
            return {
                'success': False,
                'file': None,
                'metadata': None,
                'error': '无法从URL提取棋谱ID'
            }
        
        if not output_path:
            output_path = f'/tmp/golaxy_{game_id}.sgf'
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 访问页面
                page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
                page.wait_for_timeout(self.wait_time)
                
                # 从localStorage获取数据
                engine_data = page.evaluate('''() => {
                    try {
                        const raw = localStorage.getItem('engine');
                        return raw ? JSON.parse(raw) : null;
                    } catch(e) {
                        return null;
                    }
                }''')
                
                browser.close()
                
                if not engine_data:
                    return {
                        'success': False,
                        'file': None,
                        'metadata': None,
                        'error': '未找到棋谱数据(localStorage.engine为空)'
                    }
                
                # 解析数据
                sgf_content = self._parse_to_sgf(engine_data)
                
                # 保存文件
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(sgf_content)
                
                # 提取元数据
                info = engine_data.get('sgfInfo', {})
                metadata = {
                    'black': info.get('pb', {}).get('value', ''),
                    'white': info.get('pw', {}).get('value', ''),
                    'black_rank': info.get('br', {}).get('value', ''),
                    'white_rank': info.get('wr', {}).get('value', ''),
                    'result': info.get('re', {}).get('value', ''),
                    'event': info.get('gn', {}).get('value', ''),
                    'date': info.get('dt', {}).get('value', ''),
                    'komi': info.get('km', {}).get('value', ''),
                    'board_size': engine_data.get('boardSize', 19),
                    'move_count': len(engine_data.get('sgf', '').split(','))
                }
                
                return {
                    'success': True,
                    'file': output_path,
                    'metadata': metadata,
                    'error': None
                }
                
        except Exception as e:
            return {
                'success': False,
                'file': None,
                'metadata': None,
                'error': f'下载失败: {str(e)}'
            }
    
    def _parse_to_sgf(self, engine_data: Dict) -> str:
        """将星阵数据转换为SGF格式"""
        # 提取坐标
        sgf_coords_str = engine_data.get('sgf', '')
        sgf_coords = sgf_coords_str.split(',') if sgf_coords_str else []
        
        # 提取信息
        info = engine_data.get('sgfInfo', {})
        board_size = int(engine_data.get('boardSize', 19))
        
        # 解析玩家信息
        black_name = info.get('pb', {}).get('value', '黑棋')
        white_name = info.get('pw', {}).get('value', '白棋')
        black_rank = info.get('br', {}).get('value', '')
        white_rank = info.get('wr', {}).get('value', '')
        result = info.get('re', {}).get('value', '')
        game_name = info.get('gn', {}).get('value', '')
        date = info.get('dt', {}).get('value', '')
        komi = info.get('km', {}).get('value', '7.5')
        
        # 坐标转换函数
        def to_sgf_coord(val: str, size: int = 19) -> str:
            try:
                val_int = int(val)
                x = val_int % size
                y = val_int // size
                return chr(ord('a') + x) + chr(ord('a') + y)
            except:
                return ''
        
        # 生成着法
        moves = []
        for i, coord in enumerate(sgf_coords):
            if coord:
                sgf_coord = to_sgf_coord(coord, board_size)
                if sgf_coord:
                    color = 'B' if i % 2 == 0 else 'W'
                    moves.append(f";{color}[{sgf_coord}]")
        
        # 构建SGF
        sgf = f"""(;GM[1]FF[4]CA[UTF-8]AP[星阵围棋]SZ[{board_size}]
PB[{black_name}]BR[{black_rank}]
PW[{white_name}]WR[{white_rank}]
DT[{date}]EV[{game_name}]
KM[{komi}]RE[{result}]
{''.join(moves)}
)"""
        
        return sgf


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python3 download.py <URL> [输出文件]")
        print("示例: python3 download.py 'https://m.19x19.com/app/dark/zh/sgf/70307160'")
        sys.exit(1)
    
    url = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"🌐 星阵围棋棋谱下载")
    print(f"URL: {url}")
    print("-" * 50)
    
    downloader = GolaxyDownloader()
    result = downloader.download(url, output)
    
    if result['success']:
        print(f"\n✅ 下载成功!")
        print(f"文件: {result['file']}")
        print(f"\n📋 对局信息:")
        meta = result['metadata']
        print(f"  黑方: {meta['black']} {meta['black_rank']}")
        print(f"  白方: {meta['white']} {meta['white_rank']}")
        print(f"  结果: {meta['result']}")
        print(f"  赛事: {meta['event']}")
        print(f"  手数: {meta['move_count']}")
    else:
        print(f"\n❌ 下载失败")
        print(f"错误: {result['error']}")
        sys.exit(1)


if __name__ == '__main__':
    main()

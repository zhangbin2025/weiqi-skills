#!/usr/bin/env python3
"""
围棋棋谱统一分析模块
支持三种模式：
  1. 单局面评估 (eval) - 评估指定局面
  2. 整盘分析 (analyze) - 完整分析，生成胜率曲线和HTML报告
  3. 恶手检测 (mistakes) - 标记胜率骤降点
"""

import sys
import os
import argparse
import json
import re
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from katago import KataGoManager, SGFParser, MoveAnalysis
from setup import HardwareProfiler


# ==================== 工具函数 ====================

def format_time(seconds: float) -> str:
    """格式化时间"""
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        return f"{int(seconds/60)}分钟"
    else:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}小时{mins}分钟"


def format_coord(coord: str) -> str:
    """格式化坐标 (sgf格式 -> 棋盘坐标)"""
    if not coord or coord == "pass":
        return "停一手"
    letters = 'ABCDEFGHJKLMNOPQRST'
    try:
        x = ord(coord[0]) - ord('a')
        y = ord(coord[1]) - ord('a')
        if 0 <= x < 19 and 0 <= y < 19:
            return f"{letters[x]}{19-y}"
    except:
        pass
    return coord


def format_percent(value: float) -> str:
    """格式化百分比"""
    return f"{value:.1f}%"


def format_score(value: float) -> str:
    """格式化目差"""
    if value > 0:
        return f"B+{value:.1f}"
    elif value < 0:
        return f"W+{abs(value):.1f}"
    else:
        return "0"


def print_progress(current: int, total: int, start_time: float):
    """打印进度条"""
    elapsed = datetime.now().timestamp() - start_time
    percent = current / total * 100 if total > 0 else 0
    
    if current > 0:
        eta = elapsed / current * (total - current)
        eta_str = format_time(eta)
    else:
        eta_str = "计算中..."
    
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (bar_len - filled)
    
    print(f"\r[{bar}] {current}/{total} ({percent:.1f}%) ETA: {eta_str}", end='', flush=True)


# ==================== HTML报告生成 ====================

def generate_html_report(analyses: List[MoveAnalysis], sgf_content: str, output_path: str):
    """生成HTML分析报告"""
    
    winrate_data = []
    labels = []
    
    for a in analyses:
        labels.append(str(a.move_num))
        wr = a.winrate if a.player == "B" else 100 - a.winrate
        winrate_data.append(round(wr, 1))
    
    mistakes = [a for a in analyses if a.is_mistake]
    mistakes.sort(key=lambda x: abs(x.winrate_delta), reverse=True)
    
    # 构建恶手HTML
    mistakes_html = []
    if mistakes:
        for m in mistakes[:10]:
            player = "黑" if m.player == "B" else "白"
            coord = format_coord(m.coord)
            loss = abs(m.winrate_delta)
            severity_class = m.mistake_severity
            
            mistakes_html.append(f'''<div class="mistake {severity_class}">
            <div class="mistake-move">第{m.move_num}手<br><small>{player} {coord}</small></div>
            <div class="mistake-info">
                胜率下降 <span class="mistake-loss">{loss:.1f}%</span>，
                AI推荐 <strong>{format_coord(m.best_move)}</strong>
            </div>
        </div>''')
        mistakes_html_str = "\n".join(mistakes_html)
    else:
        mistakes_html_str = '<p style="color: #28a745;">✓ 未发现明显恶手，下得不错！</p>'
    
    # 构建恶手数据点
    mistake_points = json.dumps([{'x': i, 'y': winrate_data[i]} for i, a in enumerate(analyses) if a.is_mistake])
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>KataGo 棋谱分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header .meta {{ opacity: 0.9; margin-top: 10px; }}
        .card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .card h2 {{ margin-top: 0; color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .stat {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #667eea; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .mistake {{ display: flex; align-items: center; padding: 12px; margin: 8px 0; 
                   background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; }}
        .mistake.critical {{ background: #f8d7da; border-left-color: #dc3545; }}
        .mistake.significant {{ background: #fff3cd; border-left-color: #ffc107; }}
        .mistake.minor {{ background: #d1ecf1; border-left-color: #17a2b8; }}
        .mistake-move {{ font-weight: bold; margin-right: 15px; min-width: 60px; }}
        .mistake-info {{ flex: 1; }}
        .mistake-loss {{ color: #dc3545; font-weight: bold; }}
        #chart-container {{ height: 400px; margin: 20px 0; }}
        .legend {{ display: flex; gap: 20px; justify-content: center; margin-top: 15px; flex-wrap: wrap; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 KataGo 棋谱分析报告</h1>
        <div class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
    
    <div class="card">
        <h2>📈 胜率走势</h2>
        <div id="chart-container">
            <canvas id="winrateChart"></canvas>
        </div>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background: #667eea;"></div>
                <span>黑棋胜率</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #dc3545;"></div>
                <span>恶手标记</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #28a745;"></div>
                <span>50%基准线</span>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>📋 统计信息</h2>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(analyses)}</div>
                <div class="stat-label">分析手数</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(mistakes)}</div>
                <div class="stat-label">恶手数量</div>
            </div>
            <div class="stat">
                <div class="stat-value">{format_coord(mistakes[0].coord) if mistakes else '-'}</div>
                <div class="stat-label">最大失误</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>⚠️ 恶手详情</h2>
        {mistakes_html_str}
    </div>
    
    <script>
        const ctx = document.getElementById('winrateChart').getContext('2d');
        
        const mistakePoints = {mistake_points};
        
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [
                    {{
                        label: '黑棋胜率',
                        data: {json.dumps(winrate_data)},
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        pointHoverRadius: 5
                    }},
                    {{
                        label: '恶手',
                        data: mistakePoints,
                        backgroundColor: '#dc3545',
                        pointRadius: 6,
                        pointStyle: 'circle',
                        showLine: false
                    }},
                    {{
                        label: '50%线',
                        data: Array({len(labels)}).fill(50),
                        borderColor: '#28a745',
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    intersect: false,
                    mode: 'index'
                }},
                plugins: {{
                    tooltip: {{
                        callbacks: {{
                            title: function(context) {{
                                return '第 ' + context[0].label + ' 手';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        min: 0,
                        max: 100,
                        title: {{
                            display: true,
                            text: '胜率 (%)'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: '手数'
                        }},
                        ticks: {{
                            maxTicksLimit: 20
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path


# ==================== 核心分析功能 ====================

def analyze_game(sgf_file: str, 
                start: int = 0, 
                end: Optional[int] = None,
                interval: int = 1,
                output: str = "text",
                output_file: Optional[str] = None,
                verbose: bool = True) -> Optional[List[MoveAnalysis]]:
    """分析整盘棋"""
    manager = KataGoManager()
    
    if not manager.is_ready():
        if verbose:
            print("[✗] KataGo 环境未就绪")
            print("\n请运行: weiqi-katago setup")
        return None
    
    try:
        with open(sgf_file, 'r', encoding='utf-8') as f:
            sgf_content = f.read()
    except Exception as e:
        if verbose:
            print(f"[✗] 读取SGF失败: {e}")
        return None
    
    moves = SGFParser.parse(sgf_content)
    total_moves = len(moves)
    
    if total_moves == 0:
        if verbose:
            print("[✗] SGF文件中没有找到着法")
        return None
    
    if end is None or end > total_moves:
        end = total_moves
    
    moves_to_analyze = len(range(start, end, interval))
    
    # 检测变化图
    raw_moves_count = len(re.findall(r';[BW]\[[a-z]{0,2}\]', sgf_content))
    if raw_moves_count > total_moves * 2 and verbose:
        print(f"  (注: SGF包含变化图，已自动提取主分支 {total_moves} 手进行分析)")
    
    # 预估时间
    profiler = HardwareProfiler()
    model = "b18c384nbt"
    estimate = profiler.estimate_time(moves_to_analyze, model, profiler.detect())
    
    if verbose:
        print(f"\n📊 棋谱分析")
        print("=" * 50)
        print(f"总手数: {total_moves}")
        print(f"分析范围: 第{start+1}手 - 第{end}手")
        print(f"分析间隔: 每{interval}手")
        print(f"预计分析手数: {moves_to_analyze}")
        print(f"预计用时: {estimate['formatted']}")
        print()
    
    engine = manager.create_engine()
    if not engine:
        if verbose:
            print("[✗] 无法创建KataGo引擎")
        return None
    
    if verbose:
        print("开始分析...")
    start_time = datetime.now().timestamp()
    
    try:
        engine.start()
        
        analyses = []
        prev_winrate = 50.0
        
        for idx, move_num in enumerate(range(start, end, interval)):
            if verbose:
                print_progress(idx + 1, moves_to_analyze, start_time)
            
            if move_num >= len(moves):
                break
            
            current_moves = moves[:move_num + 1]
            result = engine.analyze_position(current_moves)
            
            if not result:
                continue
            
            player, coord = moves[move_num]
            
            current_winrate = result.winrate if player == "B" else 100 - result.winrate
            winrate_delta = current_winrate - prev_winrate
            
            is_mistake = False
            severity = ""
            if abs(winrate_delta) > 5:
                is_mistake = True
                if abs(winrate_delta) > 15:
                    severity = "critical"
                elif abs(winrate_delta) > 10:
                    severity = "significant"
                else:
                    severity = "minor"
            
            best_move = result.best_moves[0]["move"] if result.best_moves else ""
            best_winrate = result.best_moves[0]["winrate"] if result.best_moves else current_winrate
            
            analysis = MoveAnalysis(
                move_num=move_num + 1,
                player=player,
                coord=coord,
                winrate=current_winrate,
                score=result.score if player == "B" else -result.score,
                winrate_delta=winrate_delta,
                score_delta=0,
                best_move=best_move,
                best_winrate=best_winrate,
                is_mistake=is_mistake,
                mistake_severity=severity
            )
            
            analyses.append(analysis)
            prev_winrate = current_winrate
        
        engine.stop()
        
        elapsed = datetime.now().timestamp() - start_time
        if verbose:
            print(f"\n\n✓ 分析完成！用时: {format_time(elapsed)}")
        
    except Exception as e:
        if verbose:
            print(f"\n[✗] 分析失败: {e}")
        engine.stop()
        return None
    
    _output_results(analyses, output, output_file, sgf_file, verbose)
    return analyses


def _output_results(analyses: List[MoveAnalysis], output: str, output_file: Optional[str], 
                   sgf_file: str, verbose: bool):
    """输出分析结果"""
    if output == "json":
        output_path = output_file or sgf_file.replace(".sgf", "_analysis.json")
        result_data = [
            {
                "move_num": a.move_num,
                "player": a.player,
                "coord": a.coord,
                "winrate": round(a.winrate, 2),
                "score": round(a.score, 2),
                "winrate_delta": round(a.winrate_delta, 2),
                "is_mistake": a.is_mistake,
                "best_move": a.best_move
            }
            for a in analyses
        ]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        if verbose:
            print(f"JSON报告已保存: {output_path}")
            
    elif output == "html":
        output_path = output_file or sgf_file.replace(".sgf", "_analysis.html")
        try:
            with open(sgf_file, 'r', encoding='utf-8') as f:
                sgf_content = f.read()
        except:
            sgf_content = ""
        generate_html_report(analyses, sgf_content, output_path)
        if verbose:
            print(f"HTML报告已保存: {output_path}")
            
    elif output == "none":
        pass
        
    else:  # text
        if not verbose:
            return
            
        print(f"\n📋 分析摘要")
        print("-" * 50)
        
        mistakes = [a for a in analyses if a.is_mistake]
        print(f"分析手数: {len(analyses)}")
        print(f"发现恶手: {len(mistakes)} 处")
        
        if mistakes:
            print("\n主要失误:")
            for m in sorted(mistakes, key=lambda x: abs(x.winrate_delta), reverse=True)[:5]:
                player = "黑" if m.player == "B" else "白"
                print(f"  第{m.move_num}手 {player}[{format_coord(m.coord)}] 胜率下降 {abs(m.winrate_delta):.1f}%")


def eval_position(sgf_file: str, move_num: int = None, verbose: bool = True) -> Optional[Dict]:
    """单局面评估"""
    manager = KataGoManager()
    
    if not manager.is_ready():
        if verbose:
            print("[✗] KataGo 环境未就绪")
            print("\n请运行: weiqi-katago setup")
        return None
    
    try:
        with open(sgf_file, 'r', encoding='utf-8') as f:
            sgf_content = f.read()
    except Exception as e:
        if verbose:
            print(f"[✗] 读取SGF失败: {e}")
        return None
    
    moves = SGFParser.parse(sgf_content)
    total_moves = len(moves)
    
    if total_moves == 0:
        if verbose:
            print("[✗] SGF文件中没有找到着法")
        return None
    
    if move_num is None or move_num > total_moves:
        move_num = total_moves
    if move_num < 1:
        move_num = 1
    
    if move_num >= len(moves):
        last_player = moves[-1][0] if moves else "B"
        current_player = "W" if last_player == "B" else "B"
    else:
        current_player = moves[move_num - 1][0] if move_num > 0 else "B"
    
    position_moves = moves[:move_num]
    
    if verbose:
        player_name = "黑棋" if current_player == "B" else "白棋"
        print(f"\n第 {move_num} 手评估 ({player_name}落子)")
        print("=" * 50)
        print(f"棋谱总手数: {total_moves}")
        print("分析中...", end='', flush=True)
    
    result = None
    try:
        engine = manager.create_engine()
        if not engine:
            if verbose:
                print("\n[✗] 无法创建KataGo引擎")
            return None
        
        engine.start()
        result = engine.analyze_position(position_moves)
        engine.stop()
        
        if verbose:
            print(" 完成")
        
    except Exception as e:
        if verbose:
            print(f"\n[✗] 分析失败: {e}")
        return None
    
    if not result:
        if verbose:
            print("[✗] 未获得分析结果")
        return None
    
    if verbose:
        _print_eval_result(result, current_player)
    
    return {
        "winrate": result.winrate,
        "score": result.score,
        "visits": result.visits,
        "best_moves": result.best_moves,
        "pv": result.pv
    }


def _print_eval_result(result, current_player: str):
    """打印单局面评估结果"""
    print()
    
    if current_player == "B":
        winrate = result.winrate
    else:
        winrate = 100 - result.winrate
    
    if winrate > 55:
        advantage = "大幅领先"
    elif winrate > 52:
        advantage = "稍占优势"
    elif winrate > 48:
        advantage = "均势"
    elif winrate > 45:
        advantage = "稍处劣势"
    else:
        advantage = "明显落后"
    
    player_name = "黑棋" if current_player == "B" else "白棋"
    print(f"当前胜率: {format_percent(winrate)} ({advantage})")
    print(f"目差: {format_score(result.score)}")
    print(f"搜索次数: {result.visits}")
    
    if result.best_moves:
        print(f"\n{player_name}推荐点 Top 5:")
        print("-" * 50)
        
        for i, move in enumerate(result.best_moves[:5], 1):
            coord = format_coord(move["move"])
            winrate = move["winrate"]
            score = move["score"]
            
            marker = "✓" if i == 1 else " "
            
            pv = move.get("pv", [])
            pv_str = ""
            if pv:
                pv_display = [format_coord(m) for m in pv[:5]]
                pv_str = f" → {' → '.join(pv_display)}"
            
            print(f"{marker} {i}. {coord:6} ({format_percent(winrate)}, {format_score(score)}) {pv_str}")
    
    if result.pv:
        print(f"\n主变化图:")
        pv_display = [format_coord(m) for m in result.pv[:10]]
        print(f"  {' → '.join(pv_display)}")
    
    print()


def detect_mistakes(sgf_file: str, threshold: float = 5.0, top: int = 20, 
                   output: str = "text", verbose: bool = True) -> List[MoveAnalysis]:
    """恶手检测"""
    analyses = analyze_game(sgf_file, interval=1, output="none", verbose=verbose)
    
    if not analyses:
        return []
    
    mistakes = [a for a in analyses if abs(a.winrate_delta) > threshold]
    mistakes.sort(key=lambda x: abs(x.winrate_delta), reverse=True)
    
    if output == "json":
        output_path = sgf_file.replace(".sgf", "_mistakes.json")
        result_data = [
            {
                "move_num": a.move_num,
                "player": a.player,
                "coord": a.coord,
                "winrate": round(a.winrate, 2),
                "winrate_delta": round(a.winrate_delta, 2),
                "best_move": a.best_move,
                "severity": a.mistake_severity
            }
            for a in mistakes[:top]
        ]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        if verbose:
            print(f"恶手报告已保存: {output_path}")
    elif verbose:
        _print_mistakes(mistakes[:top], threshold)
    
    return mistakes[:top]


def _print_mistakes(mistakes: List[MoveAnalysis], threshold: float):
    """打印恶手列表"""
    print(f"\n发现 {len(mistakes)} 处恶手 (胜率下降 >{threshold}%)")
    print("=" * 50)
    
    severity_icons = {
        "critical": "🔴 严重",
        "significant": "🟠 重大", 
        "minor": "🟡 轻微"
    }
    
    for i, m in enumerate(mistakes, 1):
        player = "黑棋" if m.player == "B" else "白棋"
        coord = format_coord(m.coord)
        icon = severity_icons.get(m.mistake_severity, "⚪")
        prev_winrate = m.winrate - m.winrate_delta
        
        print(f"\n{i}. {icon} 第{m.move_num}手 {player}[{coord}]")
        print(f"   胜率变化: {prev_winrate:.0f}% → {m.winrate:.0f}% ({m.winrate_delta:+.1f}%)")
        print(f"   AI推荐: {format_coord(m.best_move)}")


# ==================== 命令行入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description='KataGo 围棋分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单局面评估
  %(prog)s eval game.sgf
  %(prog)s eval game.sgf --move 50

  # 完整分析
  %(prog)s analyze game.sgf
  %(prog)s analyze game.sgf --interval 5 --output html

  # 恶手检测
  %(prog)s mistakes game.sgf
  %(prog)s mistakes game.sgf --threshold 10
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # eval 子命令
    eval_parser = subparsers.add_parser('eval', help='单局面评估')
    eval_parser.add_argument('sgf_file', help='SGF文件路径')
    eval_parser.add_argument('--move', '-m', type=int, default=None, 
                           help='评估到第几手后的局面（默认最后一手）')
    eval_parser.add_argument('--quiet', '-q', action='store_true',
                           help='静默模式，只输出JSON')
    
    # analyze 子命令
    analyze_parser = subparsers.add_parser('analyze', help='完整棋谱分析')
    analyze_parser.add_argument('sgf_file', help='SGF文件路径')
    analyze_parser.add_argument('--start', '-s', type=int, default=0, help='开始手数')
    analyze_parser.add_argument('--end', '-e', type=int, default=None, help='结束手数')
    analyze_parser.add_argument('--interval', '-i', type=int, default=1, 
                              help='分析间隔（每N手分析一次）')
    analyze_parser.add_argument('--output', '-o', choices=['text', 'json', 'html'], 
                              default='text', help='输出格式')
    analyze_parser.add_argument('--output-file', '-f', type=str, default=None, help='输出文件路径')
    
    # mistakes 子命令
    mistakes_parser = subparsers.add_parser('mistakes', help='恶手检测')
    mistakes_parser.add_argument('sgf_file', help='SGF文件路径')
    mistakes_parser.add_argument('--threshold', '-t', type=float, default=5.0,
                               help='胜率下降阈值 (%%)，默认 5%%')
    mistakes_parser.add_argument('--top', '-n', type=int, default=20,
                               help='显示前N个恶手，默认 20')
    mistakes_parser.add_argument('--output', '-o', choices=['text', 'json'],
                               default='text', help='输出格式')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if not os.path.exists(args.sgf_file):
        print(f"[✗] 文件不存在: {args.sgf_file}")
        sys.exit(1)
    
    if args.command == 'eval':
        result = eval_position(args.sgf_file, args.move, verbose=not args.quiet)
        if args.quiet and result:
            print(json.dumps(result, ensure_ascii=False))
        if not result:
            sys.exit(1)
            
    elif args.command == 'analyze':
        result = analyze_game(
            args.sgf_file,
            start=args.start,
            end=args.end,
            interval=args.interval,
            output=args.output,
            output_file=args.output_file
        )
        if not result:
            sys.exit(1)
            
    elif args.command == 'mistakes':
        result = detect_mistakes(
            args.sgf_file,
            threshold=args.threshold,
            top=args.top,
            output=args.output
        )
        if not result:
            sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGF围棋打谱网页生成器 - 纯本地离线工具
将野狐围棋SGF文件转换为交互式HTML打谱网页

使用方法:
    python3 replay.py input.sgf [output.html]
    python3 replay.py input.sgf --output-dir /path/to/dir

示例:
    python3 replay.py game.sgf                    # 输出到 /tmp/sgf-viewer/
    python3 replay.py game.sgf mygame.html        # 输出到 /tmp/sgf-viewer/mygame.html
"""

import sys
import os
import html
import json

# 导入 SGF 解析模块
from sgf_parser import parse_sgf


def load_template():
    """加载 HTML 模板文件"""
    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'templates', 'replay.html'
    )
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def generate_html(tree, game_info, output_path, input_base_name='棋谱', start_move=0, max_moves=0):
    """生成HTML打谱网页"""
    
    # 加载模板
    template = load_template()
    
    # 准备替换数据
    board_size = int(game_info.get('board_size', '19'))
    handicap = game_info.get('handicap', '0')
    handicap_stones = game_info.get('handicap_stones', [])
    
    # 各种转义处理
    black_name = html.escape(game_info.get('black', '黑棋'))
    white_name = html.escape(game_info.get('white', '白棋'))
    black_rank = html.escape(game_info.get('black_rank', ''))
    white_rank = html.escape(game_info.get('white_rank', ''))
    game_name = html.escape(game_info.get('game_name', '围棋棋谱'))
    result = html.escape(game_info.get('result', ''))
    
    # 构建游戏标题和信息
    game_title = game_name
    game_info_text = f"{black_name} vs {white_name}"
    if int(handicap) > 0:
        game_info_text += f" · 让{handicap}子"
    if result:
        game_info_text += f" · {result}"
    
    # 树形数据 JSON（用于前端分支导航）
    tree_json = html.escape(json.dumps(tree, ensure_ascii=False)).replace('\\', '&#92;')
    
    # 让子石 JSON
    handicap_stones_json = json.dumps(handicap_stones)
    
    # 执行模板替换
    html_content = template
    html_content = html_content.replace('{{GAME_NAME}}', game_name)
    html_content = html_content.replace('{{GAME_TITLE}}', game_title)
    html_content = html_content.replace('{{GAME_INFO}}', game_info_text)
    html_content = html_content.replace('{{BOARD_SIZE}}', str(board_size))
    html_content = html_content.replace('{{HANDICAP_STONES}}', handicap_stones_json)
    html_content = html_content.replace('{{HANDICAP_COUNT}}', str(handicap))
    html_content = html_content.replace('{{TREE_JSON}}', tree_json)
    html_content = html_content.replace('{{BLACK_NAME}}', black_name + (' ' + black_rank if black_rank else ''))
    html_content = html_content.replace('{{WHITE_NAME}}', white_name + (' ' + white_rank if white_rank else ''))
    html_content = html_content.replace('{{DOWNLOAD_FILENAME}}', html.escape(input_base_name) + '.sgf')
    html_content = html_content.replace('{{DEFAULT_MOVE}}', str(start_move))
    html_content = html_content.replace('{{MAX_MOVES}}', str(max_moves))
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 已生成打谱网页: {output_path}")
    print(f"   黑棋: {black_name}")
    print(f"   白棋: {white_name}")


def generate_json(tree, game_info, output_path, input_base_name='棋谱', start_move=0, max_moves=0):
    """生成 JSON 数据文件（供 replay.html 异步加载）"""
    
    board_size = int(game_info.get('board_size', '19'))
    handicap = game_info.get('handicap', '0')
    handicap_stones = game_info.get('handicap_stones', [])
    
    # 精简棋谱树：保留变化分支和 AI 分析关键属性
    def simplify_tree(node):
        """保留所有变化分支，保留 C（注释/胜率）和 N（标签）属性"""
        if not node:
            return None
        
        simplified = {
            'color': node.get('color'),
            'coord': node.get('coord'),
        }
        
        # 保留 C（注释，包含胜率信息）和 N（标签）属性
        if node.get('properties'):
            props = node['properties']
            keep_props = {}
            if props.get('C'):
                keep_props['C'] = props['C']
            if props.get('N'):
                keep_props['N'] = props['N']
            if keep_props:
                simplified['properties'] = keep_props
        
        # 保留所有子节点（包括变化分支）
        if node.get('children'):
            simplified['children'] = [simplify_tree(child) for child in node['children'] if child]
        
        return simplified
    
    clean_tree = simplify_tree(tree)
    
    # 处理 start_move：-1 表示最后一手
    default_move = start_move if start_move >= 0 else max_moves
    
    data = {
        'game_name': game_info.get('game_name', '围棋棋谱'),
        'black': game_info.get('black', '黑棋'),
        'white': game_info.get('white', '白棋'),
        'black_rank': game_info.get('black_rank', ''),
        'white_rank': game_info.get('white_rank', ''),
        'board_size': board_size,
        'handicap': int(handicap),
        'handicap_stones': handicap_stones,
        'result': game_info.get('result', ''),
        'tree': clean_tree,
        'download_filename': input_base_name + '.sgf',
        'default_move': default_move,
        'max_moves': max_moves
    }
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    
    print(f"✅ 已生成 JSON 数据: {output_path}")
    print(f"   黑棋: {data['black']}")
    print(f"   白棋: {data['white']}")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 replay.py input.sgf [output.html]")
        print("       python3 replay.py input.sgf --output-dir /path/to/dir")
        print("       python3 replay.py input.sgf --start-move 50")
        print("       python3 replay.py input.sgf --start-move last")
        print("       python3 replay.py input.sgf --data-only  # 仅输出JSON")
        print("示例: python3 replay.py game.sgf")
        print("       python3 replay.py game.sgf -o /tmp/myviewer")
        print("       python3 replay.py game.sgf --data-only -o /path/to/data.json")
        print("       python3 replay.py game.sgf --start-move 100  # 默认跳转到第100手")
        print("       python3 replay.py game.sgf --start-move last # 跳转到最后一手")
        sys.exit(1)

    input_file = sys.argv[1]

    # 解析参数
    output_file = None
    output_dir = None
    start_move = 0
    data_only = False  # 新增: 仅输出JSON

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] in ('--output-dir', '-o'):
            if i + 1 < len(sys.argv):
                path_arg = sys.argv[i + 1]
                # 根据是否有扩展名判断是文件还是目录
                _, ext = os.path.splitext(path_arg)
                if ext and ext in ('.html', '.htm', '.json'):
                    output_file = path_arg  # 是文件路径
                else:
                    output_dir = path_arg   # 是目录路径
                i += 2
            else:
                print("❌ 错误: --output-dir 需要指定路径")
                sys.exit(1)
        elif sys.argv[i] == '--start-move':
            if i + 1 < len(sys.argv):
                move_arg = sys.argv[i + 1]
                if move_arg.lower() == 'last':
                    start_move = -1  # 特殊标记，表示最后一手
                else:
                    try:
                        start_move = int(move_arg)
                        if start_move < 0:
                            print("❌ 错误: --start-move 必须是非负整数")
                            sys.exit(1)
                    except ValueError:
                        print("❌ 错误: --start-move 必须是整数或 'last'")
                        sys.exit(1)
                i += 2
            else:
                print("❌ 错误: --start-move 需要指定手数")
                sys.exit(1)
        elif sys.argv[i] == '--data-only':
            data_only = True
            i += 1
        elif not output_file:
            output_file = sys.argv[i]
            i += 1
        else:
            i += 1

    # 默认输出目录为 /tmp/sgf-viewer
    if output_dir is None and not output_file:
        output_dir = '/tmp/sgf-viewer'

    # 确定输出文件名
    if output_file:
        if os.path.isabs(output_file):
            output_path = output_file
        else:
            output_path = output_file  # 相对路径直接使用
        # 确保目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
    elif output_dir:
        # 根据模式确定扩展名
        ext = '.json' if data_only else '.html'
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, base_name + ext)
    else:
        # 相对路径默认
        ext = '.json' if data_only else '.html'
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_path = base_name + ext

    # 读取SGF文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            sgf_content = f.read()
    except FileNotFoundError:
        print(f"❌ 错误: 找不到文件 {input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: 读取文件失败 - {e}")
        sys.exit(1)

    # 解析 SGF
    print(f"📖 正在解析: {input_file}")
    result = parse_sgf(sgf_content)
    
    tree = result['tree']
    game_info = result['game_info']
    stats = result['stats']
    errors = result['errors']

    if stats['move_nodes'] == 0:
        print("❌ 错误: 无法从SGF中提取着法")
        if errors:
            print("   解析错误:")
            for err in errors:
                print(f"     - {err}")
        sys.exit(1)

    print(f"   总节点数: {stats['total_nodes']}")
    print(f"   着法节点: {stats['move_nodes']}")
    print(f"   最大深度: {stats['max_depth']}")
    print(f"   分支数: {stats['branch_count']}")

    if errors:
        print(f"   ⚠️  解析过程中遇到 {len(errors)} 个错误/警告")
        for err in errors[:5]:  # 最多显示5个
            print(f"     - {err}")

    # 获取输入文件名（不含扩展名）
    input_base_name = os.path.splitext(os.path.basename(input_file))[0]

    # 根据模式生成输出
    if data_only:
        # JSON 模式
        generate_json(tree, game_info, output_path, input_base_name, start_move, stats['max_depth'])
        if start_move > 0:
            print(f"   默认跳转: 第 {start_move} 手")
        elif start_move == -1:
            print(f"   默认跳转: 最后一手")
        print(f"✅ JSON 生成完成: {output_path}")
    else:
        # HTML 模式
        generate_html(tree, game_info, output_path, input_base_name, start_move, stats['max_depth'])
        if start_move > 0:
            print(f"   默认跳转: 第 {start_move} 手")
        elif start_move == -1:
            print(f"   默认跳转: 最后一手")

    print(f"\n✅ 生成完成: {output_path}")


if __name__ == '__main__':
    main()

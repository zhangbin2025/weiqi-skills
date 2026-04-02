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


def generate_html(main_moves, game_info, variations, output_path, input_base_name='棋谱'):
    """生成HTML打谱网页"""
    
    # 加载模板
    template = load_template()
    
    # 准备替换数据
    board_size = int(game_info.get('board_size', '19'))
    handicap = game_info.get('handicap', '0')
    handicap_stones = game_info.get('handicap_stones', [])
    komi = game_info.get('komi', '375')
    
    # 构建SGF字符串
    sgf_moves = ''.join([f";{m['color']}[{m['coord']}]" for m in main_moves])
    handicap_sgf = f"HA[{handicap}]" if int(handicap) > 0 else ""
    for stone in handicap_stones:
        coord = chr(97 + stone['x']) + chr(97 + stone['y'])
        handicap_sgf += f"AB[{coord}]"
    
    sgf_raw = f"""(;GM[1]FF[4]
SZ[{board_size}]
GN[{game_info.get('game_name', '围棋棋谱')}]
DT[{game_info.get('date', '')}]
PB[{game_info.get('black', '黑棋')}]
PW[{game_info.get('white', '白棋')}]
BR[{game_info.get('black_rank', '')}]
WR[{game_info.get('white_rank', '')}]
KM[{komi}]{handicap_sgf}RU[Chinese]RE[{game_info.get('result', '')}]{sgf_moves})"""
    
    # 各种转义处理
    black_name = html.escape(game_info.get('black', '黑棋'))
    white_name = html.escape(game_info.get('white', '白棋'))
    black_rank = html.escape(game_info.get('black_rank', ''))
    white_rank = html.escape(game_info.get('white_rank', ''))
    game_name = html.escape(game_info.get('game_name', '围棋棋谱'))
    result = html.escape(game_info.get('result', ''))
    
    # 构建游戏标题和信息
    game_title = game_name.replace('<绝艺讲解>', '').replace('绝艺讲解', '')
    game_info_text = f"{black_name} vs {white_name}"
    if int(handicap) > 0:
        game_info_text += f" · 让{handicap}子"
    if result:
        game_info_text += f" · {result}"
    
    # 变化图数据 JSON
    variations_json = html.escape(json.dumps(variations, ensure_ascii=False)).replace('\\', '&#92;')
    
    # 让子石 JSON
    handicap_stones_json = json.dumps(handicap_stones)
    
    # 执行模板替换
    html_content = template
    html_content = html_content.replace('{{GAME_NAME}}', game_name)
    html_content = html_content.replace('{{GAME_TITLE}}', game_title)
    html_content = html_content.replace('{{GAME_INFO}}', game_info_text)
    html_content = html_content.replace('{{MOVE_COUNT}}', str(len(main_moves)))
    html_content = html_content.replace('{{SGF_DATA}}', html.escape(sgf_raw))
    html_content = html_content.replace('{{BOARD_SIZE}}', str(board_size))
    html_content = html_content.replace('{{HANDICAP_STONES}}', handicap_stones_json)
    html_content = html_content.replace('{{HANDICAP_COUNT}}', handicap)
    html_content = html_content.replace('{{VARIATIONS_JSON}}', variations_json)
    html_content = html_content.replace('{{BLACK_NAME}}', black_name + (' ' + black_rank if black_rank else ''))
    html_content = html_content.replace('{{WHITE_NAME}}', white_name + (' ' + white_rank if white_rank else ''))
    html_content = html_content.replace('{{DOWNLOAD_FILENAME}}', html.escape(input_base_name) + '.sgf')
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 已生成打谱网页: {output_path}")
    print(f"   总手数: {len(main_moves)}")
    print(f"   黑棋: {black_name}")
    print(f"   白棋: {white_name}")


def main():
    if len(sys.argv) < 2:
        print("用法: python3 replay.py input.sgf [output.html]")
        print("       python3 replay.py input.sgf --output-dir /path/to/dir")
        print("示例: python3 replay.py game.sgf")
        print("       python3 replay.py game.sgf -o /tmp/myviewer")
        sys.exit(1)

    input_file = sys.argv[1]

    # 解析参数
    output_file = None
    output_dir = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] in ('--output-dir', '-o'):
            if i + 1 < len(sys.argv):
                output_dir = sys.argv[i + 1]
                i += 2
            else:
                print("❌ 错误: --output-dir 需要指定目录路径")
                sys.exit(1)
        elif not output_file:
            output_file = sys.argv[i]
            i += 1
        else:
            i += 1

    # 默认输出目录为 /tmp/sgf-viewer
    if output_dir is None:
        output_dir = '/tmp/sgf-viewer'

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 确定输出文件名
    if output_file:
        if os.path.isabs(output_file):
            output_path = output_file
        else:
            output_path = os.path.join(output_dir, output_file)
    else:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_path = os.path.join(output_dir, base_name + '.html')

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
    main_moves, variations, game_info, parse_info = parse_sgf(sgf_content)

    if not main_moves:
        print("❌ 错误: 无法从SGF中提取着法")
        if parse_info['errors']:
            print("   解析错误:")
            for err in parse_info['errors']:
                print(f"     - {err}")
        sys.exit(1)

    print(f"   解析器: {parse_info['parser_used']}")
    print(f"   提取到 {len(main_moves)} 手主分支着法")

    if parse_info['warnings']:
        for warn in parse_info['warnings']:
            print(f"   ⚠️  {warn}")

    if parse_info['errors'] and parse_info['parser_used'] == 'tree_parser':
        print(f"   ⚠️  解析过程中遇到 {len(parse_info['errors'])} 个错误，已尽可能恢复")

    if variations:
        total = sum(len(v) for v in variations.values())
        print(f"   提取到 {total} 个变化图")

    # 获取输入文件名（不含扩展名）
    input_base_name = os.path.splitext(os.path.basename(input_file))[0]

    # 生成HTML
    generate_html(main_moves, game_info, variations, output_path, input_base_name)

    print(f"\n✅ 生成完成: {output_path}")


if __name__ == '__main__':
    main()

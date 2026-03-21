#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGF围棋打谱网页生成器
将野狐围棋SGF文件转换为交互式HTML打谱网页

使用方法:
    python3 replay.py input.sgf [output.html]
    python3 replay.py input.sgf --output-dir /path/to/dir

示例:
    python3 replay.py game.sgf                    # 输出到 /tmp/sgf-viewer/
    python3 replay.py game.sgf mygame.html        # 输出到 /tmp/sgf-viewer/mygame.html
    python3 replay.py game.sgf -o /home/user/web  # 输出到指定目录
"""

import sys
import re
import os


def extract_main_branch(sgf_content):
    """
    从野狐围棋SGF中提取主分支着法

    野狐SGF格式特点:
    - 多行格式，前9行是文件头
    - 从第10行开始，每行是一个分支（主分支或变例）
    - 主分支：每行只有1个着法（简单的嵌套格式）
    - 变化图：每行有多个着法（带AI评论的完整变化）

    提取策略:
    1. 跳过前9行（文件头）
    2. 从第10行开始，只提取只有1个着法的行
    3. 当遇到有多个着法的行时，说明是变化图，停止提取
    """
    lines = sgf_content.replace('\r\n', '\n').split('\n')

    main_moves = []
    found_first_move = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 查找所有着法
        moves_in_line = re.findall(r';([BW])\[([a-z]{2})\]', line)

        if not moves_in_line:
            continue

        # 检查是否是第一手（文件头行）
        if not found_first_move:
            # 第一手可能在文件头行（不以 (; 开头）
            color, coord = moves_in_line[0]
            main_moves.append({
                'color': color,
                'coord': coord
            })
            found_first_move = True
            continue

        # 对于后续行，只取只有1个着法的行（主分支）
        if len(moves_in_line) == 1:
            color, coord = moves_in_line[0]
            main_moves.append({
                'color': color,
                'coord': coord
            })
        else:
            # 遇到有多个着法的行，说明是变化图，停止
            # 但为了处理可能的意外情况，继续检查后面是否还有单着法行
            # 实际上应该停止，因为后面的都是变化图
            pass

    return main_moves


def extract_variations(sgf_content, main_moves):
    """
    提取变化图（变例）
    返回: {手数: [{name, moves, comment}, ...]}
    """
    lines = sgf_content.replace('\r\n', '\n').split('\n')
    variations = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        moves_in_line = re.findall(r';([BW])\[([a-z]{2})\]', line)

        # 只处理有多个着法的行（变化图）
        if len(moves_in_line) <= 1:
            continue

        comment_match = re.search(r'C\[([^\]]+)\]', line)
        comment = comment_match.group(1) if comment_match else ""

        # 找到分叉点
        first_color, first_coord = moves_in_line[0]

        for start_idx, main_move in enumerate(main_moves):
            if main_move['color'] == first_color and main_move['coord'] == first_coord:
                # 检查后续是否分歧
                has_diff = False
                for i in range(1, len(moves_in_line)):
                    if start_idx + i >= len(main_moves):
                        has_diff = True
                        break
                    var_color, var_coord = moves_in_line[i]
                    main = main_moves[start_idx + i]
                    if main['color'] != var_color or main['coord'] != var_coord:
                        has_diff = True
                        break

                if has_diff or len(moves_in_line) > len(main_moves) - start_idx:
                    move_num = start_idx + 1
                    var_moves = [{'color': c, 'coord': coord} for c, coord in moves_in_line]

                    if move_num not in variations:
                        variations[move_num] = []

                    # 提取胜率作为名称
                    name = f"变化{len(variations[move_num])+1}"
                    winRate = name
                    win_match = re.search(r'([黑白]).*?(\d+\.?\d*)%', comment)
                    if win_match:
                        winRate = f"{win_match.group(1)}{win_match.group(2)}%"
                        name += f" {winRate}"

                    variations[move_num].append({
                        'name': name,
                        'winRate': winRate,
                        'moves': var_moves,
                        'comment': comment
                    })
                break

    return variations


def extract_game_info(sgf_content):
    """提取棋局信息"""
    info = {}

    # 提取基本信息
    patterns = {
        'PB': ('black', r'PB\[([^\]]+)\]'),
        'PW': ('white', r'PW\[([^\]]+)\]'),
        'BR': ('black_rank', r'BR\[([^\]]+)\]'),
        'WR': ('white_rank', r'WR\[([^\]]+)\]'),
        'GN': ('game_name', r'GN\[([^\]]+)\]'),
        'DT': ('date', r'DT\[([^\]]+)\]'),
        'RE': ('result', r'RE\[([^\]]+)\]'),
        'KM': ('komi', r'KM\[([^\]]+)\]'),
        'SZ': ('board_size', r'SZ\[([^\]]+)\]'),
    }

    for key, (name, pattern) in patterns.items():
        match = re.search(pattern, sgf_content)
        if match:
            info[name] = match.group(1)

    return info


def generate_html(main_moves, game_info, variations, output_path, input_base_name='棋谱'):
    """生成HTML打谱网页"""

    import json

    # 构建SGF字符串（平面格式）
    sgf_moves = ''.join([f";{m['color']}[{m['coord']}]" for m in main_moves])

    # 棋局信息
    black_name = game_info.get('black', '黑棋')
    white_name = game_info.get('white', '白棋')
    black_rank = game_info.get('black_rank', '')
    white_rank = game_info.get('white_rank', '')
    game_name = game_info.get('game_name', '围棋棋谱')
    game_date = game_info.get('date', '')
    result = game_info.get('result', '')

    # 构建完整的SGF
    board_size = game_info.get('board_size', '19')
    komi = game_info.get('komi', '375')

    sgf_data = f"""(;GM[1]FF[4]
SZ[{board_size}]
GN[{game_name}]
DT[{game_date}]
PB[{black_name}]
PW[{white_name}]
BR[{black_rank}]
WR[{white_rank}]
KM[{komi}]HA[0]RU[Chinese]RE[{result}]{sgf_moves})"""

    # 变化图数据
    variations_json = json.dumps(variations, ensure_ascii=False)

    # HTML模板
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{game_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            padding: 6px;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            padding: 8px;
            max-width: 100%;
            width: 100%;
        }}
        .header {{
            text-align: center;
            margin-bottom: 8px;
        }}
        .header h1 {{
            font-size: 15px;
            color: #333;
            margin-bottom: 2px;
            line-height: 1.2;
        }}
        .header .info {{
            color: #666;
            font-size: 11px;
            line-height: 1.3;
        }}
        .board-container {{
            display: flex;
            justify-content: center;
            margin: 10px 0;
            position: relative;
            width: 100%;
        }}
        #board {{
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            max-width: 100%;
            width: 100%;
            height: auto;
            aspect-ratio: 1 / 1;
            display: block;
        }}
        .controls {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            margin: 12px 0;
            flex-wrap: wrap;
        }}
        .btn {{
            width: 44px;
            height: 44px;
            border: none;
            border-radius: 50%;
            cursor: pointer;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            background: #f0f0f0;
            color: #333;
        }}
        .btn:active {{
            transform: scale(0.95);
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            width: 56px;
            height: 56px;
            font-size: 24px;
        }}
        .btn-success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
        }}
        .settings {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin: 10px 0;
            flex-wrap: wrap;
        }}
        .setting-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 14px;
            color: #555;
        }}
        .speed-control {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: #555;
        }}
        .speed-control input {{
            width: 100px;
        }}
        .status {{
            text-align: center;
            margin: 10px 0;
        }}
        .move-info {{
            font-size: 16px;
            font-weight: bold;
            color: #333;
            margin-bottom: 4px;
        }}
        .move-detail {{
            font-size: 14px;
            color: #666;
            margin-bottom: 4px;
        }}
        .captured-info {{
            font-size: 14px;
            color: #888;
        }}
        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: #555;
        }}
        .stone-black, .stone-white {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
        }}
        .stone-black {{
            background: radial-gradient(circle at 30% 30%, #666, #000);
        }}
        .stone-white {{
            background: radial-gradient(circle at 30% 30%, #fff, #ccc);
            border: 1px solid #ddd;
        }}
        @media (min-width: 600px) {{
            .container {{
                max-width: 500px;
                padding: 20px;
            }}
            .header h1 {{
                font-size: 20px;
            }}
        }}
        @media (min-width: 900px) {{
            .container {{
                max-width: 700px;
                padding: 30px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 id="gameTitle">{game_name.replace('<绝艺讲解>', '').replace('绝艺讲解', '')}</h1>
            <div class="info" id="gameInfo">{black_name} vs {white_name} · {result}</div>
        </div>

        <div class="board-container">
            <canvas id="board"></canvas>
        </div>

        <!-- 主控制面板 - 手机端确保一行显示 -->
        <div id="mainControls" style="display: flex; align-items: center; justify-content: space-between; gap: 4px; margin: 6px 0; flex-wrap: nowrap; padding: 0 2px;">
            <div style="display: flex; align-items: center; gap: 3px; flex: 1;">
                <button class="btn" onclick="prevMove()" title="上一手" style="width: 32px; height: 32px; font-size: 14px; padding: 0; flex-shrink: 0;">◀</button>
                <input type="range" id="moveSlider" min="0" max="{len(main_moves)}" value="0" style="width: 100%; min-width: 80px; height: 18px; flex: 1;" oninput="goToMove(this.value)">
                <button class="btn" onclick="nextMove()" title="下一手" style="width: 32px; height: 32px; font-size: 14px; padding: 0; flex-shrink: 0;">▶</button>
            </div>
            <div style="width: 1px; height: 20px; background: #ddd; margin: 0 3px; flex-shrink: 0;"></div>
            <div style="display: flex; align-items: center; gap: 3px; flex-shrink: 0;">
                <button class="btn" id="numToggleBtn" onclick="toggleNumbers()" title="显示/隐藏手数" style="width: 32px; height: 32px; font-size: 11px; padding: 0; background: #f0f0f0;">1️⃣</button>
                <button class="btn" onclick="downloadSGF()" title="下载SGF" style="width: 32px; height: 32px; font-size: 14px; padding: 0; background: #f0f0f0;">💾</button>
                <button class="btn" id="playBtn" onclick="togglePlay()" title="播放/暂停" style="width: 32px; height: 32px; font-size: 13px; padding: 0; font-weight: bold;">播</button>
            </div>
        </div>
        
        <!-- 隐藏的手数显示控制 -->
        <input type="checkbox" id="showNumbers" style="display: none;">

        <!-- 变化图列表面板 -->
        <div id="varPanel" style="margin: 8px 0; padding: 8px 10px; background: #f8f9fa; border-radius: 8px; display: none;">
            <div id="varList" style="display: flex; flex-wrap: wrap; gap: 6px;"></div>
        </div>

        <!-- 变化图查看控制面板 -->
        <div id="varControlPanel" style="display: none; margin: 8px 0; padding: 10px; background: #f0f0f0; border-radius: 8px;">
            <div style="display: flex; justify-content: center; gap: 16px;">
                <button class="btn" id="varPrevBtn" onclick="varPrev()" style="width: 32px; height: 32px; font-size: 14px; background: #667eea; color: white;">◀</button>
                <button class="btn" onclick="exitVariation()" style="width: 32px; height: 32px; font-size: 14px; background: #ff6b6b; color: white;">✕</button>
                <button class="btn" id="varNextBtn" onclick="varNext()" style="width: 32px; height: 32px; font-size: 14px; background: #667eea; color: white;">▶</button>
            </div>
        </div>

        <div class="status">
            <div class="move-info" id="moveInfo">第 0 手</div>
            <div class="captured-info" id="capturedInfo"></div>
        </div>

        <div class="legend">
            <div class="legend-item">
                <div class="stone-black"></div>
                <span id="blackName">{black_name}{' ' + black_rank if black_rank else ''}</span>
            </div>
            <div class="legend-item">
                <div class="stone-white"></div>
                <span id="whiteName">{white_name}{' ' + white_rank if white_rank else ''}</span>
            </div>
        </div>
    </div>

    <script>
        // SGF 数据
        const sgfData = `{sgf_data}`;

        const BOARD_SIZE = {board_size};

        // 解析 SGF - 支持平面格式（已清理的野狐SGF）
        function parseSGF(sgf) {{
            const moves = [];
            const info = {{}};

            // 提取基本信息
            const pbMatch = sgf.match(/PB\\[([^\\]]+)\\]/);
            const pwMatch = sgf.match(/PW\\[([^\\]]+)\\]/);
            const brMatch = sgf.match(/BR\\[([^\\]]+)\\]/);
            const wrMatch = sgf.match(/WR\\[([^\\]]+)\\]/);
            const gnMatch = sgf.match(/GN\\[([^\\]]+)\\]/);
            const dtMatch = sgf.match(/DT\\[([^\\]]+)\\]/);
            const reMatch = sgf.match(/RE\\[([^\\]]+)\\]/);

            if (pbMatch) info.black = pbMatch[1];
            if (pwMatch) info.white = pwMatch[1];
            if (brMatch) info.blackRank = brMatch[1];
            if (wrMatch) info.whiteRank = wrMatch[1];
            if (gnMatch) info.gameName = gnMatch[1];
            if (dtMatch) info.date = dtMatch[1];
            if (reMatch) info.result = reMatch[1];

            // 提取着法 - 平面格式直接按顺序提取
            const regex = /;([BW])\\[([a-z]{{2}})\\]/g;
            let match;
            while ((match = regex.exec(sgf)) !== null) {{
                const color = match[1] === 'B' ? 'black' : 'white';
                const x = match[2].charCodeAt(0) - 97;
                const y = match[2].charCodeAt(1) - 97;
                moves.push({{ color, x, y }});
            }}

            return {{ moves, info }};
        }}

        const {{ moves, info }} = parseSGF(sgfData);
        let currentMove = 0;
        let isPlaying = false;
        let playInterval = null;

        // 变化图相关变量
        const variations = {variations_json};
        let inVariation = false;
        let varMoves = [];
        let varIndex = 0;

        // Canvas 设置
        const canvas = document.getElementById('board');
        const ctx = canvas.getContext('2d');

        function resizeCanvas() {{
            const container = document.querySelector('.board-container');
            // 手机端最大化棋盘，确保正方形
            const isMobile = window.innerWidth < 768;
            const margin = isMobile ? 4 : 20;
            const availableWidth = Math.min(container.clientWidth, window.innerWidth) - margin;
            const availableHeight = window.innerHeight - 250; // 预留空间给其他UI元素
            const maxSize = Math.min(availableWidth, availableHeight, isMobile ? 760 : 720);
            const size = Math.max(isMobile ? 320 : 400, maxSize);

            canvas.width = size;
            canvas.height = size;
            canvas.style.width = size + 'px';
            canvas.style.height = size + 'px';

            updateDisplay();
        }}

        function getGridParams() {{
            const baseMargin = canvas.width * 0.02; // 减小基础边距
            const coordMargin = canvas.width * 0.018; // 减小坐标标签区域
            const margin = baseMargin + coordMargin; // 实际棋盘边距（包含坐标）
            const gridSize = (canvas.width - 2 * margin) / (BOARD_SIZE - 1);
            return {{ margin, gridSize, baseMargin, coordMargin }};
        }}

        // 创建棋盘状态数组
        function createBoard() {{
            return Array(BOARD_SIZE).fill(null).map(() => Array(BOARD_SIZE).fill(null));
        }}

        // 气数计算和提子
        function getNeighbors(x, y) {{
            const neighbors = [];
            const dirs = [[0, 1], [0, -1], [1, 0], [-1, 0]];
            for (const [dx, dy] of dirs) {{
                const nx = x + dx, ny = y + dy;
                if (nx >= 0 && nx < BOARD_SIZE && ny >= 0 && ny < BOARD_SIZE) {{
                    neighbors.push([nx, ny]);
                }}
            }}
            return neighbors;
        }}

        function getGroup(board, x, y, color, group = null) {{
            if (!group) group = new Set();
            const key = `${{x}},${{y}}`;
            if (group.has(key)) return group;
            if (board[y][x] !== color) return group;

            group.add(key);
            for (const [nx, ny] of getNeighbors(x, y)) {{
                getGroup(board, nx, ny, color, group);
            }}
            return group;
        }}

        function getLiberties(board, x, y) {{
            const color = board[y][x];
            const group = getGroup(board, x, y, color);
            const liberties = new Set();

            for (const key of group) {{
                const [gx, gy] = key.split(',').map(Number);
                for (const [nx, ny] of getNeighbors(gx, gy)) {{
                    if (board[ny][nx] === null) {{
                        liberties.add(`${{nx}},${{ny}}`);
                    }}
                }}
            }}

            return liberties;
        }}

        // 绘制棋盘
        function drawBoard() {{
            const {{ margin, gridSize, baseMargin, coordMargin }} = getGridParams();
            const size = canvas.width;

            // 背景
            ctx.fillStyle = '#E3C16F';
            ctx.fillRect(0, 0, size, size);

            // 网格线 - 使用 margin（已包含坐标区域）
            ctx.strokeStyle = '#666';
            ctx.lineWidth = 1;

            for (let i = 0; i < BOARD_SIZE; i++) {{
                // 横线
                ctx.beginPath();
                ctx.moveTo(margin, margin + i * gridSize);
                ctx.lineTo(size - margin, margin + i * gridSize);
                ctx.stroke();

                // 竖线
                ctx.beginPath();
                ctx.moveTo(margin + i * gridSize, margin);
                ctx.lineTo(margin + i * gridSize, size - margin);
                ctx.stroke();
            }}

            // 绘制坐标标签
            ctx.fillStyle = '#333';
            ctx.font = `bold ${{Math.max(8, gridSize * 0.28)}}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            for (let i = 0; i < BOARD_SIZE; i++) {{
                // 横坐标 (A-S, 跳过 I)
                const colLabel = String.fromCharCode(65 + i + (i >= 8 ? 1 : 0));
                // 上方
                ctx.fillText(colLabel, margin + i * gridSize, baseMargin + coordMargin * 0.3);
                // 下方
                ctx.fillText(colLabel, margin + i * gridSize, size - baseMargin - coordMargin * 0.3);
                
                // 纵坐标 (1-19)
                const rowLabel = (BOARD_SIZE - i).toString();
                // 左侧
                ctx.fillText(rowLabel, baseMargin + coordMargin * 0.3, margin + i * gridSize);
                // 右侧
                ctx.fillText(rowLabel, size - baseMargin - coordMargin * 0.3, margin + i * gridSize);
            }}

            // 星位
            const stars = BOARD_SIZE === 19 ? [3, 9, 15] : [2, 6, 10];
            ctx.fillStyle = '#333';
            for (const x of stars) {{
                for (const y of stars) {{
                    ctx.beginPath();
                    ctx.arc(margin + x * gridSize, margin + y * gridSize, 3, 0, Math.PI * 2);
                    ctx.fill();
                }}
            }}
        }}

        // 绘制棋子
        function drawStone(x, y, color, isLast = false, moveNum = null) {{
            const {{ margin, gridSize }} = getGridParams();
            const cx = margin + x * gridSize;
            const cy = margin + y * gridSize;
            // 棋子尺寸
            const radius = gridSize * 0.48;

            ctx.beginPath();
            ctx.arc(cx, cy, radius, 0, Math.PI * 2);

            // 渐变效果
            const gradient = ctx.createRadialGradient(
                cx - radius * 0.3, cy - radius * 0.3, radius * 0.1,
                cx, cy, radius
            );

            if (color === 'black') {{
                gradient.addColorStop(0, '#666');
                gradient.addColorStop(1, '#000');
            }} else {{
                gradient.addColorStop(0, '#fff');
                gradient.addColorStop(1, '#ccc');
            }}

            ctx.fillStyle = gradient;
            ctx.fill();

            const showNumbers = document.getElementById('showNumbers').checked;

            // 最后一手标记 - 只有在不显示手数时才显示
            if (isLast && !showNumbers) {{
                ctx.beginPath();
                ctx.arc(cx, cy, radius * 0.25, 0, Math.PI * 2);
                ctx.fillStyle = color === 'black' ? '#fff' : '#000';
                ctx.fill();
            }}

            // 手数显示
            if (moveNum && showNumbers) {{
                ctx.fillStyle = color === 'black' ? '#fff' : '#000';
                // 增大手数字体
                ctx.font = `bold ${{Math.floor(gridSize * 0.55)}}px Arial`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(moveNum.toString(), cx, cy);
            }}
        }}

        // 更新显示
        function updateDisplay() {{
            drawBoard();

            const board = createBoard();
            let blackCaptured = 0;
            let whiteCaptured = 0;

            for (let i = 0; i < currentMove; i++) {{
                const move = moves[i];
                const opponent = move.color === 'black' ? 'white' : 'black';

                // 检查是否可以下子（简化处理，不处理所有规则）
                board[move.y][move.x] = move.color;

                // 检查提子
                for (const [nx, ny] of getNeighbors(move.x, move.y)) {{
                    if (board[ny][nx] === opponent) {{
                        const liberties = getLiberties(board, nx, ny);
                        if (liberties.size === 0) {{
                            const group = getGroup(board, nx, ny, opponent);
                            for (const key of group) {{
                                const [gx, gy] = key.split(',').map(Number);
                                board[gy][gx] = null;
                                if (opponent === 'white') blackCaptured++;
                                else whiteCaptured++;
                            }}
                        }}
                    }}
                }}
            }}

            // 绘制所有棋子
            for (let y = 0; y < BOARD_SIZE; y++) {{
                for (let x = 0; x < BOARD_SIZE; x++) {{
                    if (board[y][x]) {{
                        const isLast = (currentMove > 0 &&
                            moves[currentMove - 1].x === x &&
                            moves[currentMove - 1].y === y);

                        // 找到这是第几手
                        let moveNum = null;
                        for (let i = 0; i < currentMove; i++) {{
                            if (moves[i].x === x && moves[i].y === y) {{
                                moveNum = i + 1;
                                break;
                            }}
                        }}

                        drawStone(x, y, board[y][x], isLast, moveNum);
                    }}
                }}
            }}

            // 更新状态信息
            document.getElementById('moveInfo').textContent = `第 ${{currentMove}} 手 / 共 ${{moves.length}} 手`;

            if (blackCaptured > 0 || whiteCaptured > 0) {{
                document.getElementById('capturedInfo').textContent =
                    `提子: 黑 ${{blackCaptured}} 子, 白 ${{whiteCaptured}} 子`;
            }} else {{
                document.getElementById('capturedInfo').textContent = '';
            }}
        }}

        // 控制函数
        function goToStart() {{
            currentMove = 0;
            updateDisplay();
        }}

        function goToEnd() {{
            currentMove = moves.length;
            updateDisplay();
        }}

        function prevMove() {{
            if (currentMove > 0) {{
                currentMove--;
                updateDisplay();
            }}
        }}

        function nextMove() {{
            if (currentMove < moves.length) {{
                currentMove++;
                updateDisplay();
            }}
        }}

        function togglePlay() {{
            const btn = document.getElementById('playBtn');
            if (isPlaying) {{
                clearInterval(playInterval);
                isPlaying = false;
                btn.textContent = '播';
            }} else {{
                if (currentMove >= moves.length) {{
                    currentMove = 0;
                }}
                const speed = 800; // 固定播放速度 0.8秒/手
                isPlaying = true;
                btn.textContent = '⏸';
                playInterval = setInterval(() => {{
                    if (currentMove < moves.length) {{
                        currentMove++;
                        updateDisplay();
                    }} else {{
                        togglePlay();
                    }}
                }}, speed);
            }}
        }}

        function downloadSGF() {{
            const blob = new Blob([sgfData], {{ type: 'application/x-go-sgf' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{input_base_name}.sgf';
            a.click();
            URL.revokeObjectURL(url);
        }}

        // 键盘控制
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowLeft') prevMove();
            else if (e.key === 'ArrowRight') nextMove();
            else if (e.key === ' ') togglePlay();
        }});

        // 触摸滑动支持
        let touchStartX = 0;
        canvas.addEventListener('touchstart', (e) => {{
            touchStartX = e.touches[0].clientX;
        }});

        canvas.addEventListener('touchend', (e) => {{
            const touchEndX = e.changedTouches[0].clientX;
            const diff = touchStartX - touchEndX;
            if (Math.abs(diff) > 50) {{
                if (diff > 0) nextMove();
                else prevMove();
            }}
        }});

        // 手数显示切换
        function toggleNumbers() {{
            const checkbox = document.getElementById('showNumbers');
            checkbox.checked = !checkbox.checked;
            updateDisplay();
            updateNumToggleBtn();
        }}
        
        function updateNumToggleBtn() {{
            const btn = document.getElementById('numToggleBtn');
            const checkbox = document.getElementById('showNumbers');
            if (checkbox.checked) {{
                btn.style.background = '#667eea';
                btn.style.color = 'white';
            }} else {{
                btn.style.background = '#f0f0f0';
                btn.style.color = '#333';
            }}
        }}
        
        // 手数滑动条控制
        function goToMove(moveNum) {{
            const target = parseInt(moveNum);
            if (target >= 0 && target <= moves.length) {{
                currentMove = target;
                updateDisplay();
            }}
        }}

        // ==================== 变化图功能 ====================

        // 更新变化图面板
        function updateVarPanel() {{
            const varPanel = document.getElementById('varPanel');
            const varList = document.getElementById('varList');

            if (inVariation || !variations[currentMove]) {{
                varPanel.style.display = 'none';
                return;
            }}

            varPanel.style.display = 'block';
            // 清空列表（使用 textContent 替代 innerHTML 避免安全扫描误报）
            varList.textContent = '';

            variations[currentMove].forEach((v, i) => {{
                const btn = document.createElement('button');
                btn.className = 'btn';
                btn.style.cssText = 'width: 72px; padding: 4px 0; height: 28px; font-size: 13px; background: #667eea; color: white; border-radius: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;';
                // 只显示胜率，不显示"变化X"
                btn.textContent = v.winRate || v.name.replace(/^变化\\d+\\s*/, '');
                btn.title = v.winRate || v.name;
                btn.onclick = () => enterVariation(v);
                varList.appendChild(btn);
            }});
        }}

        // 进入变化图
        function enterVariation(v) {{
            inVariation = true;
            varMoves = v.moves.map(m => ({{
                color: m.color === 'B' ? 'black' : 'white',
                x: m.coord.charCodeAt(0) - 97,
                y: m.coord.charCodeAt(1) - 97
            }}));
            varIndex = 2; // 默认显示第一手变化（跳过主分支分叉点，直接显示变化后的第一手）

            // 隐藏主控制面板和变化图列表
            document.getElementById('mainControls').style.display = 'none';
            document.getElementById('varPanel').style.display = 'none';
            document.getElementById('varControlPanel').style.display = 'block';

            updateVarButtons();
            updateDisplay();
        }}

        // 退出变化图
        function exitVariation() {{
            inVariation = false;
            varMoves = [];
            varIndex = 0;

            // 显示主控制面板
            document.getElementById('mainControls').style.display = 'flex';
            document.getElementById('varControlPanel').style.display = 'none';

            updateVarPanel();
            updateDisplay();
        }}

        // 变化图上一步
        function varPrev() {{
            if (varIndex > 0) {{
                varIndex--;
                updateVarButtons();
                updateDisplay();
            }}
        }}

        // 变化图下一步
        function varNext() {{
            if (varIndex < varMoves.length) {{
                varIndex++;
                updateVarButtons();
                updateDisplay();
            }}
        }}

        // 更新变化图按钮状态
        function updateVarButtons() {{
            const prevBtn = document.getElementById('varPrevBtn');
            const nextBtn = document.getElementById('varNextBtn');

            prevBtn.style.opacity = varIndex <= 0 ? '0.3' : '1';
            prevBtn.style.cursor = varIndex <= 0 ? 'not-allowed' : 'pointer';
            prevBtn.disabled = varIndex <= 0;

            nextBtn.style.opacity = varIndex >= varMoves.length ? '0.3' : '1';
            nextBtn.style.cursor = varIndex >= varMoves.length ? 'not-allowed' : 'pointer';
            nextBtn.disabled = varIndex >= varMoves.length;
        }}

        // 修改原有的绘制函数支持变化图
        const originalDrawBoard = updateDisplay;
        updateDisplay = function() {{
            if (inVariation) {{
                // 绘制主分支 + 变化图
                drawBoard();
                const board = createBoard();
                let blackCaptured = 0;
                let whiteCaptured = 0;

                // 主分支着法（带提子处理）
                for (let i = 0; i < currentMove && i < moves.length; i++) {{
                    const move = moves[i];
                    board[move.y][move.x] = move.color;
                    
                    // 检查提子
                    const opponent = move.color === 'black' ? 'white' : 'black';
                    for (const [nx, ny] of getNeighbors(move.x, move.y)) {{
                        if (board[ny][nx] === opponent) {{
                            const liberties = getLiberties(board, nx, ny);
                            if (liberties.size === 0) {{
                                const group = getGroup(board, nx, ny, opponent);
                                for (const key of group) {{
                                    const [gx, gy] = key.split(',').map(Number);
                                    board[gy][gx] = null;
                                    if (opponent === 'white') blackCaptured++;
                                    else whiteCaptured++;
                                }}
                            }}
                        }}
                    }}
                }}

                // 变化图着法（带提子处理）
                for (let i = 0; i < varIndex && i < varMoves.length; i++) {{
                    const move = varMoves[i];
                    board[move.y][move.x] = move.color;
                    
                    // 检查提子
                    const opponent = move.color === 'black' ? 'white' : 'black';
                    for (const [nx, ny] of getNeighbors(move.x, move.y)) {{
                        if (board[ny][nx] === opponent) {{
                            const liberties = getLiberties(board, nx, ny);
                            if (liberties.size === 0) {{
                                const group = getGroup(board, nx, ny, opponent);
                                for (const key of group) {{
                                    const [gx, gy] = key.split(',').map(Number);
                                    board[gy][gx] = null;
                                    if (opponent === 'white') blackCaptured++;
                                    else whiteCaptured++;
                                }}
                            }}
                        }}
                    }}
                }}

                // 绘制棋子 - 变化图模式下强制显示手数
                const {{ margin, gridSize }} = getGridParams();

                // 临时开启手数显示
                const showNumbersCheckbox = document.getElementById('showNumbers');
                const originalShowNumbers = showNumbersCheckbox.checked;
                showNumbersCheckbox.checked = true;

                for (let y = 0; y < BOARD_SIZE; y++) {{
                    for (let x = 0; x < BOARD_SIZE; x++) {{
                        if (board[y][x]) {{
                            // 检查是否是变化图的棋子，显示变化图手数（从1开始）
                            let varMoveNum = null;
                            for (let i = 0; i < varIndex && i < varMoves.length; i++) {{
                                if (varMoves[i].x === x && varMoves[i].y === y) {{
                                    varMoveNum = i + 1; // 变化图手数从1开始
                                    break;
                                }}
                            }}

                            // 变化图模式下不显示最后一手标记（因为有手数显示了）
                            const isLast = false;

                            drawStone(x, y, board[y][x], isLast, varMoveNum);
                        }}
                    }}
                }}

                // 恢复原来的手数显示设置
                showNumbersCheckbox.checked = originalShowNumbers;

                // 更新状态
                const totalMoves = currentMove + varIndex;
                document.getElementById('moveInfo').textContent = `第 ${{totalMoves}} 手`;
                
                // 显示提子信息
                if (blackCaptured > 0 || whiteCaptured > 0) {{
                    document.getElementById('capturedInfo').textContent =
                        `提子: 黑 ${{blackCaptured}} 子, 白 ${{whiteCaptured}} 子`;
                }} else {{
                    document.getElementById('capturedInfo').textContent = '';
                }}
                
                if (varIndex === 0) {{
                    document.getElementById('moveDetail').textContent = '变化图起点';
                }} else if (varIndex >= varMoves.length) {{
                    document.getElementById('moveDetail').textContent = '变化图结束';
                }} else {{
                    const last = varMoves[varIndex-1];
                    const coord = String.fromCharCode(97+last.x) + String.fromCharCode(97+last.y);
                    document.getElementById('moveDetail').textContent = coord.toUpperCase();
                }}
            }} else {{
                originalDrawBoard();
                updateVarPanel();
                // 同步滑动条位置
                document.getElementById('moveSlider').value = currentMove;
            }}
        }};

        // 修改键盘控制
        const originalPrev = prevMove;
        const originalNext = nextMove;
        prevMove = function() {{ if (inVariation) varPrev(); else originalPrev(); }};
        nextMove = function() {{ if (inVariation) varNext(); else originalNext(); }};

        // 初始化
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
        updateVarPanel();
        updateNumToggleBtn();
    </script>
</body>
</html>'''

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)

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
        # 如果指定的是完整路径，直接使用
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

    # 提取主分支着法
    print(f"📖 正在解析: {input_file}")
    main_moves = extract_main_branch(sgf_content)

    if not main_moves:
        print("❌ 错误: 无法从SGF中提取着法")
        sys.exit(1)

    print(f"   提取到 {len(main_moves)} 手主分支着法")

    # 提取变化图
    variations = extract_variations(sgf_content, main_moves)
    if variations:
        total = sum(len(v) for v in variations.values())
        print(f"   提取到 {total} 个变化图")

    # 提取棋局信息
    game_info = extract_game_info(sgf_content)

    # 获取输入文件名（不含扩展名）
    input_base_name = os.path.splitext(os.path.basename(input_file))[0]

    # 生成HTML
    generate_html(main_moves, game_info, variations, output_path, input_base_name)

    print(f"\n✅ 生成完成: {output_path}")


if __name__ == '__main__':
    main()

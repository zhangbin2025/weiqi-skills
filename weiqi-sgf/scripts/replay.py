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
import html


def extract_main_branch(sgf_content):
    """
    从野狐围棋SGF中提取主分支着法

    支持两种格式:
    1. 嵌套格式（野狐原始格式）：多行，每行一个分支
    2. 平面格式（已清理）：所有着法在一行，用分号分隔

    提取策略:
    1. 检测SGF格式类型
    2. 平面格式：按顺序提取所有着法，直到遇到变例分支
    3. 嵌套格式：按行处理，只取单着法的行
    """
    sgf_content = sgf_content.replace('\r\n', '\n')
    lines = sgf_content.split('\n')

    main_moves = []

    # 检测格式：如果第一行包含大量着法，认为是平面格式
    first_non_empty = ''
    for line in lines:
        stripped = line.strip()
        if stripped:
            first_non_empty = stripped
            break

    moves_in_first = re.findall(r';([BW])\[([a-z]{2})\]', first_non_empty)
    is_flat_format = len(moves_in_first) > 10  # 平面格式：第一行有很多着法

    if is_flat_format:
        # 平面格式：直接按顺序提取所有着法
        # 但需要处理可能的变化图分支（以 '(' 开头的新分支）
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 查找所有着法及其位置
            for match in re.finditer(r';([BW])\[([a-z]{2})\]', line):
                pos = match.start()

                # 检查这个着法是否在变例分支内（前面有未闭合的括号）
                # 简单方法：计算该位置前的 '(' 和 ')' 数量
                prefix = line[:pos]
                open_parens = prefix.count('(')
                close_parens = prefix.count(')')

                # SGF格式: (;GM...;B[pd]...) 主分支着法在 depth=1
                # 变例分支是嵌套的 (...)，depth > 1
                if open_parens - close_parens == 1:
                    color = match.group(1)
                    coord = match.group(2)
                    main_moves.append({
                        'color': color,
                        'coord': coord
                    })
    else:
        # 嵌套格式（原始野狐格式）：按行处理
        found_first_move = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            moves_in_line = re.findall(r';([BW])\[([a-z]{2})\]', line)

            if not moves_in_line:
                continue

            if not found_first_move:
                color, coord = moves_in_line[0]
                main_moves.append({
                    'color': color,
                    'coord': coord
                })
                found_first_move = True
                continue

            # 只取只有1个着法的行（主分支）
            if len(moves_in_line) == 1:
                color, coord = moves_in_line[0]
                main_moves.append({
                    'color': color,
                    'coord': coord
                })

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
        # 清理评论中的特殊字符，避免JSON解析错误
        comment = comment.replace('\\', '/').replace('"', '')

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
        'HA': ('handicap', r'HA\[(\d+)\]'),
    }

    for key, (name, pattern) in patterns.items():
        match = re.search(pattern, sgf_content)
        if match:
            info[name] = match.group(1)

    # 提取让子位置 (AB = Add Black)
    # 支持格式1: AB[pd][dp][dd][pp][jj] (连续多个，HA标签在同一行)
    # 支持格式2: ;AB[dd];AB[pp];AB[dp];AB[pd];AB[jj] (分散多个，每行一个)
    handicap_stones = []
    
    # 先尝试匹配分散格式 ;AB[xx]; (野狐围棋实时对局格式)
    for match in re.finditer(r';AB\[([a-z]{2})\]', sgf_content):
        coord = match.group(1)
        x = ord(coord[0]) - 97
        y = ord(coord[1]) - 97
        handicap_stones.append({'x': x, 'y': y})
    
    # 如果分散格式没找到，尝试匹配连续格式 AB[xx][yy][zz]
    if not handicap_stones:
        ab_match = re.search(r'AB((?:\[[a-z]{2}\])+)', sgf_content)
        if ab_match:
            # 提取所有 [xx] 中的坐标
            coords = re.findall(r'\[([a-z]{2})\]', ab_match.group(1))
            for coord in coords:
                x = ord(coord[0]) - 97
                y = ord(coord[1]) - 97
                handicap_stones.append({'x': x, 'y': y})
    
    info['handicap_stones'] = handicap_stones

    return info


def generate_html(main_moves, game_info, variations, output_path, input_base_name='棋谱'):
    """生成HTML打谱网页"""

    import json

    # 构建SGF字符串（平面格式）
    sgf_moves = ''.join([f";{m['color']}[{m['coord']}]" for m in main_moves])

    # 棋局信息（HTML转义防止XSS）
    black_name = html.escape(game_info.get('black', '黑棋'))
    white_name = html.escape(game_info.get('white', '白棋'))
    black_rank = html.escape(game_info.get('black_rank', ''))
    white_rank = html.escape(game_info.get('white_rank', ''))
    game_name = html.escape(game_info.get('game_name', '围棋棋谱'))
    game_date = html.escape(game_info.get('date', ''))
    result = html.escape(game_info.get('result', ''))
    handicap = game_info.get('handicap', '0')
    handicap_stones = game_info.get('handicap_stones', [])

    # 构建完整的SGF（SGF属性值需要转义]和\字符）
    board_size = game_info.get('board_size', '19')
    komi = game_info.get('komi', '375')

    # 添加让子标记到SGF
    handicap_sgf = f"HA[{handicap}]" if int(handicap) > 0 else ""
    for stone in handicap_stones:
        coord = chr(97 + stone['x']) + chr(97 + stone['y'])
        handicap_sgf += f"AB[{coord}]"

    # SGF内容需要转义HTML特殊字符后再嵌入
    sgf_raw = f"""(;GM[1]FF[4]
SZ[{board_size}]
GN[{game_info.get('game_name', '围棋棋谱')}]
DT[{game_info.get('date', '')}]
PB[{game_info.get('black', '黑棋')}]
PW[{game_info.get('white', '白棋')}]
BR[{game_info.get('black_rank', '')}]
WR[{game_info.get('white_rank', '')}]
KM[{komi}]{handicap_sgf}RU[Chinese]RE[{game_info.get('result', '')}]{sgf_moves})"""
    sgf_data = html.escape(sgf_raw)

    # 变化图数据（JSON转义后再HTML转义）
    variations_json = html.escape(json.dumps(variations, ensure_ascii=False))

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
            <div class="info" id="gameInfo">{black_name} vs {white_name} {'· 让' + handicap + '子' if int(handicap) > 0 else ''} · {result}</div>
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
                <button class="btn" id="soundToggleBtn" onclick="toggleSound()" title="音效开关" style="width: 32px; height: 32px; font-size: 14px; padding: 0; background: #f0f0f0;">🔊</button>
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

        <!-- 试下控制面板 -->
        <div id="trialControlPanel" style="display: none; margin: 8px 0; padding: 10px; background: #f0f0f0; border-radius: 8px;">
            <div style="display: flex; justify-content: center; align-items: center; gap: 24px;">
                <button class="btn" id="trialPrevBtn" onclick="trialPrev()" style="width: 40px; height: 40px; font-size: 16px; background: #667eea; color: white;">◀</button>
                <button class="btn" onclick="exitTrialMode()" style="width: 40px; height: 40px; font-size: 16px; background: #ff6b6b; color: white;">✕</button>
                <button class="btn" id="trialNextBtn" onclick="trialNext()" style="width: 40px; height: 40px; font-size: 16px; background: #667eea; color: white;">▶</button>
            </div>
        </div>

        <div class="status">
            <div class="move-info" id="moveInfo">第 0 手</div>
            <div class="move-detail" id="moveDetail" style="font-size: 14px; color: #666;"></div>
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
        // SGF 数据（HTML解码）
        const sgfData = (() => {{
            const textarea = document.createElement('textarea');
            textarea.innerHTML = `{sgf_data}`;
            return textarea.value;
        }})();

        const BOARD_SIZE = {board_size};

        // 让子信息
        const handicapStones = {json.dumps(handicap_stones)};
        const handicapCount = {handicap};

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

        // 变化图相关变量（HTML解码后解析JSON）
        const variations = JSON.parse((() => {{
            const textarea = document.createElement('textarea');
            textarea.innerHTML = `{variations_json}`;
            return textarea.value;
        }})());
        let inVariation = false;
        let varMoves = [];
        let varIndex = 0;

        // Canvas 设置
        const canvas = document.getElementById('board');
        const ctx = canvas.getContext('2d');

        // ==================== 音效系统 ====================
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        let soundEnabled = true;
        let audioUnlocked = false;
        let noiseBuffer = null;

        // 创建噪声缓冲区（用于真实围棋音效）
        function createNoiseBuffer() {{
            const bufferSize = audioCtx.sampleRate * 0.1;
            const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
            const data = buffer.getChannelData(0);
            for (let i = 0; i < bufferSize; i++) {{
                data[i] = Math.random() * 2 - 1;
            }}
            return buffer;
        }}

        // 解锁音频上下文（浏览器自动播放策略要求用户交互）
        function unlockAudio() {{
            if (!audioUnlocked && audioCtx.state === 'suspended') {{
                audioCtx.resume().then(() => {{
                    audioUnlocked = true;
                }});
            }}
            if (!noiseBuffer) {{
                noiseBuffer = createNoiseBuffer();
            }}
        }}
        document.addEventListener('click', unlockAudio, {{ once: true }});
        document.addEventListener('touchstart', unlockAudio, {{ once: true }});
        document.addEventListener('keydown', unlockAudio, {{ once: true }});

        // 落子音效 - 木石碰撞声（使用噪声合成）
        function playStoneSound() {{
            if (!soundEnabled) return;
            if (audioCtx.state === 'suspended') {{
                audioCtx.resume();
            }}
            if (!noiseBuffer) {{
                noiseBuffer = createNoiseBuffer();
            }}
            
            // 白噪声 + bandpass 滤波器模拟木石碰撞
            const noise = audioCtx.createBufferSource();
            noise.buffer = noiseBuffer;
            
            const filter = audioCtx.createBiquadFilter();
            filter.type = 'bandpass';
            filter.frequency.value = 2500;
            filter.Q.value = 1;
            
            const gain = audioCtx.createGain();
            gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.06);
            
            noise.connect(filter);
            filter.connect(gain);
            gain.connect(audioCtx.destination);
            
            noise.start(audioCtx.currentTime);
            noise.stop(audioCtx.currentTime + 0.06);
            
            // 添加谐波增强木质感
            const osc = audioCtx.createOscillator();
            osc.type = 'triangle';
            osc.frequency.value = 400;
            
            const oscGain = audioCtx.createGain();
            oscGain.gain.setValueAtTime(0.15, audioCtx.currentTime);
            oscGain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.05);
            
            osc.connect(oscGain);
            oscGain.connect(audioCtx.destination);
            osc.start(audioCtx.currentTime);
            osc.stop(audioCtx.currentTime + 0.05);
        }}

        // 吃子音效 - 提子声（更低沉、稍长，带石子散落效果）
        function playCaptureSound() {{
            if (!soundEnabled) return;
            if (audioCtx.state === 'suspended') {{
                audioCtx.resume();
            }}
            if (!noiseBuffer) {{
                noiseBuffer = createNoiseBuffer();
            }}
            
            // 主提子声：低通滤波的白噪声
            const noise = audioCtx.createBufferSource();
            noise.buffer = noiseBuffer;
            
            const filter = audioCtx.createBiquadFilter();
            filter.type = 'lowpass';
            filter.frequency.value = 1200;
            filter.frequency.linearRampToValueAtTime(600, audioCtx.currentTime + 0.15);
            
            const gain = audioCtx.createGain();
            gain.gain.setValueAtTime(0.6, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.18);
            
            noise.connect(filter);
            filter.connect(gain);
            gain.connect(audioCtx.destination);
            
            noise.start(audioCtx.currentTime);
            noise.stop(audioCtx.currentTime + 0.18);
            
            // 添加随机微响声模拟石子散落
            for (let i = 0; i < 3; i++) {{
                setTimeout(() => {{
                    if (audioCtx.state === 'running' && soundEnabled) {{
                        const microNoise = audioCtx.createBufferSource();
                        microNoise.buffer = noiseBuffer;
                        const microFilter = audioCtx.createBiquadFilter();
                        microFilter.type = 'highpass';
                        microFilter.frequency.value = 3000;
                        const microGain = audioCtx.createGain();
                        microGain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                        microGain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.03);
                        microNoise.connect(microFilter);
                        microFilter.connect(microGain);
                        microGain.connect(audioCtx.destination);
                        microNoise.start(audioCtx.currentTime);
                        microNoise.stop(audioCtx.currentTime + 0.03);
                    }}
                }}, 50 + i * 30);
            }}
        }}

        // 多颗提子音效 - 增强版提子声
        function playMultiCaptureSound(count) {{
            if (!soundEnabled || count <= 0) return;
            
            // 播放主提子音
            playCaptureSound();
            
            // 额外添加更多石子散落声
            const now = audioCtx.currentTime;
            const extraCount = Math.min(count - 1, 4);
            for (let i = 0; i < extraCount; i++) {{
                setTimeout(() => {{
                    if (audioCtx.state === 'running' && soundEnabled) {{
                        const noise = audioCtx.createBufferSource();
                        noise.buffer = noiseBuffer;
                        const filter = audioCtx.createBiquadFilter();
                        filter.type = 'bandpass';
                        filter.frequency.value = 2000 - i * 200;
                        const gain = audioCtx.createGain();
                        gain.gain.setValueAtTime(0.3 - i * 0.05, audioCtx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.08);
                        noise.connect(filter);
                        filter.connect(gain);
                        gain.connect(audioCtx.destination);
                        noise.start(audioCtx.currentTime);
                        noise.stop(audioCtx.currentTime + 0.08);
                    }}
                }}, i * 60);
            }}
        }}

        // 切换音效开关
        function toggleSound() {{
            soundEnabled = !soundEnabled;
            updateSoundBtn();
        }}

        function updateSoundBtn() {{
            const btn = document.getElementById('soundToggleBtn');
            if (soundEnabled) {{
                btn.textContent = '🔊';
                btn.style.background = '#f0f0f0';
                btn.style.color = '#333';
            }} else {{
                btn.textContent = '🔇';
                btn.style.background = '#ff6b6b';
                btn.style.color = 'white';
            }}
        }}

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

        // 跟踪上一次的提子数量用于音效判断
        let lastBlackCaptured = 0;
        let lastWhiteCaptured = 0;

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

            // 播放音效（仅在向前移动时）
            const newBlackCaptured = blackCaptured - lastBlackCaptured;
            const newWhiteCaptured = whiteCaptured - lastWhiteCaptured;
            const totalNewCaptured = newBlackCaptured + newWhiteCaptured;

            if (totalNewCaptured > 0) {{
                // 有提子
                if (totalNewCaptured >= 3) {{
                    playMultiCaptureSound(totalNewCaptured);
                }} else {{
                    playCaptureSound();
                }}
            }} else if (currentMove > 0 && currentMove > (window.lastMoveNum || 0)) {{
                // 单纯落子（向前移动）
                playStoneSound();
            }}

            // 更新记录
            lastBlackCaptured = blackCaptured;
            lastWhiteCaptured = whiteCaptured;
            window.lastMoveNum = currentMove;

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
            a.download = '{html.escape(input_base_name)}.sgf';
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

        // ==================== 试下功能 ====================
        let inTrialMode = false;
        let trialMoves = [];
        let trialIndex = 0;
        let trialCurrentPlayer = 'black';
        let trialCapturedBlack = 0;
        let trialCapturedWhite = 0;
        let trialKoPosition = null;

        function createBoardFromMainMoves(moveCount) {{
            const board = createBoard();
            for (let i = 0; i < moveCount && i < moves.length; i++) {{
                const move = moves[i];
                board[move.y][move.x] = move.color;
                const opponent = move.color === 'black' ? 'white' : 'black';
                for (const [nx, ny] of getNeighbors(move.x, move.y)) {{
                    if (board[ny][nx] === opponent) {{
                        const liberties = getLiberties(board, nx, ny);
                        if (liberties.size === 0) {{
                            const group = getGroup(board, nx, ny, opponent);
                            for (const key of group) {{
                                const [gx, gy] = key.split(',').map(Number);
                                board[gy][gx] = null;
                            }}
                        }}
                    }}
                }}
            }}
            return board;
        }}

        function getStoneAt(board, x, y) {{
            return board[y][x];
        }}

        function findGroupOnBoard(board, startX, startY, color) {{
            const group = [];
            const visited = new Set();
            const stack = [{{x: startX, y: startY}}];
            while (stack.length > 0) {{
                const {{x, y}} = stack.pop();
                const key = `${{x}},${{y}}`;
                if (visited.has(key)) continue;
                visited.add(key);
                if (board[y][x] === color) {{
                    group.push({{x, y}});
                    for (const [nx, ny] of getNeighbors(x, y)) {{
                        stack.push({{x: nx, y: ny}});
                    }}
                }}
            }}
            return group;
        }}

        function countLibertiesOnBoard(board, group) {{
            const liberties = new Set();
            for (const stone of group) {{
                const neighbors = getNeighbors(stone.x, stone.y);
                for (const [nx, ny] of neighbors) {{
                    if (ny >= 0 && ny < BOARD_SIZE && nx >= 0 && nx < BOARD_SIZE) {{
                        if (board[ny][nx] === null) {{
                            liberties.add(`${{nx}},${{ny}}`);
                        }}
                    }}
                }}
            }}
            return liberties.size;
        }}

        function isSuicideOnBoard(board, x, y, color) {{
            const opponent = color === 'black' ? 'white' : 'black';
            board[y][x] = color;
            let canCapture = false;
            const checked = new Set();
            for (const [nx, ny] of getNeighbors(x, y)) {{
                if (board[ny][nx] === opponent) {{
                    const key = `${{nx}},${{ny}}`;
                    if (!checked.has(key)) {{
                        const group = findGroupOnBoard(board, nx, ny, opponent);
                        for (const s of group) checked.add(`${{s.x}},${{s.y}}`);
                        if (countLibertiesOnBoard(board, group) === 0) canCapture = true;
                    }}
                }}
            }}
            const myGroup = findGroupOnBoard(board, x, y, color);
            const myLiberties = countLibertiesOnBoard(board, myGroup);
            board[y][x] = null;
            return myLiberties === 0 && !canCapture;
        }}

        function removeDeadStonesOnBoard(board, x, y, color) {{
            const opponent = color === 'black' ? 'white' : 'black';
            const captured = [];
            const checked = new Set();
            for (const [nx, ny] of getNeighbors(x, y)) {{
                if (board[ny][nx] === opponent) {{
                    const key = `${{nx}},${{ny}}`;
                    if (checked.has(key)) continue;
                    const group = findGroupOnBoard(board, nx, ny, opponent);
                    for (const s of group) checked.add(`${{s.x}},${{s.y}}`);
                    if (countLibertiesOnBoard(board, group) === 0) {{
                        for (const s of group) {{
                            captured.push({{x: s.x, y: s.y}});
                            board[s.y][s.x] = null;
                        }}
                    }}
                }}
            }}
            return captured;
        }}

        function checkKoOnBoard(board, x, y, color, captured) {{
            if (captured.length !== 1) return null;
            const opponent = color === 'black' ? 'white' : 'black';
            const capturedPos = captured[0];
            board[capturedPos.y][capturedPos.x] = opponent;
            const myGroup = findGroupOnBoard(board, x, y, color);
            const myLiberties = countLibertiesOnBoard(board, myGroup);
            const canBeCaptured = myLiberties === 0 && myGroup.length === 1;
            board[capturedPos.y][capturedPos.x] = null;
            if (canBeCaptured) return {{x: capturedPos.x, y: capturedPos.y}};
            return null;
        }}

        function enterTrialMode() {{
            // 播放中时不能试下
            if (isPlaying) return;
            // 变化图模式下暂不支持试下
            if (inVariation) {{
                alert('变化图模式下暂不支持试下功能');
                return;
            }}
            inTrialMode = true;
            trialMoves = [];
            trialIndex = 0;
            trialCurrentPlayer = (currentMove % 2 === 0) ? 'black' : 'white';
            trialCapturedBlack = 0;
            trialCapturedWhite = 0;
            trialKoPosition = null;
            document.getElementById('mainControls').style.display = 'none';
            document.getElementById('varPanel').style.display = 'none';
            document.getElementById('trialControlPanel').style.display = 'block';
            updateTrialButtons();
            updateDisplay();
        }}

        function exitTrialMode() {{
            inTrialMode = false;
            trialMoves = [];
            trialIndex = 0;
            trialKoPosition = null;
            document.getElementById('mainControls').style.display = 'flex';
            document.getElementById('trialControlPanel').style.display = 'none';
            updateVarPanel();
            updateDisplay();
        }}

        function trialPlaceStone(x, y) {{
            const board = createBoardFromMainMoves(currentMove);
            for (let i = 0; i < trialIndex && i < trialMoves.length; i++) {{
                const m = trialMoves[i];
                board[m.y][m.x] = m.color;
                removeDeadStonesOnBoard(board, m.x, m.y, m.color);
            }}
            if (getStoneAt(board, x, y) !== null) return false;
            if (trialKoPosition && trialKoPosition.x === x && trialKoPosition.y === y) return false;
            if (isSuicideOnBoard(board, x, y, trialCurrentPlayer)) return false;
            board[y][x] = trialCurrentPlayer;
            const captured = removeDeadStonesOnBoard(board, x, y, trialCurrentPlayer);
            trialKoPosition = checkKoOnBoard(board, x, y, trialCurrentPlayer, captured);
            if (trialCurrentPlayer === 'black') trialCapturedWhite += captured.length;
            else trialCapturedBlack += captured.length;
            trialMoves = trialMoves.slice(0, trialIndex);
            trialMoves.push({{x, y, color: trialCurrentPlayer, captured: captured.length}});
            trialIndex++;
            trialCurrentPlayer = trialCurrentPlayer === 'black' ? 'white' : 'black';
            if (captured.length > 0) {{
                if (captured.length >= 3) playMultiCaptureSound(captured.length);
                else playCaptureSound();
            }} else {{
                playStoneSound();
            }}
            updateTrialButtons();
            updateDisplay();
            return true;
        }}

        function trialPrev() {{
            if (trialIndex > 0) {{
                trialIndex--;
                const move = trialMoves[trialIndex];
                if (move.color === 'black') trialCapturedWhite -= move.captured || 0;
                else trialCapturedBlack -= move.captured || 0;
                trialCurrentPlayer = move.color;
                trialKoPosition = null;
                updateTrialButtons();
                updateDisplay();
            }}
        }}

        function trialNext() {{
            if (trialIndex < trialMoves.length) {{
                const move = trialMoves[trialIndex];
                trialIndex++;
                if (move.color === 'black') trialCapturedWhite += move.captured || 0;
                else trialCapturedBlack += move.captured || 0;
                trialCurrentPlayer = move.color === 'black' ? 'white' : 'black';
                updateTrialButtons();
                updateDisplay();
            }}
        }}

        function updateTrialButtons() {{
            const prevBtn = document.getElementById('trialPrevBtn');
            const nextBtn = document.getElementById('trialNextBtn');
            prevBtn.style.opacity = trialIndex <= 0 ? '0.3' : '1';
            prevBtn.style.cursor = trialIndex <= 0 ? 'not-allowed' : 'pointer';
            prevBtn.disabled = trialIndex <= 0;
            nextBtn.style.opacity = trialIndex >= trialMoves.length ? '0.3' : '1';
            nextBtn.style.cursor = trialIndex >= trialMoves.length ? 'not-allowed' : 'pointer';
            nextBtn.disabled = trialIndex >= trialMoves.length;
        }}

        function handleBoardClick(e) {{
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const x = (e.clientX - rect.left) * scaleX;
            const y = (e.clientY - rect.top) * scaleY;
            const {{margin, gridSize}} = getGridParams();
            const bx = Math.round((x - margin) / gridSize);
            const by = Math.round((y - margin) / gridSize);
            if (bx >= 0 && bx < BOARD_SIZE && by >= 0 && by < BOARD_SIZE) {{
                if (inTrialMode) {{
                    trialPlaceStone(bx, by);
                }} else if (!isPlaying) {{
                    enterTrialMode();
                    trialPlaceStone(bx, by);
                }}
            }}
        }}

        canvas.addEventListener('click', handleBoardClick);
        canvas.addEventListener('touchstart', function(e) {{
            e.preventDefault();
            const touch = e.touches[0];
            handleBoardClick(touch);
        }}, {{ passive: false }});

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

        // 变化图提子跟踪
        let varLastBlackCaptured = 0;
        let varLastWhiteCaptured = 0;

        // 进入变化图
        function enterVariation(v) {{
            inVariation = true;
            varMoves = v.moves.map(m => ({{
                color: m.color === 'B' ? 'black' : 'white',
                x: m.coord.charCodeAt(0) - 97,
                y: m.coord.charCodeAt(1) - 97
            }}));
            varIndex = 2; // 默认显示第一手变化（跳过主分支分叉点，直接显示变化后的第一手）

            // 重置变化图提子记录
            varLastBlackCaptured = 0;
            varLastWhiteCaptured = 0;
            window.varLastMoveNum = 2;

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

            // 重置主分支音效记录
            lastBlackCaptured = 0;
            lastWhiteCaptured = 0;
            window.lastMoveNum = currentMove;

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

        // 绘制半透明棋子
        function drawStoneWithOpacity(x, y, color, isLast, moveNum, opacity) {{
            const {{margin, gridSize}} = getGridParams();
            const cx = margin + x * gridSize;
            const cy = margin + y * gridSize;
            const radius = gridSize * 0.48;
            ctx.save();
            ctx.globalAlpha = opacity;
            ctx.beginPath();
            ctx.arc(cx, cy, radius, 0, Math.PI * 2);
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
            ctx.restore();
        }}

        // 修改原有的绘制函数支持变化图和试下
        const originalDrawBoard = updateDisplay;
        updateDisplay = function() {{
            if (inTrialMode) {{
                // 试下模式绘制
                drawBoard();
                const showNumbers = document.getElementById('showNumbers').checked;
                
                // 构建棋盘状态（使用与 trialPlaceStone 相同的逻辑）
                const board = createBoardFromMainMoves(currentMove);
                
                // 应用试下着法
                for (let i = 0; i < trialIndex && i < trialMoves.length; i++) {{
                    const m = trialMoves[i];
                    board[m.y][m.x] = m.color;
                    removeDeadStonesOnBoard(board, m.x, m.y, m.color);
                }}
                
                // 收集所有棋子用于绘制
                const trialPositions = new Set();
                for (let i = 0; i < trialIndex && i < trialMoves.length; i++) {{
                    trialPositions.add(`${{trialMoves[i].x}},${{trialMoves[i].y}}`);
                }}
                
                const lastTrialMove = trialIndex > 0 ? trialMoves[trialIndex - 1] : null;
                
                // 绘制所有棋子
                // 使用包含试下着法的 board（已计算提子）
                for (let y = 0; y < BOARD_SIZE; y++) {{
                    for (let x = 0; x < BOARD_SIZE; x++) {{
                        if (board[y][x]) {{
                            const isTrial = trialPositions.has(`${{x}},${{y}}`);
                            if (isTrial) {{
                                // 试下棋子 - 强制显示手数（从1开始）
                                const moveIdx = [...trialPositions].indexOf(`${{x}},${{y}}`);
                                // 绘制棋子（不显示最后一手标记，因为会挡住手数）
                                drawStone(x, y, board[y][x], false, null);
                                // 绘制手数（强制显示，不依赖手数开关）
                                const {{margin: m2, gridSize: gs2}} = getGridParams();
                                const cx2 = m2 + x * gs2;
                                const cy2 = m2 + y * gs2;
                                ctx.fillStyle = board[y][x] === 'black' ? '#fff' : '#000';
                                ctx.font = `bold ${{Math.floor(gs2 * 0.55)}}px Arial`;
                                ctx.textAlign = 'center';
                                ctx.textBaseline = 'middle';
                                ctx.fillText((moveIdx + 1).toString(), cx2, cy2);
                            }} else {{
                                // 主分支棋子 - 正常显示
                                drawStone(x, y, board[y][x], false, null);
                            }}
                        }}
                    }}
                }}
                // 试下模式 - 清空状态文字
                document.getElementById('moveInfo').textContent = '';
                document.getElementById('capturedInfo').textContent = '';
            }} else if (inVariation) {{
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

                // 变化图音效
                const varNewBlackCaptured = blackCaptured - varLastBlackCaptured;
                const varNewWhiteCaptured = whiteCaptured - varLastWhiteCaptured;
                const varTotalNewCaptured = varNewBlackCaptured + varNewWhiteCaptured;

                if (varTotalNewCaptured > 0) {{
                    if (varTotalNewCaptured >= 3) {{
                        playMultiCaptureSound(varTotalNewCaptured);
                    }} else {{
                        playCaptureSound();
                    }}
                }} else if (varIndex > 0 && varIndex > (window.varLastMoveNum || 0)) {{
                    playStoneSound();
                }}

                varLastBlackCaptured = blackCaptured;
                varLastWhiteCaptured = whiteCaptured;
                window.varLastMoveNum = varIndex;

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
        
        // 绘制让子
        function drawHandicapStones() {{
            if (handicapStones && handicapStones.length > 0) {{
                for (const stone of handicapStones) {{
                    drawStone(stone.x, stone.y, 'black', false, null);
                }}
            }}
        }}
        
        // 在初始绘制后添加让子
        const _originalDrawBoard = drawBoard;
        drawBoard = function() {{
            _originalDrawBoard();
            drawHandicapStones();
        }};
        
        // 修改createBoard函数以包含让子
        const _originalCreateBoard = createBoard;
        createBoard = function() {{
            const board = _originalCreateBoard();
            if (handicapStones && handicapStones.length > 0) {{
                for (const stone of handicapStones) {{
                    board[stone.y][stone.x] = 'black';
                }}
            }}
            return board;
        }};
        
        updateVarPanel();
        updateNumToggleBtn();
        updateSoundBtn();
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

    # 提取变化图（包含全部）
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

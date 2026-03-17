#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGF围棋打谱网页生成器
将野狐围棋SGF文件转换为交互式HTML打谱网页

使用方法:
    python3 sgf_to_html.py input.sgf [output.html]
    
示例:
    python3 sgf_to_html.py game.sgf
    python3 sgf_to_html.py game.sgf viewer.html
"""

import sys
import re
import os


def extract_main_branch(sgf_content):
    """
    从野狐围棋SGF中提取主分支着法
    
    野狐SGF格式特点:
    - 使用线性嵌套保存变化图: (;B[qd](;W[pp](;B[dc]...)...)
    - 主分支是沿着第一个子节点走的线路
    - depth 1-N 每个depth只有一个着法的部分是主分支
    - depth=N+1 的第一个着法（后面直接是)）是主分支的最后一手
    
    提取策略:
    1. 计算每个着法的括号深度
    2. 统计每个深度的着法数量
    3. 提取主分支：每个depth只有一个着法的连续序列
    4. 对于depth=N+1，只取第一个子节点
    """
    # 清理换行符
    sgf = sgf_content.replace('\r\n', '').replace('\n', '')
    
    # 提取所有着法及其深度
    moves = []
    for match in re.finditer(r';([BW])\[([a-z]{2})\]', sgf):
        pos = match.start()
        # 计算括号深度
        depth = 0
        for j in range(pos):
            if sgf[j] == '(':
                depth += 1
            elif sgf[j] == ')':
                depth -= 1
        
        moves.append({
            'color': match.group(1),
            'coord': match.group(2),
            'depth': depth
        })
    
    # 按深度分组
    depth_groups = {}
    for m in moves:
        if m['depth'] not in depth_groups:
            depth_groups[m['depth']] = []
        depth_groups[m['depth']].append(m)
    
    # 提取主分支
    # 主分支是depth连续递增，且每个depth只有一个着法的部分
    main_moves = []
    prev_depth = 0
    
    for d in sorted(depth_groups.keys()):
        group = depth_groups[d]
        
        if d == prev_depth + 1:
            # depth连续递增
            # 取第一个着法作为主分支
            main_moves.append(group[0])
            prev_depth = d
            
            # 如果当前depth有多个着法，说明后续都是变化图，停止
            if len(group) > 1:
                break
        else:
            # depth不连续，停止
            break
    
    return main_moves


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


def generate_html(main_moves, game_info, output_path):
    """生成HTML打谱网页"""
    
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
    
    # HTML模板
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{game_name}}</title>
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
            padding: 10px;
        }}
        .container {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            padding: 15px;
            max-width: 100%;
            width: 100%;
        }}
        .header {{
            text-align: center;
            margin-bottom: 12px;
        }}
        .header h1 {{
            font-size: 18px;
            color: #333;
            margin-bottom: 6px;
            line-height: 1.3;
        }}
        .header .info {{
            color: #666;
            font-size: 12px;
            line-height: 1.6;
        }}
        .board-container {{
            display: flex;
            justify-content: center;
            margin: 10px 0;
            position: relative;
        }}
        #board {{
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            max-width: 100%;
            height: auto;
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
            <h1 id="gameTitle">{game_name}</h1>
            <div class="info" id="gameInfo">
                加载中...
            </div>
        </div>

        <div class="board-container">
            <canvas id="board"></canvas>
        </div>

        <div class="controls">
            <button class="btn" onclick="goToStart()" title="跳到开头">⏮</button>
            <button class="btn" onclick="prevMove()" title="上一手">◀</button>
            <button class="btn btn-primary" id="playBtn" onclick="togglePlay()" title="播放/暂停">▶</button>
            <button class="btn" onclick="nextMove()" title="下一手">▶</button>
            <button class="btn" onclick="goToEnd()" title="跳到结尾">⏭</button>
        </div>

        <div class="settings">
            <div class="setting-item">
                <input type="checkbox" id="showNumbers" onchange="updateDisplay()">
                <label for="showNumbers">手数</label>
            </div>
            <div class="speed-control">
                <label>速度</label>
                <input type="range" id="speedRange" min="200" max="2000" value="800" step="200">
                <span id="speedValue">0.8s</span>
            </div>
            <button class="btn btn-success" onclick="downloadSGF()" title="下载SGF" style="width: 40px; height: 40px; font-size: 18px;">💾</button>
        </div>

        <div class="status">
            <div class="move-info" id="moveInfo">第 0 手</div>
            <div class="move-detail" id="moveDetail">点击播放开始打谱</div>
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

        // Canvas 设置
        const canvas = document.getElementById('board');
        const ctx = canvas.getContext('2d');
        
        function resizeCanvas() {{
            const container = document.querySelector('.board-container');
            const maxWidth = Math.min(container.clientWidth - 20, window.innerWidth - 40, 570);
            const size = Math.max(300, maxWidth);
            
            canvas.width = size;
            canvas.height = size;
            canvas.style.width = size + 'px';
            canvas.style.height = size + 'px';
            
            updateDisplay();
        }}

        function getGridParams() {{
            const margin = canvas.width * 0.05;
            const gridSize = (canvas.width - 2 * margin) / (BOARD_SIZE - 1);
            return {{ margin, gridSize }};
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
            const {{ margin, gridSize }} = getGridParams();
            const size = canvas.width;
            
            // 背景
            ctx.fillStyle = '#E3C16F';
            ctx.fillRect(0, 0, size, size);
            
            // 网格线
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
            const radius = gridSize * 0.42;
            
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
            
            // 最后一手标记
            if (isLast) {{
                ctx.beginPath();
                ctx.arc(cx, cy, radius * 0.25, 0, Math.PI * 2);
                ctx.fillStyle = color === 'black' ? '#fff' : '#000';
                ctx.fill();
            }}
            
            // 手数显示
            if (moveNum && document.getElementById('showNumbers').checked) {{
                ctx.fillStyle = color === 'black' ? '#fff' : '#000';
                ctx.font = `bold ${{Math.floor(gridSize * 0.5)}}px Arial`;
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
            
            if (currentMove > 0) {{
                const lastMove = moves[currentMove - 1];
                const coord = String.fromCharCode(97 + lastMove.x) + String.fromCharCode(97 + lastMove.y);
                const colorText = lastMove.color === 'black' ? '黑' : '白';
                document.getElementById('moveDetail').textContent = `${{colorText}}棋下在 ${{coord.toUpperCase()}}`;
            }} else {{
                document.getElementById('moveDetail').textContent = '点击播放开始打谱';
            }}
            
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
                btn.textContent = '▶';
            }} else {{
                if (currentMove >= moves.length) {{
                    currentMove = 0;
                }}
                const speed = parseInt(document.getElementById('speedRange').value);
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
            a.download = 'game.sgf';
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

        // 速度显示
        document.getElementById('speedRange').addEventListener('input', (e) => {{
            document.getElementById('speedValue').textContent = (e.target.value / 1000) + 's';
        }});

        // 初始化
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
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
        print("用法: python3 sgf_to_html.py input.sgf [output.html]")
        print("示例: python3 sgf_to_html.py game.sgf")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # 默认输出文件名
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        base_name = os.path.splitext(input_file)[0]
        output_file = base_name + '.html'
    
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
    
    # 提取棋局信息
    game_info = extract_game_info(sgf_content)
    
    # 生成HTML
    generate_html(main_moves, game_info, output_file)
    
    print(f"\n🌐 查看方式:")
    print(f"   python3 -m http.server 8080")
    print(f"   浏览器访问: http://localhost:8080/{output_file}")


if __name__ == '__main__':
    main()

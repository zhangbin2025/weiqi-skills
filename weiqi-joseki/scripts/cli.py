#!/usr/bin/env python3
"""
围棋定式数据库 - 命令行入口
"""

import sys
import argparse
from pathlib import Path

# 导入依赖模块
from .joseki_db import JosekiDB, DEFAULT_DB_PATH
from .joseki_extractor import extract_joseki_from_sgf, parse_multigogm
from .katago_downloader import (
    download_katago_games, iter_sgf_from_tar,
    DownloadManager, ProgressManager, MemoryMonitor
)


# KataGo 配置
KATAGO_CACHE_DIR = Path.home() / ".weiqi-joseki" / "katago-cache"
KATAGO_PROGRESS_FILE = Path.home() / ".weiqi-joseki" / "katago-progress.json"


def cmd_init(args):
    db = JosekiDB(args.db)
    db._save()
    print(f"✅ 已创建数据库: {db.db_path}")


def cmd_add(args):
    db = JosekiDB(args.db)
    
    moves = []
    if args.sgf:
        moves = [f"{m.group(1)}[{m.group(2)}]" for m in __import__('re').finditer(r';([BW])\[([a-z]{2})\]', args.sgf)]
    elif args.moves:
        moves = args.moves.split(",")
    
    if not moves:
        print("❌ 错误: 未提供有效的着法序列", file=sys.stderr)
        sys.exit(1)
    
    # 先标准化着法以检测角位
    coord_moves = db.normalize_moves(moves, ignore_pass=False)
    detected_corner = db.detect_corner(coord_moves)
    corner_names = {'tl': '左上', 'tr': '右上', 'bl': '左下', 'br': '右下'}
    
    if detected_corner:
        corner_desc = corner_names.get(detected_corner, detected_corner)
        if detected_corner == 'tr':
            print(f"📍 检测到角位: {corner_desc}（已是右上角视角，无需转换）")
        else:
            print(f"📍 检测到角位: {corner_desc} → 已自动转换为右上角视角")
    else:
        print(f"⚠️  无法自动识别角位，按原坐标入库")
    
    if not args.force:
        conflict = db.check_conflict(moves)
        if conflict.has_conflict:
            print("⚠️  检测到相同定式已存在:")
            for s in conflict.similar_joseki:
                print(f"    {s['id']}: {s.get('name', s['id'])}")
            print("使用 --force 强制添加")
            sys.exit(1)
    
    joseki_id, _ = db.add(
        name=args.name, category_path=args.category,
        moves=moves, tags=args.tag or [], description=args.description or "", force=args.force
    )
    
    if joseki_id:
        print(f"✅ 已添加定式: {joseki_id}")
    else:
        print("❌ 添加失败")
        sys.exit(1)


def cmd_remove(args):
    db = JosekiDB(args.db)
    joseki = db.get(args.id)
    if not joseki:
        print(f"❌ 未找到定式: {args.id}")
        sys.exit(1)
    if db.remove(args.id):
        print(f"✅ 已删除定式: {args.id}")


def cmd_clear(args):
    db = JosekiDB(args.db)
    count = len(db.joseki_list)
    if count == 0:
        print("数据库已经是空的")
        return
    if not args.force:
        confirm = input(f"确定要删除全部 {count} 个定式吗? [y/N]: ")
        if confirm.lower() != 'y':
            print("已取消")
            return
    deleted = db.clear()
    print(f"✅ 已清空数据库，删除 {deleted} 个定式")


def cmd_list(args):
    db = JosekiDB(args.db)
    joseki_list = db.list_all(category=args.category)
    if not joseki_list:
        print("数据库为空")
        return
    if args.limit:
        joseki_list = joseki_list[:args.limit]
    
    max_moves = getattr(args, 'max_moves', 8)
    
    # 新格式：ID, 分类, 手数, 次数, 概率, 着法, 名称
    print(f"{'ID':<10} {'分类':<16} {'手数':<4} {'次数':<7} {'概率':<8} {'着法':<{max_moves*3}} {'名称':<16}")
    print("-" * (60 + max_moves*3))
    for j in joseki_list:
        freq = str(j['frequency']) if j.get('frequency') is not None else "-"
        prob = f"{j['probability']:.2%}" if j.get('probability') is not None else "-"
        name = j['name'] if j.get('name') else "(空)"
        # 显示着法，截断到 max_moves
        moves = j.get('moves', [])
        if moves:
            display_moves = moves[:max_moves]
            moves_str = " ".join(display_moves)
            if len(moves) > max_moves:
                moves_str += "..."
        else:
            moves_str = "-"
        print(f"{j['id']:<10} {j['category_path']:<16} {j['move_count']:<4} {freq:<7} {prob:<8} {moves_str:<{max_moves*3+3}} {name:<16}")


def cmd_8way(args):
    """查看定式8向变化SGF"""
    db = JosekiDB(args.db)
    joseki = db.get(args.id)
    if not joseki:
        print(f"❌ 未找到定式: {args.id}")
        sys.exit(1)
    
    # 解析方向参数
    directions = None
    if args.direction:
        directions = [d.strip() for d in args.direction.split(',')]
        # 验证方向有效性
        valid_directions = ['lurd', 'ludr', 'ldru', 'ldur', 'ruld', 'rudl', 'rdlu', 'rdul']
        invalid = [d for d in directions if d not in valid_directions]
        if invalid:
            print(f"❌ 无效的方向: {invalid}")
            print(f"有效的方向: {', '.join(valid_directions)}")
            sys.exit(1)
    
    sgf = db.generate_8way_sgf(args.id, directions=directions)
    if sgf:
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(sgf)
            print(f"✅ 已保存到: {args.output}")
        else:
            print(sgf)
    else:
        print("❌ 生成SGF失败")


def _print_match_results(results):
    if not results:
        print("  无匹配")
        return
    # 新格式：显示前缀长度和总手数
    print(f"  {'排名':<6} {'ID':<12} {'名称':<25} {'前缀/总手':<12} {'方向':<8}")
    print("  " + "-" * 70)
    for i, r in enumerate(results, 1):
        prefix_str = f"{r.prefix_len}/{r.total_moves}"
        marker = " ✓" if r.prefix_len == r.total_moves else ""  # 完全匹配标记
        print(f"  {i:<6} {r.id:<12} {r.name:<25} {prefix_str:<12} {r.matched_direction:<8}{marker}")


def cmd_match(args):
    db = JosekiDB(args.db)
    sgf_data = ""
    if args.sgf_file:
        with open(args.sgf_file, 'r', encoding='utf-8') as f:
            sgf_data = f.read()
    elif args.sgf:
        sgf_data = args.sgf
    else:
        sgf_data = sys.stdin.read()
    
    if not sgf_data:
        print("❌ 错误: 未提供SGF数据", file=sys.stderr)
        sys.exit(1)
    
    # 解析多路参数（默认9,11,13）
    try:
        corner_sizes = [int(x.strip()) for x in args.corner_sizes.split(',')]
        corner_sizes = [x for x in corner_sizes if x in [9, 11, 13]]
        if not corner_sizes:
            corner_sizes = [9, 11, 13]
    except (ValueError, AttributeError):
        corner_sizes = [9, 11, 13]
    
    if args.corner:
        # 指定了具体角，进行多路匹配
        all_matches = []
        for size in corner_sizes:
            multigogm = extract_joseki_from_sgf(sgf_data, first_n=args.first_n, corner=args.corner, corner_size=size)
            parsed = parse_multigogm(multigogm)
            
            if args.corner not in parsed:
                continue
            
            comment, moves = parsed[args.corner]
            coord_seq = [c for _, c in moves if c]
            
            if not coord_seq:
                continue
            
            matches = db.match(coord_seq, top_k=args.top_k, corner='tr')
            for m in matches:
                object.__setattr__(m, 'matched_from_size', size)
            all_matches.extend(matches)
        
        # 按前缀长度排序
        if all_matches:
            all_matches.sort(key=lambda x: (-x.prefix_len, x.total_moves))
            results = all_matches[:args.top_k]
            print(f"\n『{args.corner.upper()}』角 (多路匹配 {corner_sizes}):")
            _print_match_results(results)
        else:
            print(f"⚠️  {args.corner} 角没有着法")
    else:
        # 未指定角，使用identify_corners（多路）
        results = db.identify_corners(sgf_data, top_k=args.top_k, first_n=args.first_n, 
                                       corner_sizes=corner_sizes)
        for corner in ['tl', 'tr', 'bl', 'br']:
            matches = results.get(corner, [])
            if matches:
                print(f"\n『{corner.upper()}』角:")
                _print_match_results(matches)


def cmd_identify(args):
    db = JosekiDB(args.db)
    sgf_data = ""
    if args.sgf_file:
        with open(args.sgf_file, 'r', encoding='utf-8') as f:
            sgf_data = f.read()
    elif args.sgf:
        sgf_data = args.sgf
    else:
        sgf_data = sys.stdin.read()
    
    if not sgf_data:
        print("❌ 错误: 未提供SGF数据", file=sys.stderr)
        sys.exit(1)
    
    # 解析多路参数（默认9,11,13）
    try:
        corner_sizes = [int(x.strip()) for x in args.corner_sizes.split(',')]
        corner_sizes = [x for x in corner_sizes if x in [9, 11, 13]]
        if not corner_sizes:
            corner_sizes = [9, 11, 13]
    except (ValueError, AttributeError):
        corner_sizes = [9, 11, 13]
    
    results = db.identify_corners(sgf_data, top_k=args.top_k, first_n=args.first_n, 
                                   corner_sizes=corner_sizes)
    
    if args.output == "json":
        import json
        output = {}
        for corner, matches in results.items():
            # 新的输出字段
            output[corner] = [{
                "id": m.id,
                "name": m.name,
                "prefix_len": m.prefix_len,
                "total_moves": m.total_moves
            } for m in matches]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 70)
        print("「定式识别结果」")
        if corner_sizes:
            print(f"（多路匹配: {corner_sizes}路，取最长前缀）")
        print("=" * 70)
        corner_names = {"tl": "左上", "tr": "右上", "bl": "左下", "br": "右下"}
        for corner in ["tl", "tr", "bl", "br"]:
            matches = results.get(corner, [])
            cn = corner_names.get(corner, corner)
            if matches:
                best = matches[0]
                # 显示来源路数
                from_size = getattr(best, 'matched_from_size', None)
                size_info = f"[{from_size}路] " if from_size else ""
                # 新格式：显示前缀/总手数
                match_str = f"{size_info}{best.name} ({best.prefix_len}/{best.total_moves}手)"
                if best.prefix_len == best.total_moves:
                    match_str += " ✓ 完全匹配"
                elif best.prefix_len >= 4:
                    match_str += " ✓ 高置信度"
            else:
                match_str = "(无匹配)"
            print(f"  {cn}: {match_str}")
        print("=" * 70)


def cmd_stats(args):
    db = JosekiDB(args.db)
    stats = db.stats()
    print(f"\n『定式库统计』")
    print(f"  数据库路径: {stats['db_path']}")
    print(f"  定式总数: {stats['total']}")
    if stats['by_category']:
        print(f"\n『按分类统计』")
        for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count} 个")


def cmd_extract(args):
    """从SGF提取四角定式，输出MULTIGOGM格式SGF"""
    sgf_data = ""
    if args.sgf_file:
        with open(args.sgf_file, 'r', encoding='utf-8') as f:
            sgf_data = f.read()
    else:
        sgf_data = sys.stdin.read()
    
    if not sgf_data:
        print("❌ 错误: 未提供SGF数据", file=sys.stderr)
        sys.exit(1)
    
    # 解析corner_sizes，取第一个作为extract的size（extract不支持多路）
    try:
        corner_sizes = [int(x.strip()) for x in args.corner_sizes.split(',')]
        corner_size = corner_sizes[0] if corner_sizes else 9
    except (ValueError, AttributeError):
        corner_size = 9
    
    result = extract_joseki_from_sgf(sgf_data, first_n=args.first_n, corner=args.corner, corner_size=corner_size)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"✅ 已保存到: {args.output}")
    else:
        print(result)


def cmd_import(args):
    """从SGF目录批量导入定式"""
    import os
    from pathlib import Path
    
    sgf_dir = Path(args.sgf_dir)
    if not sgf_dir.exists():
        print(f"❌ 错误: 目录不存在: {sgf_dir}")
        sys.exit(1)
    
    # 收集所有SGF文件
    sgf_files = list(sgf_dir.rglob("*.sgf"))
    if not sgf_files:
        print(f"⚠️  未找到SGF文件: {sgf_dir}")
        return
    
    print(f"📁 找到 {len(sgf_files)} 个SGF文件")
    
    # 使用 joseki_db 的导入功能
    db = JosekiDB(args.db)
    
    # 使用高精度CMS配置
    db.set_cms_config(width=4194304, depth=4)
    
    # 解析多路参数
    corner_sizes = None
    if args.corner_sizes:
        try:
            corner_sizes = [int(x.strip()) for x in args.corner_sizes.split(',')]
            corner_sizes = [x for x in corner_sizes if x in [9, 11, 13]]
            if not corner_sizes:
                corner_sizes = None
        except ValueError:
            corner_sizes = None
    
    # 导入定式
    if corner_sizes:
        print(f"\n⏳ 开始提取定式（前{args.first_n}手，多路: {corner_sizes}）...")
    else:
        print(f"\n⏳ 开始提取定式（前{args.first_n}手）...")
    
    def progress_callback(current, total, source, sgf_count):
        if current % 10 == 0 or current == total:
            print(f"\r  提取进度: {current}/{total}", end='', flush=True)
    
    added, skipped, candidates = db.import_from_sgfs(
        sgf_sources=sgf_files,
        min_count=args.min_count,
        min_moves=args.min_moves,
        min_rate=args.min_rate,
        first_n=args.first_n,
        corner_sizes=corner_sizes,
        dry_run=args.dry_run,
        progress_callback=progress_callback,
        category="/导入",
        verbose=True,
        top_k=args.top_k
    )
    
    print()  # 换行
    
    print(f"\n📊 统计结果：")
    print(f"   候选定式: {len(candidates)}个")
    print(f"{'排名':<6} {'频率':<8} {'定式':<40}")
    print("-" * 60)
    
    for rank, candidate in enumerate(candidates[:20], 1):
        if " (" in candidate:
            prefix, count_str = candidate.rsplit(" (", 1)
            count = count_str.replace("次)", "")
            print(f"{rank:<6} {count:<8} {prefix:<40} ({len(prefix.split())}手)")
    
    if args.dry_run:
        print(f"\n🧪 试运行模式，共找到 {len(candidates)} 个候选定式")
        return
    
    print(f"\n🎉 完成！新增 {added} 个定式，跳过 {skipped} 个（已存在）")


def cmd_export(args):
    """导出定式库到SGF"""
    db = JosekiDB(args.db)
    
    # 解析tags参数
    tags = None
    if args.tag:
        tags = [t.strip() for t in args.tag.split(',')]
    
    # 解析ids参数
    ids = None
    if args.id:
        ids = [i.strip() for i in args.id.split(',')]
    
    sgf = db.export_to_sgf(
        output_path=args.output,
        category=args.category,
        min_moves=args.min_moves,
        max_moves=args.max_moves,
        tags=tags,
        ids=ids
    )
    
    # 统计符合条件的定式数
    filtered_count = sgf.count('(;C[') - 1  # 减去根节点的C属性
    
    if args.output:
        print(f"✅ 已导出 {filtered_count} 个定式到: {args.output}")
    else:
        print(sgf)


def cmd_katago(args):
    """从KataGo棋谱库下载并提取定式"""
    import shutil
    import time
    import signal
    from datetime import datetime, timedelta
    
    # 参数处理
    cache_dir = Path(args.cache_dir) if args.cache_dir else KATAGO_CACHE_DIR
    progress_file = Path(args.progress_file) if args.progress_file else KATAGO_PROGRESS_FILE
    
    # 解析日期
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError:
        print("❌ 错误: 日期格式应为 YYYY-MM-DD")
        sys.exit(1)
    
    if start_date > end_date:
        print("❌ 错误: 起始日期不能晚于结束日期")
        sys.exit(1)
    
    # 生成日期列表
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    print(f"📅 日期范围: {args.start_date} 至 {args.end_date}（共{len(dates)}天）")
    print(f"💾 缓存目录: {cache_dir}")
    print(f"📊 进度文件: {progress_file}")
    
    # 初始化进度管理器
    progress = ProgressManager(progress_file)
    
    # 如果不resume，清除旧进度
    if not args.resume:
        progress.clear()
        print("🧹 已清除历史进度")
    
    # 过滤已完成的日期
    if args.resume:
        dates = [d for d in dates if not progress.is_completed(d)]
        print(f"⏩ 断点续传模式，剩余 {len(dates)} 天需要处理")
    
    if not dates:
        print("✅ 所有日期已处理完毕")
        return
    
    # 设置信号处理（捕获Ctrl+C）
    stop_flag = [False]
    
    def signal_handler(sig, frame):
        print("\n\n⚠️ 收到中断信号，正在保存进度...")
        stop_flag[0] = True
        progress.save()
        print("✅ 进度已保存，下次使用 --resume 继续")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 下载阶段
    print(f"\n📥 开始下载（并行{args.workers}线程）...")
    
    downloader = DownloadManager(
        cache_dir=cache_dir,
        max_retries=3,
        workers=args.workers,
        keep_cache=not args.remove_cache  # 默认保留缓存
    )
    
    # 在后台打印下载进度
    downloaded = {}
    download_error = [False]
    
    def download_worker():
        try:
            nonlocal downloaded
            downloaded = downloader.download(dates)
        except Exception as e:
            print(f"\n❌ 下载出错: {e}")
            download_error[0] = True
    
    download_thread = __import__('threading').Thread(target=download_worker)
    download_thread.start()
    
    # 显示下载进度
    while download_thread.is_alive():
        downloader.print_progress()
        time.sleep(0.5)
    
    download_thread.join()
    print()  # 换行
    
    if download_error[0]:
        print("❌ 下载过程中发生错误")
        sys.exit(1)
    
    print(f"✅ 下载完成: {len(downloaded)}/{len(dates)} 个文件")
    
    
    tar_files = []
    for date_str, tar_path in downloaded.items():
        if tar_path and tar_path.exists():
            tar_files.append(tar_path)
    
    # 解析多路参数
    corner_sizes = None
    if args.corner_sizes:
        try:
            corner_sizes = [int(x.strip()) for x in args.corner_sizes.split(',')]
            corner_sizes = [x for x in corner_sizes if x in [9, 11, 13]]
            if not corner_sizes:
                corner_sizes = None
        except ValueError:
            corner_sizes = None
    
    # 导入定式
    if corner_sizes:
        print(f"\n⏳ 开始提取定式（前{args.first_n}手，多路: {corner_sizes}）...")
    else:
        print(f"\n⏳ 开始提取定式（前{args.first_n}手）...")
    
    db = JosekiDB(args.db)
    
    # 使用高精度CMS配置
    db.set_cms_config(width=4194304, depth=4)
    
    def progress_callback(current, total, source, sgf_count):
        if current % 100 == 0 or current == total:
            print(f"\r  提取进度: {current}/{total}", end='', flush=True)
            progress.mark_completed(str(source)[:10], {'sgf_count': sgf_count})
    
    added, skipped, candidates = db.import_from_sgfs(
        sgf_sources=tar_files,
        min_count=args.min_count,
        min_moves=args.min_moves,
        min_rate=args.min_rate,
        first_n=args.first_n,
        corner_sizes=corner_sizes,
        dry_run=args.dry_run,
        progress_callback=progress_callback,
        category="/katago",
        verbose=True,
        top_k=args.top_k
    )
    
    print()  # 换行
    
    print(f"\n📊 统计结果：")
    print(f"   候选定式: {len(candidates)}个")
    print(f"{'排名':<6} {'频率':<8} {'定式':<40}")
    print("-" * 60)
    
    for rank, candidate in enumerate(candidates[:20], 1):
        if " (" in candidate:
            prefix, count_str = candidate.rsplit(" (", 1)
            count = count_str.replace("次)", "")
            print(f"{rank:<6} {count:<8} {prefix:<40} ({len(prefix.split())}手)")
    
    if args.dry_run:
        print(f"\n🧪 试运行模式，共找到 {len(candidates)} 个候选定式")
        return
    
    print(f"\n🎉 完成！新增 {added} 个定式，跳过 {skipped} 个（已存在）")
    
    # 清理进度文件（如果全部完成）
    if len(progress.data.get('completed_dates', [])) >= len(dates):
        if progress_file.exists():
            progress_file.unlink()
            print("🧹 已清理进度文件")


def cmd_discover(args):
    """发现值得研究的定式"""
    from pathlib import Path
    
    # 收集SGF源
    sgf_sources = []
    for path_str in args.paths:
        path = Path(path_str)
        if path.exists():
            sgf_sources.append(path)
        elif not args.quiet:
            print(f"⚠️  路径不存在: {path_str}")
    
    if not sgf_sources:
        if not args.quiet:
            print("❌ 错误: 没有有效的SGF源")
        sys.exit(1)
    
    # 解析多路参数（默认9,11,13）
    try:
        corner_sizes = [int(x.strip()) for x in args.corner_sizes.split(',')]
        corner_sizes = [x for x in corner_sizes if x in [9, 11, 13]]
        if not corner_sizes:
            corner_sizes = [9, 11, 13]
    except (ValueError, AttributeError):
        corner_sizes = [9, 11, 13]
    
    db = JosekiDB(args.db)
    
    result = db.discover(
        sgf_sources=sgf_sources,
        first_n=args.first_n,
        min_moves=args.min_moves,
        corner_sizes=corner_sizes,
        limit=args.limit,
        verbose=not args.quiet
    )
    
    # 输出结果
    if args.output == "json":
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 表格格式输出
        stats = result.get('stats', {})
        joseki_list = result.get('joseki_list', [])
        
        print("\n" + "=" * 100)
        print("「定式发现结果」按研究价值排序（罕见定式优先 → 常见定式）")
        print("=" * 100)
        print(f"统计: {stats.get('total_files', 0)}文件 → {stats.get('total_joseki', 0)}定式 → {stats.get('unique_joseki', 0)}唯一 | 罕见:{stats.get('rare_joseki', 0)} 常见:{stats.get('common_joseki', 0)}")
        print("-" * 100)
        # 添加概率列
        print(f"{'排名':<6} {'ID':<12} {'罕见?':<6} {'手数':<6} {'次数':<8} {'概率':<8} {'前缀':<8} {'着法序列':<30} {'来源'}")
        print("-" * 110)
        
        for item in joseki_list:
            joseki_id = item['joseki_id'] if item['joseki_id'] else "(未匹配)"
            is_rare = "罕见" if item['is_rare'] else ""
            moves_str = " ".join(item['moves'][:8])
            if len(item['moves']) > 8:
                moves_str += "..."
            
            prefix_len = item.get('matched_prefix_len', 0)
            prob_str = f"{item.get('probability', 0):.1%}"
            
            # 来源信息摘要
            sources_summary = ""
            if item['sources']:
                first_source = item['sources'][0]
                players = []
                if first_source.get('black_player'):
                    players.append(first_source['black_player'])
                if first_source.get('white_player'):
                    players.append(first_source['white_player'])
                if players:
                    sources_summary = " vs ".join(players)
                elif first_source.get('event'):
                    sources_summary = first_source['event'][:20]
                else:
                    sources_summary = Path(first_source.get('file', 'unknown')).name[:20]
            
            print(f"{item['rank']:<6} {joseki_id:<12} {is_rare:<6} {item['move_count']:<6} "
                  f"{item['frequency']:<8} {prob_str:<8} {prefix_len:<8} {moves_str:<30} {sources_summary}")
        
        print("=" * 100)
        print(f"总计: {len(joseki_list)} 个定式")


def main():
    parser = argparse.ArgumentParser(description="围棋定式数据库管理工具")
    parser.add_argument("--db", default=None, help="数据库路径 (默认: ~/.weiqi-joseki/database.json)")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    p_init = subparsers.add_parser("init", help="初始化数据库")
    
    p_add = subparsers.add_parser("add", help="添加定式")
    p_add.add_argument("--name", help="定式名称（可选）")
    p_add.add_argument("--category", help="分类路径（可选）")
    p_add.add_argument("--sgf")
    p_add.add_argument("--moves")
    p_add.add_argument("--tag", action="append")
    p_add.add_argument("--description")
    p_add.add_argument("--force", action="store_true")
    
    p_remove = subparsers.add_parser("remove", help="删除定式")
    p_remove.add_argument("id")
    
    p_clear = subparsers.add_parser("clear", help="清空定式库")
    p_clear.add_argument("--force", action="store_true")
    
    p_list = subparsers.add_parser("list", help="列出现式")
    p_list.add_argument("--category")
    p_list.add_argument("--limit", type=int)
    p_list.add_argument("--max-moves", type=int, default=8, help="最多显示多少手（默认8）")
    
    p_8way = subparsers.add_parser("8way", help="生成定式8向变化SGF")
    p_8way.add_argument("id", help="定式ID")
    p_8way.add_argument("--output", "-o", help="输出文件路径")
    p_8way.add_argument("--direction", help="指定方向，如 'ruld,rudl'（默认全部8个方向）")
    
    p_match = subparsers.add_parser("match", help="匹配定式")
    p_match.add_argument("--sgf")
    p_match.add_argument("--sgf-file")
    p_match.add_argument("--corner", choices=["tl", "tr", "bl", "br"])
    p_match.add_argument("--corner-sizes", type=str, default="9,11,13", help="角大小，如'9,11,13'（默认9,11,13）")
    p_match.add_argument("--first-n", type=int, default=80, help="分析前N手（默认80）")
    p_match.add_argument("--top-k", type=int, default=5)
    
    p_identify = subparsers.add_parser("identify", help="识别整盘棋")
    p_identify.add_argument("--sgf")
    p_identify.add_argument("--sgf-file")
    p_identify.add_argument("--corner-sizes", type=str, default="9,11,13", help="角大小，如'9,11,13'（默认9,11,13）")
    p_identify.add_argument("--top-k", type=int, default=1)
    p_identify.add_argument("--first-n", type=int, default=80, help="分析前N手（默认80）")
    p_identify.add_argument("--output", choices=["table", "json"], default="table")
    
    p_stats = subparsers.add_parser("stats", help="统计信息")
    
    p_extract = subparsers.add_parser("extract", help="从SGF提取四角定式")
    p_extract.add_argument("--sgf-file", help="SGF文件路径")
    p_extract.add_argument("--first-n", type=int, default=50, help="只取前N手（默认50）")
    p_extract.add_argument("--corner-sizes", type=str, default="9,11,13", help="角大小，如'9,11,13'（默认9,11,13）")
    p_extract.add_argument("--output", "-o", help="输出文件路径")
    p_extract.add_argument("--corner", choices=["tl", "tr", "bl", "br"], help="只提取指定角 (tl=左上, tr=右上, bl=左下, br=右下)")
    
    p_import = subparsers.add_parser("import", help="从SGF目录批量导入定式")
    p_import.add_argument("sgf_dir", help="SGF文件目录路径")
    p_import.add_argument("--min-count", type=int, default=10, help="最少出现次数才入库（默认10）")
    p_import.add_argument("--min-moves", type=int, default=4, help="定式至少多少手才入库（默认4）")
    p_import.add_argument("--min-rate", type=float, default=0.0, help="最小出现概率%%才入库（默认0，例如：1表示1%%，0.5表示0.5%%）")
    p_import.add_argument("--first-n", type=int, default=80, help="每谱提取前N手内的定式（默认80）")
    p_import.add_argument("--corner-sizes", type=str, default="9,11,13", help="角大小，如'9,11,13'（默认9,11,13）")
    p_import.add_argument("--dry-run", action="store_true", help="试运行，只统计不真入库")
    p_import.add_argument("--top-k", type=int, default=200000, help="返回前k个高频定式（默认200000）")
    
    # 新增 export 命令
    p_export = subparsers.add_parser("export", help="导出定式库到SGF")
    p_export.add_argument("--output", "-o", help="输出文件路径（不指定则输出到控制台）")
    p_export.add_argument("--category", help="按分类路径过滤（前缀匹配）")
    p_export.add_argument("--min-moves", type=int, help="最少手数")
    p_export.add_argument("--max-moves", type=int, help="最多手数")
    p_export.add_argument("--tag", help="按标签过滤（多个用逗号分隔）")
    p_export.add_argument("--id", help="指定定式ID（多个用逗号分隔）")
    
    # KataGo 命令
    p_katago = subparsers.add_parser("katago", help="从KataGo棋谱库下载并提取定式")
    p_katago.add_argument("--start-date", required=True, help="起始日期 (YYYY-MM-DD)")
    p_katago.add_argument("--end-date", required=True, help="结束日期 (YYYY-MM-DD)")
    p_katago.add_argument("--cache-dir", help="下载缓存目录（默认 ~/.weiqi-joseki/katago-cache）")
    p_katago.add_argument("--remove-cache", action="store_true", help="删除缓存文件（默认保留）")
    p_katago.add_argument("--workers", type=int, default=1, help="并行下载线程数（默认1）")
    p_katago.add_argument("--max-memory-mb", type=int, default=512, help="内存上限MB（默认512）")
    p_katago.add_argument("--resume", action="store_true", help="断点续传")
    p_katago.add_argument("--min-count", type=int, default=10, help="最少出现次数才入库（默认10）")
    p_katago.add_argument("--min-moves", type=int, default=4, help="定式至少多少手才入库（默认4）")
    p_katago.add_argument("--min-rate", type=float, default=0.5, help="最小出现概率%%才入库（默认0.5）")
    p_katago.add_argument("--first-n", type=int, default=80, help="每谱提取前N手内的定式（默认80）")
    p_katago.add_argument("--corner-sizes", type=str, default="9,11,13", help="角大小，如'9,11,13'（默认9,11,13）")
    p_katago.add_argument("--dry-run", action="store_true", help="试运行，只统计不真入库")
    p_katago.add_argument("--top-k", type=int, default=200000, help="返回前k个高频定式（默认200000）")
    p_katago.add_argument("--progress-file", help="进度文件路径（默认 ~/.weiqi-joseki/katago-progress.json）")
    
    # Discover 命令 - 发现有研究价值的定式
    p_discover = subparsers.add_parser("discover", help="发现值得研究的定式（罕见定式优先）")
    p_discover.add_argument("paths", nargs="+", help="SGF文件或目录路径（可多个）")
    p_discover.add_argument("--first-n", type=int, default=50, help="分析前N手的定式（默认50）")
    p_discover.add_argument("--min-moves", type=int, default=4, help="定式最少手数（默认4）")
    p_discover.add_argument("--corner-sizes", type=str, default="9,11,13", help="角大小，如'9,11,13'（默认9,11,13）")
    p_discover.add_argument("--limit", type=int, default=50, help="最多返回多少个定式（默认50）")
    p_discover.add_argument("--output", choices=["table", "json"], default="table", help="输出格式（默认table）")
    p_discover.add_argument("--quiet", action="store_true", help="安静模式，只输出JSON结果（自动设置--output=json）")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        "init": cmd_init, "add": cmd_add, "remove": cmd_remove,
        "clear": cmd_clear, "list": cmd_list, "8way": cmd_8way,
        "match": cmd_match, "identify": cmd_identify, "stats": cmd_stats,
        "extract": cmd_extract, "import": cmd_import, "export": cmd_export,
        "katago": cmd_katago, "discover": cmd_discover,
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()

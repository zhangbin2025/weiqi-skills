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
    
    # 新格式：ID, 分类, 手数, 次数, 概率, 名称
    print(f"{'ID':<10} {'分类':<18} {'手数':<5} {'次数':<7} {'概率':<8} {'名称':<20}")
    print("-" * 75)
    for j in joseki_list:
        freq = str(j['frequency']) if j.get('frequency') is not None else "-"
        prob = f"{j['probability']:.2%}" if j.get('probability') is not None else "-"
        name = j['name'] if j.get('name') else "(空)"
        print(f"{j['id']:<10} {j['category_path']:<18} {j['move_count']:<5} {freq:<7} {prob:<8} {name:<20}")


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
    print(f"  {'排名':<6} {'ID':<12} {'名称':<25} {'相似度':<10} {'方向':<8}")
    print("  " + "-" * 70)
    for i, r in enumerate(results, 1):
        marker = " ✓" if r.similarity > 0.9 else ""
        print(f"  {i:<6} {r.id:<12} {r.name:<25} {r.similarity:<10.2f} {r.matched_direction:<8}{marker}")


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
    
    if args.corner:
        # 使用提取+匹配流程（统一到右上角）
        multigogm = extract_joseki_from_sgf(sgf_data, first_n=50)
        parsed = parse_multigogm(multigogm)
        
        if args.corner not in parsed:
            print(f"⚠️  {args.corner} 角没有着法")
            return
        
        comment, moves = parsed[args.corner]
        coord_seq = [c for _, c in moves if c and c != 'tt']
        
        if not coord_seq:
            print(f"⚠️  {args.corner} 角没有有效着法")
            return
        
        results = db.match_top_right(coord_seq, top_k=args.top_k)
        print(f"\n『{args.corner.upper()}』角 ({comment}):")
        _print_match_results(results)
    else:
        results = db.identify_corners(sgf_data, top_k=args.top_k)
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
    
    results = db.identify_corners(sgf_data, top_k=args.top_k)
    
    if args.output == "json":
        import json
        output = {}
        for corner, matches in results.items():
            output[corner] = [{"id": m.id, "name": m.name, "similarity": m.similarity} for m in matches]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 70)
        print("「定式识别结果」")
        print("=" * 70)
        corner_names = {"tl": "左上", "tr": "右上", "bl": "左下", "br": "右下"}
        for corner in ["tl", "tr", "bl", "br"]:
            matches = results.get(corner, [])
            cn = corner_names.get(corner, corner)
            if matches:
                best = matches[0]
                match_str = f"{best.name} (相似度: {best.similarity:.2f})"
                if best.similarity > 0.9:
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
    
    result = extract_joseki_from_sgf(sgf_data, first_n=args.first_n, corner=args.corner)
    
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
    print(f"⏳ 正在提取定式（前{args.first_n}手）...")
    
    # 使用 joseki_db 的导入功能
    db = JosekiDB(args.db)
    
    def progress_callback(current, total):
        if current % 10 == 0 or current == total:
            print(f"\r  处理进度: {current}/{total}", end='', flush=True)
    
    added, skipped, candidates = db.import_from_sgfs(
        sgf_sources=sgf_files,
        min_count=args.min_count,
        min_moves=args.min_moves,
        min_rate=args.min_rate,
        first_n=args.first_n,
        dry_run=args.dry_run,
        progress_callback=progress_callback
    )
    
    print()  # 换行
    
    # 显示统计结果
    print(f"\n📊 统计结果（次数≥{args.min_count}，手数≥{args.min_moves}，概率≥{args.min_rate}%）：")
    print(f"   候选定式: {len(candidates)}个")
    print(f"{'排名':<6} {'频率':<8} {'定式':<40}")
    print("-" * 60)
    
    for rank, candidate in enumerate(candidates[:20], 1):
        # candidate 格式: "prefix (count次)"
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
    
    # 导入定式
    print(f"\n⏳ 开始提取定式（前{args.first_n}手）...")
    
    db = JosekiDB(args.db)
    
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
        dry_run=args.dry_run,
        progress_callback=progress_callback,
        category="/katago",
        verbose=True
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
    
    p_8way = subparsers.add_parser("8way", help="生成定式8向变化SGF")
    p_8way.add_argument("id", help="定式ID")
    p_8way.add_argument("--output", "-o", help="输出文件路径")
    p_8way.add_argument("--direction", help="指定方向，如 'ruld,rudl'（默认全部8个方向）")
    
    p_match = subparsers.add_parser("match", help="匹配定式")
    p_match.add_argument("--sgf")
    p_match.add_argument("--sgf-file")
    p_match.add_argument("--corner", choices=["tl", "tr", "bl", "br"])
    p_match.add_argument("--top-k", type=int, default=5)
    
    p_identify = subparsers.add_parser("identify", help="识别整盘棋")
    p_identify.add_argument("--sgf")
    p_identify.add_argument("--sgf-file")
    p_identify.add_argument("--top-k", type=int, default=1)
    p_identify.add_argument("--output", choices=["table", "json"], default="table")
    
    p_stats = subparsers.add_parser("stats", help="统计信息")
    
    p_extract = subparsers.add_parser("extract", help="从SGF提取四角定式")
    p_extract.add_argument("--sgf-file", help="SGF文件路径")
    p_extract.add_argument("--first-n", type=int, default=50, help="只取前N手（默认50）")
    p_extract.add_argument("--output", "-o", help="输出文件路径")
    p_extract.add_argument("--corner", choices=["tl", "tr", "bl", "br"], help="只提取指定角 (tl=左上, tr=右上, bl=左下, br=右下)")
    
    p_import = subparsers.add_parser("import", help="从SGF目录批量导入定式")
    p_import.add_argument("sgf_dir", help="SGF文件目录路径")
    p_import.add_argument("--min-count", type=int, default=10, help="最少出现次数才入库（默认10）")
    p_import.add_argument("--min-moves", type=int, default=4, help="定式至少多少手才入库（默认4）")
    p_import.add_argument("--min-rate", type=float, default=0.0, help="最小出现概率%%才入库（默认0，例如：1表示1%%，0.5表示0.5%%）")
    p_import.add_argument("--first-n", type=int, default=80, help="每谱提取前N手内的定式（默认80）")
    p_import.add_argument("--dry-run", action="store_true", help="试运行，只统计不真入库")
    
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
    p_katago.add_argument("--dry-run", action="store_true", help="试运行，只统计不真入库")
    p_katago.add_argument("--progress-file", help="进度文件路径（默认 ~/.weiqi-joseki/katago-progress.json）")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    commands = {
        "init": cmd_init, "add": cmd_add, "remove": cmd_remove,
        "clear": cmd_clear, "list": cmd_list, "8way": cmd_8way,
        "match": cmd_match, "identify": cmd_identify, "stats": cmd_stats,
        "extract": cmd_extract, "import": cmd_import, "export": cmd_export,
        "katago": cmd_katago,
    }
    
    commands[args.command](args)


if __name__ == "__main__":
    main()

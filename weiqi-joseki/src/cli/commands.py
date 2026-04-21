#!/usr/bin/env python3
"""
简化版CLI - 仅支持KataGo定式库
"""

import argparse
import sys
from pathlib import Path

from ..storage import JsonStorage, DEFAULT_DB_PATH
from ..builder import build_katago_joseki_db
from ..discover import discover_joseki
from ..extraction import extract_moves_all_corners, convert_to_multigogm
from ..matching import TrieMatcher


def cmd_init(args):
    """初始化空数据库"""
    storage = JsonStorage(args.db)
    storage.clear()
    print(f"✅ 已初始化空数据库: {storage.db_path}")


def cmd_katago(args):
    """从KataGo棋谱构建定式库"""
    if not Path(args.tar).exists():
        print(f"❌ 文件不存在: {args.tar}")
        return 1
    
    count = build_katago_joseki_db(
        tar_path=args.tar,
        db_path=args.db,
        min_freq=args.min_freq,
        top_k=args.top_k,
        max_games=args.max_games,
        first_n=args.first_n,
        distance_threshold=args.distance_threshold,
        min_moves=args.min_moves
    )
    print(f"✅ 已构建定式库: {count} 条定式")


def cmd_list(args):
    """列出定式"""
    storage = JsonStorage(args.db)
    joseki_list = storage.get_all()
    
    if not joseki_list:
        print("数据库为空")
        return
    
    # 排序
    if args.sort == "freq":
        joseki_list.sort(key=lambda x: -x.get("frequency", 0))
    elif args.sort == "length":
        joseki_list.sort(key=lambda x: -len(x.get("moves", [])))
    else:  # id
        joseki_list.sort(key=lambda x: x.get("id", ""))
    
    # 限制数量
    if args.limit:
        joseki_list = joseki_list[:args.limit]
    
    print(f"共 {len(storage.get_all())} 条定式")
    print()
    print(f"{'ID':<12} {'手数':>4} {'频率':>8} {'着法串'}")
    print("-" * 60)
    
    for j in joseki_list:
        jid = j.get("id", "-")
        moves = j.get("moves", [])
        freq = j.get("frequency", 0)
        moves_str = " ".join(moves[:8])
        if len(moves) > 8:
            moves_str += "..."
        print(f"{jid:<12} {len(moves):>4} {freq:>8} {moves_str}")


def cmd_stats(args):
    """统计信息"""
    storage = JsonStorage(args.db)
    joseki_list = storage.get_all()
    
    if not joseki_list:
        print("数据库为空")
        return
    
    total = len(joseki_list)
    frequencies = [j.get("frequency", 0) for j in joseki_list]
    lengths = [len(j.get("moves", [])) for j in joseki_list]
    
    # 频率统计
    freq_sorted = sorted(frequencies, reverse=True)
    total_freq = sum(frequencies)
    
    # 中位数
    def median(lst):
        lst_sorted = sorted(lst)
        n = len(lst_sorted)
        if n == 0:
            return 0
        if n % 2 == 1:
            return lst_sorted[n // 2]
        return (lst_sorted[n // 2 - 1] + lst_sorted[n // 2]) // 2
    
    # 找出频率最高的定式
    max_freq_joseki = max(joseki_list, key=lambda x: x.get("frequency", 0))
    
    print("=" * 50)
    print("定式库统计")
    print("=" * 50)
    print(f"总定式数:     {total}")
    print(f"总出现次数:   {total_freq}")
    print()
    print("【频率统计】")
    print(f"  最高:       {max(frequencies)}")
    print(f"  最低:       {min(frequencies)}")
    print(f"  平均:       {total_freq / total:.1f}")
    print(f"  中位数:     {median(frequencies)}")
    print(f"  Top 10%平均: {sum(freq_sorted[:total//10]) / (total//10 or 1):.1f}")
    print()
    print("【着法长度统计】")
    print(f"  最长:       {max(lengths)} 手")
    print(f"  最短:       {min(lengths)} 手")
    print(f"  平均:       {sum(lengths) / total:.1f} 手")
    print(f"  中位数:     {median(lengths)} 手")
    print()
    print("【出现最多定式】")
    print(f"  ID:         {max_freq_joseki.get('id')}")
    print(f"  频率:       {max_freq_joseki.get('frequency', 0)}")
    print(f"  着法:       {' '.join(max_freq_joseki.get('moves', []))}")


def cmd_extract(args):
    """从SGF提取四角着法"""
    if not Path(args.input).exists():
        print(f"❌ 文件不存在: {args.input}")
        return 1
    
    sgf_data = Path(args.input).read_text(encoding='utf-8')
    
    result = extract_moves_all_corners(
        sgf_data,
        first_n=args.first_n,
        distance_threshold=args.distance_threshold
    )
    
    if not result:
        print("未提取到着法")
        return
    
    print(f"提取结果（前{args.first_n}手，距离阈值{args.distance_threshold}）:")
    print()
    
    corner_names = {'tl': '左上', 'tr': '右上', 'bl': '左下', 'br': '右下'}
    
    for corner in ['tl', 'tr', 'bl', 'br']:
        if corner not in result:
            continue
        
        moves = result[corner]
        coords = [c for _, c in moves if c != 'tt']
        
        print(f"【{corner_names.get(corner, corner)}】{len(coords)}子")
        
        if args.verbose:
            for i, (color, coord) in enumerate(moves):
                coord_display = coord if coord != 'tt' else 'tt(脱先)'
                print(f"  {i+1:2d}. {color}[{coord_display}]")
        else:
            moves_str = " ".join(coords[:10])
            if len(coords) > 10:
                moves_str += f"... ({len(coords)}手)"
            print(f"  {moves_str}")
        print()
    
    # 可选保存MULTIGOGM
    if args.output:
        multigogm = convert_to_multigogm(result)
        Path(args.output).write_text(multigogm, encoding='utf-8')
        print(f"已保存MULTIGOGM: {args.output}")


def cmd_discover(args):
    """从SGF发现定式"""
    if not Path(args.input).exists():
        print(f"❌ 文件不存在: {args.input}")
        return 1
    
    storage = JsonStorage(args.db)
    joseki_list = storage.get_all()
    
    if not joseki_list:
        print("❌ 数据库为空，请先使用katago命令构建定式库")
        return 1
    
    sgf_data = Path(args.input).read_text(encoding='utf-8')
    
    results = discover_joseki(
        sgf_data,
        joseki_list,
        first_n=args.first_n,
        distance_threshold=args.distance_threshold
    )
    
    if not results:
        print("未发现定式")
        return
    
    corner_names = {'tl': '左上', 'tr': '右上', 'bl': '左下', 'br': '右下'}
    
    print(f"发现定式:")
    print()
    
    for corner in ['tl', 'tr', 'bl', 'br']:
        if corner not in results:
            continue
        
        print(f"【{corner_names.get(corner, corner)}】")
        
        for r in results[corner]:
            print(f"  - {r.joseki_id}: 匹配{r.prefix_len}/{r.total_moves}手 ({r.matched_direction})")
            if args.verbose:
                joseki = storage.get(r.joseki_id)
                if joseki:
                    moves = joseki.get("moves", [])
                    print(f"    定式: {' '.join(moves)}")
        print()


def cmd_export(args):
    """导出定式"""
    storage = JsonStorage(args.db)
    joseki_list = storage.get_all()
    
    if not joseki_list:
        print("数据库为空")
        return
    
    if args.format == "json":
        import json
        output = json.dumps(joseki_list, ensure_ascii=False, indent=2)
    elif args.format == "sgf":
        # 简单SGF格式
        lines = ["(;CA[utf-8]FF[4]AP[JosekiExport]SZ[19]GM[1]"]
        for j in joseki_list[:args.limit or 100]:
            moves = j.get("moves", [])
            if moves:
                lines.append(f"(;C[{j.get('id')} freq={j.get('frequency',0)}]")
                color = 'B'
                for m in moves:
                    lines.append(f";{color}[{m}]")
                    color = 'W' if color == 'B' else 'B'
                lines.append(")")
        lines.append(")")
        output = "".join(lines)
    else:
        print(f"❌ 不支持的格式: {args.format}")
        return 1
    
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"✅ 已导出到: {args.output}")
    else:
        print(output)


def main():
    parser = argparse.ArgumentParser(
        prog="weiqi-joseki",
        description="围棋定式数据库 - KataGo版"
    )
    parser.add_argument("--db", help="数据库路径", default=str(DEFAULT_DB_PATH))
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # init
    p_init = subparsers.add_parser("init", help="初始化空数据库")
    
    # katago
    p_katago = subparsers.add_parser("katago", help="从KataGo棋谱构建定式库")
    p_katago.add_argument("tar", help="tar文件路径")
    p_katago.add_argument("--min-freq", type=int, default=5, help="最小频率")
    p_katago.add_argument("--top-k", type=int, default=10000, help="入库数量上限")
    p_katago.add_argument("--max-games", type=int, default=None, help="最大处理棋谱数")
    p_katago.add_argument("--first-n", type=int, default=80, help="提取前N手")
    p_katago.add_argument("--distance-threshold", type=int, default=4, help="连通块距离阈值")
    p_katago.add_argument("--min-moves", type=int, default=4, help="最少手数")
    
    # list
    p_list = subparsers.add_parser("list", help="列出定式")
    p_list.add_argument("--limit", type=int, help="限制数量")
    p_list.add_argument("--sort", choices=["id", "freq", "length"], default="id", help="排序方式")
    
    # stats
    p_stats = subparsers.add_parser("stats", help="统计信息")
    
    # extract
    p_extract = subparsers.add_parser("extract", help="从SGF提取四角着法")
    p_extract.add_argument("input", help="SGF文件路径")
    p_extract.add_argument("--first-n", type=int, default=80, help="提取前N手")
    p_extract.add_argument("--distance-threshold", type=int, default=4, help="连通块距离阈值")
    p_extract.add_argument("--output", "-o", help="输出MULTIGOGM文件")
    p_extract.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    # discover
    p_discover = subparsers.add_parser("discover", help="从SGF发现定式")
    p_discover.add_argument("input", help="SGF文件路径")
    p_discover.add_argument("--first-n", type=int, default=80, help="提取前N手")
    p_discover.add_argument("--distance-threshold", type=int, default=4, help="连通块距离阈值")
    p_discover.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    # export
    p_export = subparsers.add_parser("export", help="导出定式")
    p_export.add_argument("--format", choices=["json", "sgf"], default="json", help="导出格式")
    p_export.add_argument("--output", "-o", help="输出文件")
    p_export.add_argument("--limit", type=int, help="限制导出数量")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        "init": cmd_init,
        "katago": cmd_katago,
        "list": cmd_list,
        "stats": cmd_stats,
        "extract": cmd_extract,
        "discover": cmd_discover,
        "export": cmd_export,
    }
    
    func = commands.get(args.command)
    if func:
        return func(args) or 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

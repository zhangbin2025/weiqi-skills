#!/usr/bin/env python3
"""
围棋选手信息统一查询脚本
同时查询手谈等级分和易查分业余段位

使用方法:
    python3 query.py <姓名>
    python3 query.py --json <姓名>
    python3 query.py --batch 姓名1 姓名2 姓名3
    
示例:
    python3 query.py 张三
    python3 query.py --json 张三
    python3 query.py --batch 李四 王五 赵六
"""

import sys
import subprocess
import os
import json
import argparse
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def query_shoutan(name, json_output=False):
    """调用手谈查询脚本"""
    script_path = os.path.join(SCRIPTS_DIR, "query_shoutan.py")
    try:
        cmd = ["python3", script_path, name]
        if json_output:
            cmd.append("--json")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if json_output:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"found": False, "error": result.stderr or result.stdout}
        return result.stdout
    except Exception as e:
        if json_output:
            return {"found": False, "error": str(e)}
        return f"❌ 手谈查询失败: {e}"


def query_yichafen(name, json_output=False):
    """调用易查分查询脚本"""
    script_path = os.path.join(SCRIPTS_DIR, "query_yichafen.py")
    try:
        cmd = ["python3", script_path, name]
        if json_output:
            cmd.append("--json")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        if json_output:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"found": False, "error": result.stderr or result.stdout}
        return result.stdout
    except Exception as e:
        if json_output:
            return {"found": False, "error": str(e)}
        return f"❌ 易查分查询失败: {e}"


def query_single(name, json_output=False):
    """查询单个选手（双平台）"""
    if json_output:
        # JSON 模式
        result = {
            "success": True,
            "query_time": datetime.now().isoformat(),
            "name": name,
            "shoutan": query_shoutan(name, json_output=True),
            "yichafen": query_yichafen(name, json_output=True)
        }
        return result
    
    # 文本模式
    print(f"\n{'='*60}")
    print(f"🔍 正在查询: {name}")
    print(f"{'='*60}\n")
    
    # 查询手谈等级分
    print("【1/2】手谈等级分查询")
    print("-" * 40)
    shoutan_result = query_shoutan(name)
    print(shoutan_result)
    
    # 查询易查分段位
    print("\n【2/2】易查分业余段位查询")
    print("-" * 40)
    yichafen_result = query_yichafen(name)
    print(yichafen_result)
    
    print(f"\n{'='*60}")
    print(f"✅ {name} 查询完成")
    print(f"{'='*60}\n")


def query_batch(names, json_output=False):
    """批量查询多个选手"""
    if json_output:
        results = []
        for name in names:
            results.append(query_single(name, json_output=True))
        return results
    
    print(f"\n{'='*60}")
    print(f"🚀 批量查询 {len(names)} 位棋手")
    print(f"名单: {', '.join(names)}")
    print(f"{'='*60}\n")
    
    for i, name in enumerate(names, 1):
        print(f"\n[{i}/{len(names)}] {'='*50}")
        query_single(name)


def main():
    parser = argparse.ArgumentParser(description='围棋选手信息统一查询')
    parser.add_argument('names', nargs='+', help='选手姓名')
    parser.add_argument('--batch', action='store_true', help='批量查询模式')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    args = parser.parse_args()
    
    if args.batch:
        # 批量模式
        if args.json:
            results = query_batch(args.names, json_output=True)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            query_batch(args.names)
    else:
        # 单个查询
        if args.json:
            result = query_single(args.names[0], json_output=True)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            query_single(args.names[0])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
weiqi-joseki 集成测试脚本
测试完整流程：KataGo导入 + 定式发现
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki')

from src.builder import build_katago_joseki_db
from src.discover import discover_joseki
from src.storage import JsonStorage
from src.extraction import extract_moves_all_corners


def test_katago_import():
    """测试KataGo定式导入"""
    print("=" * 60)
    print("测试1: KataGo定式导入")
    print("=" * 60)
    
    # 使用cache目录的tar文件（取前两天的）
    cache_dir = Path("/root/.weiqi-joseki/katago-cache")
    tar_files = sorted(cache_dir.glob("*.tar.bz2"))[:2]
    
    if not tar_files:
        print("❌ 未找到tar文件")
        return False
    
    print(f"找到 {len(tar_files)} 个tar文件:")
    for f in tar_files:
        print(f"  - {f.name}")
    
    # 创建临时数据库
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_joseki.json"
        
        total_count = 0
        for tar_file in tar_files:
            print(f"\n处理: {tar_file.name}")
            try:
                count = build_katago_joseki_db(
                    tar_path=str(tar_file),
                    db_path=str(db_path),
                    min_freq=3,  # 降低阈值以便测试
                    top_k=1000,
                    first_n=80,
                    distance_threshold=4,
                    min_moves=4,
                    max_moves=50
                )
                total_count += count
                print(f"✅ 导入 {count} 条定式")
            except Exception as e:
                print(f"⚠️  处理失败: {e}")
                continue
        
        # 验证数据库
        storage = JsonStorage(str(db_path))
        joseki_list = storage.get_all()
        print(f"\n📊 数据库统计:")
        print(f"   总定式数: {len(joseki_list)}")
        
        if joseki_list:
            # 显示频率最高的几个定式
            top_joseki = sorted(joseki_list, key=lambda x: -x.get('frequency', 0))[:5]
            print(f"\n   Top 5 高频定式:")
            for j in top_joseki:
                moves = ' '.join(j.get('moves', [])[:6])
                if len(j.get('moves', [])) > 6:
                    moves += '...'
                print(f"   - {j.get('id')}: freq={j.get('frequency')}, {moves}")
            
            return True
        else:
            print("❌ 数据库为空")
            return False


def test_discover():
    """测试定式发现"""
    print("\n" + "=" * 60)
    print("测试2: 定式发现")
    print("=" * 60)
    
    # 使用真实棋谱
    sgf_dir = Path("/tmp/foxwq_downloads/2026-04-18")
    sgf_files = list(sgf_dir.glob("*.sgf"))[:3]
    
    if not sgf_files:
        print("❌ 未找到SGF文件")
        return False
    
    print(f"找到 {len(sgf_files)} 个SGF文件")
    
    # 先构建一个测试用的定式库
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_joseki.json"
        
        # 使用一天的KataGo数据构建定式库
        cache_dir = Path("/root/.weiqi-joseki/katago-cache")
        tar_files = sorted(cache_dir.glob("*.tar.bz2"))[:1]
        
        if tar_files:
            print(f"\n构建测试定式库...")
            build_katago_joseki_db(
                tar_path=str(tar_files[0]),
                db_path=str(db_path),
                min_freq=5,
                top_k=500,
                first_n=80,
                distance_threshold=4,
                min_moves=4,
                max_moves=50
            )
        
        storage = JsonStorage(str(db_path))
        joseki_list = storage.get_all()
        print(f"定式库: {len(joseki_list)} 条定式")
        
        if not joseki_list:
            print("❌ 定式库为空，无法测试发现")
            return False
        
        # 测试发现
        print(f"\n测试定式发现:")
        for i, sgf_file in enumerate(sgf_files, 1):
            print(f"\n  [{i}/{len(sgf_files)}] {sgf_file.name[:40]}...")
            
            try:
                sgf_data = sgf_file.read_text(encoding='utf-8')
                
                # 先提取
                extracted = extract_moves_all_corners(sgf_data, first_n=80, distance_threshold=4)
                print(f"      提取到 {len(extracted)} 个角")
                
                # 再发现
                results = discover_joseki(sgf_data, joseki_list, first_n=80, distance_threshold=4)
                
                total_matches = sum(len(r) for r in results.values())
                print(f"      发现 {total_matches} 个定式匹配")
                
                # 显示详细信息
                for corner, matches in results.items():
                    if matches:
                        top = matches[0]
                        print(f"      - {corner}: {top.joseki_id} "
                              f"(匹配{top.prefix_len}/{top.total_moves}手, "
                              f"来源:{top.source_corner})")
                
            except Exception as e:
                print(f"      ⚠️  处理失败: {e}")
                continue
        
        return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("weiqi-joseki 重构版集成测试")
    print("=" * 60)
    
    success = True
    
    # 测试1: KataGo导入
    if not test_katago_import():
        success = False
    
    # 测试2: 定式发现
    if not test_discover():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有集成测试通过")
    else:
        print("⚠️  部分测试未通过")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

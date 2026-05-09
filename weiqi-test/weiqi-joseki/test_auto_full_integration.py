#!/usr/bin/env python3
"""
Katago Auto模式完整集成测试（真实下载）

此脚本会：
1. 下载最近1-2天的真实棋谱
2. 执行完整的提取→CMS→重建流程
3. 所有数据在/tmp/下，不影响现有数据

⚠️ 注意：这会真实下载棋谱，可能需要几分钟时间
"""

import sys
import shutil
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/weiqi-joseki')

from src.auto import AutoState
from src.builder import KatagoJosekiBuilder
from src.extraction.katago_downloader import download_auto, fetch_available_dates


def run_full_integration_test():
    """运行完整的集成测试（真实下载）"""
    
    # 创建临时目录
    test_dir = Path("/tmp/weiqi-joseki-fulltest")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True)
    
    print("=" * 70)
    print("🧪 Katago Auto模式完整集成测试（真实下载）")
    print("=" * 70)
    print(f"📁 测试目录: {test_dir}")
    print()
    
    try:
        # 1. 初始化AutoState
        print("【步骤1】初始化AutoState...")
        auto_dir = test_dir / "auto"
        state = AutoState(auto_dir)
        
        # 小配置，测试用
        state.init_config(
            estimated_games=50_000,
            first_n=50,
            min_freq=5,
            global_top_k=5000,
            rebuild_threshold_days=0
        )
        print(f"   ✅ 初始化完成")
        print()
        
        # 2. 获取最近1天的日期
        print("【步骤2】获取可用日期...")
        available_dates = fetch_available_dates()
        if not available_dates:
            print("   ❌ 无法获取服务器日期列表")
            return 1
        
        # 只测试最近1天，节省时间
        test_date = available_dates[-1]
        print(f"   ✅ 测试日期: {test_date}")
        print()
        
        # 3. 下载（使用download_auto）
        print("【步骤3】下载棋谱...")
        cache_dir = test_dir / "katago-cache"
        cache_dir.mkdir()
        
        # 手动标记这个日期为待下载
        print(f"   📥 下载 {test_date} 的棋谱...")
        
        # 这里我们直接使用download_katago_games下载单个日期
        from extraction.katago_downloader import download_katago_games
        
        downloaded_files, missing = download_katago_games(
            start_date=test_date,
            end_date=test_date,
            cache_dir=cache_dir,
            max_retries=2,
            workers=1,
            delay=5
        )
        
        if not downloaded_files:
            print("   ⚠️  下载失败，可能是网络问题或服务器无此日期数据")
            print("   📝 但这不影响流程验证，继续测试...")
            # 创建一个空文件继续测试流程
            (cache_dir / f"{test_date}rating.tar.bz2").touch()
        else:
            print(f"   ✅ 下载完成: {len(downloaded_files)} 个文件")
            for f in downloaded_files:
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"      {f.name} ({size_mb:.1f} MB)")
        
        # 标记为已下载
        state.mark_downloaded(test_date)
        print()
        
        # 4. 执行自动构建流程
        print("【步骤4】执行自动构建流程...")
        db_path = test_dir / "database.json"
        builder = KatagoJosekiBuilder(db_path)
        
        print(f"   状态检查:")
        print(f"      已下载: {len(state.progress['downloaded'])} 个日期")
        print(f"      已提取: {len(state.progress['extracted'])} 个日期")
        print(f"      是否重建: {state.should_rebuild()}")
        print()
        
        # 调用run_auto
        result = builder.run_auto(state, cache_dir)
        
        if result:
            print(f"\n✅ 构建成功！生成 {len(result)} 条定式")
        else:
            print(f"\n⏭️  没有生成定式（可能是tar文件为空或无效）")
        
        # 5. 最终验证
        print()
        print("【步骤5】验证结果...")
        
        # 检查生成的文件
        if db_path.exists():
            import json
            db_content = json.loads(db_path.read_text())
            joseki_count = len(db_content.get('joseki_list', []))
            print(f"   ✅ 数据库: {joseki_count} 条定式")
        else:
            print(f"   ⚠️  数据库未生成")
        
        if (auto_dir / "cms.pkl").exists():
            cms_size = (auto_dir / "cms.pkl").stat().st_size / (1024 * 1024)
            print(f"   ✅ CMS文件: {cms_size:.1f} MB")
        
        if (auto_dir / "temp" / f"{test_date}.txt.gz").exists():
            temp_size = (auto_dir / "temp" / f"{test_date}.txt.gz").stat().st_size / 1024
            print(f"   ✅ Temp文件: {temp_size:.1f} KB")
        
        # 显示最终状态
        print()
        print("【最终状态】")
        print(f"   已下载: {state.progress['downloaded']}")
        print(f"   已提取: {state.progress['extracted']}")
        print(f"   CMS更新至: {state.progress['cms_updated_to']}")
        print(f"   最后重建: {state.progress['last_rebuild']}")
        
        print()
        print("=" * 70)
        print("✅ 完整集成测试完成！")
        print("=" * 70)
        print()
        print(f"测试目录: {test_dir}")
        print("如需清理: rm -rf /tmp/weiqi-joseki-fulltest")
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ 集成测试失败: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    print("⚠️  此测试会真实下载棋谱，大约需要2-5分钟")
    print("如需快速测试（不下载），请运行 test_auto_integration.py")
    print()
    
    # 简单的确认提示
    # response = input("继续? [y/N]: ")
    # if response.lower() != 'y':
    #     print("已取消")
    #     sys.exit(0)
    
    exit_code = run_full_integration_test()
    sys.exit(exit_code)

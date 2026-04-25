#!/usr/bin/env python3
"""
Auto模式状态管理模块

管理 ~/.weiqi-joseki/auto/state.json
包括配置、进度、统计信息
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union


DEFAULT_AUTO_DIR = Path.home() / ".weiqi-joseki" / "auto"
DEFAULT_STATE_FILE = DEFAULT_AUTO_DIR / "state.json"


def get_adaptive_cms_config(estimated_games: int) -> Dict[str, int]:
    """根据预估棋谱数返回自适应CMS配置
    
    Args:
        estimated_games: 预估棋谱数量
        
    Returns:
        dict: {'width': int, 'depth': int}
    """
    if estimated_games < 100_000:
        return {"width": 1_048_576, "depth": 4}   # 16MB
    elif estimated_games < 1_000_000:
        return {"width": 4_194_304, "depth": 4}   # 64MB
    else:
        return {"width": 16_777_216, "depth": 4}  # 256MB


class AutoState:
    """自动模式状态管理器
    
    管理配置和进度，所有数据持久化到 state.json
    """
    
    def __init__(self, auto_dir: Optional[Union[str, Path]] = None):
        """
        Args:
            auto_dir: auto目录路径，默认 ~/.weiqi-joseki/auto
        """
        self.auto_dir = Path(auto_dir) if auto_dir else DEFAULT_AUTO_DIR
        self.state_file = self.auto_dir / "state.json"
        self._data = self._load()
    
    def _load(self) -> dict:
        """加载状态文件，不存在则返回空结构"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._empty_state()
    
    def _save(self):
        """保存状态到文件"""
        self.auto_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
    
    def _empty_state(self) -> dict:
        """返回空状态结构"""
        return {
            "mode": "auto",
            "config": {},
            "progress": {
                "downloaded": [],
                "extracted": [],
                "cms_updated_to": None,
                "last_rebuild": None
            },
            "stats": {
                "total_sgf": 0,
                "total_sequences": 0,
                "current_joseki": 0
            }
        }
    
    def init_config(self, 
                    estimated_games: int = 100_000,
                    first_n: int = 80,
                    distance_threshold: int = 4,
                    min_freq: int = 5,
                    global_top_k: int = 10_000,
                    rebuild_threshold_days: int = 7) -> dict:
        """初始化配置
        
        Args:
            estimated_games: 预估棋谱数，用于自适应CMS配置
            first_n: 提取前N手
            distance_threshold: 连通块距离阈值
            min_freq: 最小频率
            global_top_k: 全局Top-K定式数
            rebuild_threshold_days: 重建触发阈值（天）
            
        Returns:
            配置字典
        """
        cms_config = get_adaptive_cms_config(estimated_games)
        
        self._data["config"] = {
            "cms_width": cms_config["width"],
            "cms_depth": cms_config["depth"],
            "first_n": first_n,
            "distance_threshold": distance_threshold,
            "min_freq": min_freq,
            "global_top_k": global_top_k,
            "rebuild_threshold_days": rebuild_threshold_days
        }
        
        self._save()
        return self._data["config"]
    
    @property
    def config(self) -> dict:
        """获取当前配置"""
        return self._data.get("config", {})
    
    @property
    def progress(self) -> dict:
        """获取当前进度"""
        return self._data.get("progress", {})
    
    @property
    def stats(self) -> dict:
        """获取统计数据"""
        return self._data.get("stats", {})
    
    def mark_downloaded(self, date: str):
        """标记日期已下载"""
        if date not in self._data["progress"]["downloaded"]:
            self._data["progress"]["downloaded"].append(date)
            self._data["progress"]["downloaded"].sort()
            self._save()
    
    def mark_extracted(self, date: str):
        """标记日期已提取"""
        if date not in self._data["progress"]["extracted"]:
            self._data["progress"]["extracted"].append(date)
            self._data["progress"]["extracted"].sort()
            self._save()
    
    def mark_cms_updated(self, date: str):
        """标记CMS已更新到该日期"""
        self._data["progress"]["cms_updated_to"] = date
        self._save()
    
    def mark_rebuild(self, joseki_count: int = None, sequence_count: int = None):
        """标记已完成重建
        
        Args:
            joseki_count: 当前定式数量，更新到stats
            sequence_count: 序列总数，更新到stats
        """
        today = datetime.now().strftime("%Y-%m-%d")
        self._data["progress"]["last_rebuild"] = today
        
        if joseki_count is not None:
            self._data["stats"]["current_joseki"] = joseki_count
        if sequence_count is not None:
            self._data["stats"]["total_sequences"] = sequence_count
            
        self._save()
    
    def update_stats(self, sgf_delta: int = 0, seq_delta: int = 0):
        """更新统计数字
        
        Args:
            sgf_delta: SGF数量变化（可为负）
            seq_delta: 序列数量变化（可为负）
        """
        self._data["stats"]["total_sgf"] += sgf_delta
        self._data["stats"]["total_sequences"] += seq_delta
        self._save()
    
    def get_pending_downloads(self, available_dates: List[str]) -> List[str]:
        """获取待下载的日期列表
        
        Args:
            available_dates: 服务器上所有可用日期（已排序）
            
        Returns:
            未下载的日期列表
        """
        downloaded = set(self._data["progress"]["downloaded"])
        return [d for d in available_dates if d not in downloaded]
    
    def get_pending_extractions(self) -> List[str]:
        """获取待提取的日期列表"""
        downloaded = set(self._data["progress"]["downloaded"])
        extracted = set(self._data["progress"]["extracted"])
        pending = downloaded - extracted
        return sorted(list(pending))
    
    def get_pending_cms_dates(self) -> List[str]:
        """获取待CMS统计的日期列表"""
        extracted = set(self._data["progress"]["extracted"])
        cms_updated_to = self._data["progress"]["cms_updated_to"]
        
        if cms_updated_to is None:
            return sorted(list(extracted))
        
        # 返回晚于cms_updated_to的提取日期
        return [d for d in extracted if d > cms_updated_to]
    
    def should_rebuild(self) -> bool:
        """判断是否需要执行步骤4重建
        
        Returns:
            True: 需要重建
            False: 不需要
        """
        last_rebuild = self._data["progress"]["last_rebuild"]
        cms_updated_to = self._data["progress"]["cms_updated_to"]
        
        # 从未重建过
        if last_rebuild is None:
            return True
        
        # CMS没有新数据
        if cms_updated_to is None or cms_updated_to <= last_rebuild:
            return False
        
        # 检查是否达到重建阈值
        threshold = self._data["config"].get("rebuild_threshold_days", 7)
        last_date = datetime.strptime(last_rebuild, "%Y-%m-%d")
        cms_date = datetime.strptime(cms_updated_to, "%Y-%m-%d")
        
        days_since = (cms_date - last_date).days
        return days_since >= threshold
    
    def is_initialized(self) -> bool:
        """检查是否已初始化（有配置）"""
        return bool(self._data.get("config"))
    
    def reset(self):
        """重置所有状态（删除state.json的效果）"""
        self._data = self._empty_state()
        if self.state_file.exists():
            self.state_file.unlink()
    
    def __repr__(self):
        return f"AutoState(dir={self.auto_dir}, initialized={self.is_initialized()})"

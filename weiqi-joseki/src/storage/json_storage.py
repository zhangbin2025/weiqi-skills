#!/usr/bin/env python3
"""
JSON文件存储实现
管理定式库的JSON持久化存储
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime


DEFAULT_DB_DIR = Path.home() / ".weiqi-joseki"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "database.json"


class JsonStorage:
    """JSON文件存储"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._ensure_dir()
        self._data = self._load()
    
    def _ensure_dir(self):
        """确保目录存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load(self) -> dict:
        """加载数据库（兼容旧格式列表和新格式字典）"""
        if self.db_path.exists():
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容旧格式: 直接是列表
                if isinstance(data, list):
                    return {"version": "1.0.0", "joseki_list": data}
                # 新格式: 字典
                return data
        return {"version": "1.0.0", "joseki_list": []}
    
    def _save(self):
        """保存数据库"""
        self._data["last_updated"] = datetime.now().isoformat()
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
    
    @property
    def joseki_list(self) -> List[dict]:
        """获取定式列表"""
        return self._data.get("joseki_list", [])
    
    @joseki_list.setter
    def joseki_list(self, value: List[dict]):
        """设置定式列表并保存"""
        self._data["joseki_list"] = value
        self._save()
    
    def get(self, joseki_id: str) -> Optional[dict]:
        """根据ID获取定式"""
        for j in self.joseki_list:
            if j.get("id") == joseki_id:
                return j
        return None
    
    def add(self, joseki: dict) -> str:
        """添加定式"""
        joseki_id = joseki.get("id")
        if not joseki_id:
            joseki_id = f"joseki_{len(self.joseki_list) + 1:03d}"
            joseki["id"] = joseki_id
        
        self._data["joseki_list"].append(joseki)
        self._save()
        return joseki_id
    
    def remove(self, joseki_id: str) -> bool:
        """删除定式"""
        for i, j in enumerate(self.joseki_list):
            if j.get("id") == joseki_id:
                del self._data["joseki_list"][i]
                self._save()
                return True
        return False
    
    def update(self, joseki_id: str, updates: dict) -> bool:
        """更新定式"""
        for j in self.joseki_list:
            if j.get("id") == joseki_id:
                j.update(updates)
                self._save()
                return True
        return False
    
    def clear(self):
        """清空数据库"""
        self._data["joseki_list"] = []
        self._save()
    
    def reload(self):
        """重新加载数据库"""
        self._data = self._load()

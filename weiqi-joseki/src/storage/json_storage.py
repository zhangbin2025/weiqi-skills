#!/usr/bin/env python3
"""
简化版JSON存储 - 仅支持KataGo定式
使用 gzip 压缩存储
"""

import json
import gzip
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


DEFAULT_DB_PATH = Path.home() / ".weiqi-joseki" / "database.json.gz"


class JsonStorage:
    """简化版JSON存储 - 仅KataGo定式，gzip压缩"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._ensure_dir()
        self._data = self._load()
    
    def _ensure_dir(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load(self) -> dict:
        # 支持旧版 .json 文件自动迁移
        old_path = self.db_path.with_suffix('') if self.db_path.suffix == '.gz' else None
        
        if self.db_path.exists():
            with gzip.open(self.db_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"version": "2.0.0", "joseki_list": data}
                return data
        elif old_path and old_path.exists():
            # 迁移旧文件
            with open(old_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                data = {"version": "2.0.0", "joseki_list": data}
            # 保存为新格式
            self._data = data
            self._save()
            # 删除旧文件
            old_path.unlink()
            return data
        return {"version": "2.0.0", "joseki_list": []}
    
    def _save(self):
        self._data["last_updated"] = datetime.now().isoformat()
        with gzip.open(self.db_path, 'wt', encoding='utf-8', compresslevel=3) as f:
            json.dump(self._data, f, ensure_ascii=False, separators=(',', ':'))
    
    @property
    def joseki_list(self) -> List[dict]:
        return self._data.get("joseki_list", [])
    
    def get(self, joseki_id: str) -> Optional[dict]:
        for j in self.joseki_list:
            if j.get("id") == joseki_id:
                return j
        return None
    
    def get_all(self) -> List[dict]:
        return self.joseki_list
    
    def add(self, joseki: dict) -> str:
        joseki_id = joseki.get("id")
        if not joseki_id:
            joseki_id = f"kj_{len(self.joseki_list) + 1:05d}"
            joseki["id"] = joseki_id
        self._data["joseki_list"].append(joseki)
        self._save()
        return joseki_id
    
    def clear(self):
        self._data["joseki_list"] = []
        self._save()
    
    def reload(self):
        self._data = self._load()

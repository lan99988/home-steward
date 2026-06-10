"""设备状态缓存——MQTT 断开时的降级保护"""

import json
import logging
import time
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CachedDeviceState:
    device_id: str
    status: str  # online, offline, unknown
    properties: Dict[str, Any]
    last_seen: datetime
    cached_at: datetime


class DeviceStateCache:
    """设备状态缓存：内存 + SQLite 双重保障"""

    def __init__(self, db_path: str = "data/device_cache.db"):
        self.memory_cache: Dict[str, CachedDeviceState] = {}
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 缓存表"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_cache (
                device_id TEXT PRIMARY KEY,
                status TEXT,
                properties TEXT,
                last_seen REAL,
                cached_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def update(self, device_id: str, properties: Dict, status: str = "online"):
        """更新设备缓存"""
        now = datetime.now()
        state = CachedDeviceState(
            device_id=device_id,
            status=status,
            properties=properties,
            last_seen=now,
            cached_at=now,
        )
        self.memory_cache[device_id] = state
        self._persist(device_id, state)

    def get(self, device_id: str) -> Optional[CachedDeviceState]:
        """读取缓存（MQTT 断开时只能读到这个）"""
        if device_id in self.memory_cache:
            return self.memory_cache[device_id]
        return self._load(device_id)

    def get_staleness(self, device_id: str) -> timedelta:
        """返回缓存数据的陈旧程度"""
        state = self.get(device_id)
        if not state:
            return timedelta.max
        return datetime.now() - state.last_seen

    def is_stale(self, device_id: str, max_age_seconds: int = 30) -> bool:
        """判断缓存是否过时"""
        return self.get_staleness(device_id).total_seconds() > max_age_seconds

    def all_devices(self) -> Dict[str, CachedDeviceState]:
        """返回所有缓存设备"""
        return dict(self.memory_cache)

    def _persist(self, device_id: str, state: CachedDeviceState):
        """持久化到 SQLite"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                "INSERT OR REPLACE INTO device_cache (device_id, status, properties, last_seen, cached_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    device_id,
                    state.status,
                    json.dumps(state.properties),
                    state.last_seen.timestamp(),
                    state.cached_at.timestamp(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"缓存持久化失败: {e}")

    def _load(self, device_id: str) -> Optional[CachedDeviceState]:
        """从 SQLite 加载"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute(
                "SELECT device_id, status, properties, last_seen, cached_at FROM device_cache WHERE device_id = ?",
                (device_id,),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return CachedDeviceState(
                    device_id=row[0],
                    status=row[1],
                    properties=json.loads(row[2]),
                    last_seen=datetime.fromtimestamp(row[3]),
                    cached_at=datetime.fromtimestamp(row[4]),
                )
        except Exception as e:
            logger.error(f"缓存加载失败: {e}")
        return None

"""中期记忆——按周汇总的行为模式"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class MediumTermMemory:
    """中期记忆：按周汇总的行为模式

    从短期记忆中提取规律性操作（固定时间 + 固定设备 + 固定操作），
    形成可观察的行为模式。
    """

    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.patterns: Dict[str, Any] = self._load()

    def _load(self) -> Dict:
        path = self.storage_dir / "medium_term.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                pass
        return {
            "routines": [],
            "insights": [],
            "last_compressed": time.time(),
        }

    def save(self):
        path = self.storage_dir / "medium_term.json"
        path.write_text(
            json.dumps(self.patterns, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_event(self, event: Dict):
        """添加事件并检测模式"""
        if "timestamp" not in event or "intent" not in event:
            return

        hour = time.localtime(event["timestamp"]).tm_hour
        device = event.get("device", "unknown")
        intent = event.get("intent", "unknown")
        routines = self.patterns.get("routines", [])

        # 找同小时 + 同设备 + 同意图的已有记录
        matching = [
            r for r in routines
            if r.get("hour") == hour
            and r.get("device") == device
            and r.get("intent") == intent
        ]

        if matching:
            matching[0]["count"] += 1
            matching[0]["last_seen"] = time.time()
        else:
            routines.append({
                "hour": hour,
                "device": device,
                "intent": intent,
                "count": 1,
                "first_seen": time.time(),
                "last_seen": time.time(),
            })

        # 保留高频模式（最多 100 条）
        self.patterns["routines"] = sorted(
            routines, key=lambda x: x["count"], reverse=True
        )[:100]
        self.save()

    def get_patterns(self, min_count: int = 3) -> List[Dict]:
        """获取出现次数超过阈值的行为模式"""
        return [
            r for r in self.patterns.get("routines", [])
            if r["count"] >= min_count
        ]

    def get_daily_routine(self, hour: int) -> List[Dict]:
        """获取某小时的常见操作"""
        return [
            r for r in self.patterns.get("routines", [])
            if r.get("hour") == hour
        ]

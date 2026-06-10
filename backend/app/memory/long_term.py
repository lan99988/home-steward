"""长期记忆——用户画像 + 高度压缩的习惯"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LongTermMemory:
    """长期记忆：用户画像 + 稳定习惯

    从中期记忆的高频模式中学习为长期习惯。
    """

    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.profile: Dict[str, Any] = self._load()

    def _load(self) -> Dict:
        path = self.storage_dir / "long_term.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                pass
        return {
            "user_profile": {},
            "habits": [],
            "preferences": {},
        }

    def save(self):
        path = self.storage_dir / "long_term.json"
        path.write_text(
            json.dumps(self.profile, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def learn_habit(self, routine: Dict[str, Any]):
        """从中期模式的规律中学习为长期习惯"""
        habits = self.profile.get("habits", [])
        habit_key = (
            f"{routine.get('hour')}:"
            f"{routine.get('device')}:"
            f"{routine.get('intent')}"
        )

        existing = [h for h in habits if h.get("key") == habit_key]
        if existing:
            existing[0]["confidence"] = min(routine["count"] / 30, 0.99)
            existing[0]["updated_at"] = time.time()
        else:
            habits.append({
                "key": habit_key,
                "summary": (
                    f"每天{routine.get('hour')}点左右 "
                    f"{routine.get('intent')} {routine.get('device')}"
                ),
                "hour": routine.get("hour"),
                "device": routine.get("device"),
                "intent": routine.get("intent"),
                "confidence": min(routine["count"] / 30, 0.95),
                "created_at": time.time(),
                "updated_at": time.time(),
            })

        # 保留高信度习惯
        self.profile["habits"] = sorted(
            habits, key=lambda x: x["confidence"], reverse=True
        )[:50]
        self.save()

    def get_habits(self, min_confidence: float = 0.5) -> list:
        """获取超过置信度阈值的学习习惯"""
        return [
            h for h in self.profile.get("habits", [])
            if h["confidence"] >= min_confidence
        ]

    def get_preferences(self) -> dict:
        return self.profile.get("preferences", {})

    def update_preferences(self, domain: str, preferences: dict):
        self.profile.setdefault("preferences", {})[domain] = preferences
        self.save()

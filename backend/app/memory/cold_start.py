"""冷启动加速器——种子记忆 + 快速收敛"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


# 种子记忆库——通用家庭模板
SEED_MEMORIES = [
    {
        "template": "typical_wakeup",
        "summary": "多数用户在 07:00-08:00 起床，需要逐渐亮灯",
        "confidence": 0.3,
        "tags": ["routine", "morning"],
        "actions": [{"domain": "light", "operation": "gradual_brighten"}],
    },
    {
        "template": "typical_sleep",
        "summary": "多数用户在 22:00-23:30 入睡，需要关灯调温",
        "confidence": 0.3,
        "tags": ["routine", "night"],
        "actions": [
            {"domain": "light", "operation": "turn_off_all"},
            {"domain": "climate", "operation": "set_night_mode"},
        ],
    },
    {
        "template": "typical_leave",
        "summary": "多数用户离家时关闭所有设备",
        "confidence": 0.3,
        "tags": ["routine", "away"],
        "actions": [{"domain": "all", "operation": "turn_off_all"}],
    },
    {
        "template": "typical_cozy",
        "summary": "多数用户在晚上喜欢温馨的暖色调灯光",
        "confidence": 0.25,
        "tags": ["scene", "evening"],
        "actions": [{"domain": "light", "operation": "set_scene", "scene": "cozy"}],
    },
]


class ColdStartAccelerator:
    """冷启动加速器

    系统初期记忆库为空时，用种子记忆提供通用推荐。
    快速收敛：观察到 3 次重复即可形成临时习惯。
    """

    def __init__(self):
        self.min_confirmations = 3
        self.observation_buffer: List[Dict] = []

    def get_seed_memories(self) -> List[Dict]:
        """获取种子记忆"""
        return SEED_MEMORIES

    def observe(self, event: Dict) -> bool:
        """观察事件，检测重复模式

        返回 True 表示检测到可确认的模式。
        """
        self.observation_buffer.append(event)

        pattern = self._detect_pattern(event)
        if pattern and pattern["count"] >= self.min_confirmations:
            logger.info(f"🔍 冷启动加速器: 检测到模式 "
                        f"'{pattern['summary']}' ({pattern['count']}次)")
            self._clear_pattern(pattern)
            return True

        return False

    def should_activate(self, event_count: int) -> bool:
        """事件少于 10 条时使用种子记忆"""
        return event_count < 10

    def _detect_pattern(self, event: Dict) -> Dict:
        """检测重复模式"""
        # 简化实现：相同小时 + 相同设备 + 相同操作 = 模式
        hour = event.get("hour")
        device = event.get("device")
        intent = event.get("intent")

        if not all([hour is not None, device, intent]):
            return {}

        matches = [
            e for e in self.observation_buffer
            if e.get("hour") == hour
            and e.get("device") == device
            and e.get("intent") == intent
        ]

        if len(matches) >= self.min_confirmations:
            return {
                "summary": f"每{hour}点{intent}{device}",
                "hour": hour,
                "device": device,
                "intent": intent,
                "count": len(matches),
            }
        return {}

    def _clear_pattern(self, pattern: Dict):
        """清除已确认的模式相关缓存"""
        self.observation_buffer = [
            e for e in self.observation_buffer
            if not (
                e.get("hour") == pattern.get("hour")
                and e.get("device") == pattern.get("device")
            )
        ]

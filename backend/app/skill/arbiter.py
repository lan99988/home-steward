"""冲突仲裁器——三层仲裁：用户优先 → 静态优先级 → 防震荡"""

import logging
import time
from collections import deque
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ConflictRecord:
    """单次冲突记录"""
    def __init__(self, device_id: str, domain: str, intent: str,
                 skill: str, priority: int):
        self.device_id = device_id
        self.domain = domain
        self.intent = intent
        self.skill = skill
        self.priority = priority
        self.timestamp = time.time()


class ConflictArbiter:
    """三层冲突仲裁器

    第一层: 用户指令优先（固定优先级 100）
    第二层: 静态优先级数值比较
    第三层: 同设备 30 秒内切换频率检测（防震荡）
    """

    def __init__(self, history_size: int = 50):
        self.history: deque = deque(maxlen=history_size)

    def resolve(self, intent: Dict[str, Any], skill_priority: int = 50,
                skill_name: str = "unknown") -> Optional[Dict[str, Any]]:
        """
        冲突仲裁主入口。

        Args:
            intent: 设备操作意图
            skill_priority: 当前 Skill 的优先级 (1-100)
            skill_name: 当前 Skill 名称

        Returns:
            通过 → 返回 intent；被阻止 → 返回 None
        """
        # 第一层：用户指令最高优先级（固定 100）
        if intent.get("source") == "user":
            return intent

        device_id = intent.get("device")
        domain = intent.get("domain", "unknown")

        # 第二层：检查 30 秒内的同设备冲突
        now = time.time()
        recent = [
            r for r in self.history
            if r.device_id == device_id
            and r.domain == domain
            and (now - r.timestamp) < 30
        ]

        if not recent:
            # 无冲突 → 放行并记录
            self._record(intent, skill_name, skill_priority)
            return intent

        # 优先级比较
        highest = max(r.priority for r in recent)
        if skill_priority > highest:
            # 当前 Skill 优先级更高 → 覆盖
            logger.info(f"⚡ {skill_name} (优先级{skill_priority}) 覆盖 "
                        f"之前的操作 (最高{highest})")
            self._record(intent, skill_name, skill_priority)
            return intent
        elif skill_priority < highest:
            # 被更高优先级的操作阻止
            logger.warning(f"⛔ {skill_name} (优先级{skill_priority}) "
                           f"被更高优先级阻止 (最高{highest})")
            return None

        # 第三层：同优先级 → 防震荡
        recent_toggles = sum(
            1 for r in recent
            if r.intent != intent.get("intent")
        )
        if recent_toggles >= 2:
            logger.warning(f"⚠️ 防震荡: {device_id} 在 30 秒内切换 "
                           f"{recent_toggles} 次，已阻止")
            return None

        self._record(intent, skill_name, skill_priority)
        return intent

    def _record(self, intent: Dict, skill_name: str, priority: int):
        """记录一次操作到历史"""
        record = ConflictRecord(
            device_id=intent.get("device", ""),
            domain=intent.get("domain", "unknown"),
            intent=intent.get("intent", ""),
            skill=skill_name,
            priority=priority,
        )
        self.history.append(record)

    def get_recent(self, device_id: str = None, minutes: int = 5) -> List[dict]:
        """获取最近的冲突记录"""
        now = time.time()
        cutoff = now - minutes * 60
        result = []
        for r in self.history:
            if r.timestamp < cutoff:
                continue
            if device_id and r.device_id != device_id:
                continue
            result.append({
                "device_id": r.device_id,
                "domain": r.domain,
                "intent": r.intent,
                "skill": r.skill,
                "priority": r.priority,
                "time": time.strftime("%H:%M:%S", time.localtime(r.timestamp)),
            })
        return result

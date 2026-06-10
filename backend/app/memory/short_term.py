"""短期记忆——当前会话，最多 50 条"""

import time
from collections import deque
from typing import Dict, Any, List


class ShortTermMemory:
    """短期记忆：当前会话的操作记录"""

    def __init__(self, max_size: int = 50):
        self.events: deque = deque(maxlen=max_size)

    def add(self, event: Dict[str, Any]):
        """添加一条事件"""
        self.events.append({
            **event,
            "timestamp": time.time(),
        })

    def get_recent(self, n: int = 10) -> List[Dict]:
        """获取最近 N 条事件"""
        return list(self.events)[-n:]

    def search(self, keyword: str) -> List[Dict]:
        """搜索记忆"""
        return [
            e for e in self.events
            if keyword.lower() in str(e).lower()
        ]

    def count(self) -> int:
        return len(self.events)

    def clear(self):
        self.events.clear()

"""三级通道路由器——根据指令复杂度自动选择处理通道"""

import time
import logging
from enum import Enum
from typing import Dict, Any, Optional, Tuple

from app.llm.express import ExpressMatcher
from app.llm.standard import LocalLLM

logger = logging.getLogger(__name__)


class Channel(Enum):
    EXPRESS = "express"      # < 500ms, 纯规则
    STANDARD = "standard"    # < 5s, 本地小模型
    DEEP = "deep"            # < 30s, 大模型/云端（暂未实现）


class LatencyRouter:
    """三级通道路由器：快速 → 标准 → 深度，逐级降级"""

    def __init__(self, express: ExpressMatcher, standard: LocalLLM):
        self.express = express
        self.standard = standard
        self.stats = {c: {"count": 0, "total_ms": 0} for c in Channel}

    async def route(self, text: str) -> Tuple[Channel, Optional[Dict[str, Any]]]:
        """路由用户输入到最合适的通道"""
        start = time.time()

        # 1. 快速通道：规则匹配（零成本）
        intent = self.express.match(text)
        if intent:
            elapsed = (time.time() - start) * 1000
            self._record(Channel.EXPRESS, elapsed)
            logger.info(f"⚡ [快速通道] {elapsed:.0f}ms → {intent}")
            return Channel.EXPRESS, intent

        # 2. 标准通道：本地小模型
        intent = await self.standard.parse_intent(text)
        if intent and intent.get("intent") != "unknown":
            elapsed = (time.time() - start) * 1000
            self._record(Channel.STANDARD, elapsed)
            logger.info(f"🧠 [标准通道] {elapsed:.0f}ms → {intent}")
            return Channel.STANDARD, intent

        # 3. 深度通道：暂未实现
        elapsed = (time.time() - start) * 1000
        self._record(Channel.DEEP, elapsed)
        logger.info(f"🔮 [深度通道] {elapsed:.0f}ms → 无法解析")
        return Channel.DEEP, None

    def _record(self, channel: Channel, elapsed_ms: float):
        self.stats[channel]["count"] += 1
        self.stats[channel]["total_ms"] += elapsed_ms

    def get_stats(self) -> dict:
        """获取各通道统计"""
        result = {}
        for ch, stat in self.stats.items():
            avg = stat["total_ms"] / stat["count"] if stat["count"] > 0 else 0
            result[ch.value] = {"count": stat["count"], "avg_ms": round(avg, 1)}
        return result

"""舒适度检测——确定性规则引擎 + LLM 文案润色

规则引擎 100% 确定性，不依赖 LLM 判断。
LLM 只在规则命中后做文案润色（把"温度偏高"润色为自然的提醒）。
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class ComfortRule:
    """一条舒适度规则"""
    name: str
    condition_fn: Callable[[Dict[str, Any]], bool]  # 判断是否触发
    message: str                                      # 默认文案
    priority: int = 0                                  # 优先级（数字越大越优先）


@dataclass
class ComfortSuggestion:
    """一条舒适度建议"""
    rule_name: str
    device_id: str
    message: str                    # 原始 message
    polished_message: str = ""      # LLM 润色后的文案
    triggered_at: float = 0.0


class ComfortEngine:
    """舒适度检测引擎——确定性规则"""

    def __init__(self):
        self.rules: List[ComfortRule] = []
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认舒适度规则"""
        self.rules = [
            ComfortRule(
                name="temperature_too_high",
                condition_fn=lambda s: (
                    s.get("temperature", 25) > 28
                    and s.get("device_type") == "ac"
                    and s.get("on") is False
                ),
                message="温度偏高，建议打开空调",
                priority=10,
            ),
            ComfortRule(
                name="ac_on_too_cold",
                condition_fn=lambda s: (
                    s.get("temperature", 24) < 18
                    and s.get("device_type") == "ac"
                    and s.get("on") is True
                ),
                message="空调温度过低，建议调高到 24°C",
                priority=8,
            ),
            ComfortRule(
                name="room_too_dark",
                condition_fn=lambda s: (
                    s.get("brightness", 100) < 20
                    and s.get("device_type") == "light"
                    and s.get("on") is False
                    and s.get("is_night") is False
                ),
                message="光线偏暗，建议开灯",
                priority=7,
            ),
            ComfortRule(
                name="light_too_bright_night",
                condition_fn=lambda s: (
                    s.get("brightness", 0) > 80
                    and s.get("device_type") == "light"
                    and s.get("on") is True
                    and s.get("is_night") is True
                ),
                message="夜间灯光太亮，建议调暗",
                priority=6,
            ),
            ComfortRule(
                name="curtain_closed_daytime",
                condition_fn=lambda s: (
                    s.get("position", 100) < 30
                    and s.get("device_type") == "curtain"
                    and s.get("is_night") is False
                ),
                message="白天窗帘关闭，建议打开透光",
                priority=5,
            ),
        ]

    def add_rule(self, rule: ComfortRule):
        """添加自定义规则"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def check_device(self, device_id: str, status: Dict[str, Any]) -> List[ComfortSuggestion]:
        """检查单个设备是否偏离舒适区"""
        suggestions = []
        for rule in self.rules:
            try:
                if rule.condition_fn(status):
                    suggestions.append(ComfortSuggestion(
                        rule_name=rule.name,
                        device_id=device_id,
                        message=rule.message,
                        triggered_at=time.time(),
                    ))
            except Exception as e:
                logger.warning(f"规则 {rule.name} 检查失败: {e}")
        return suggestions

    def check_all(self, device_statuses: Dict[str, Dict[str, Any]]) -> List[ComfortSuggestion]:
        """检查所有设备"""
        all_suggestions = []
        for device_id, status in device_statuses.items():
            all_suggestions.extend(self.check_device(device_id, status))
        return all_suggestions


# ============================================================
# LLM 文案润色（可选）
# ============================================================

class ComfortPolisher:
    """LLM 润色——只做文案，不做判断"""

    def __init__(self, llm=None):
        self.llm = llm  # LocalLLM 实例，可选

    async def polish(self, suggestion: ComfortSuggestion) -> str:
        """用 LLM 润色建议文案（不改变建议本身）"""
        if not self.llm:
            return suggestion.message

        prompt = (
            f"将下面的智能家居提醒改写为口语化的中文，不要改变含义，不要增减信息。\n"
            f"原文: {suggestion.message}\n"
            f"改写后:"
        )
        # 这里会调用 LLM，但如果 LLM 不可用则返回原文
        try:
            resp = await self.llm.client.post(
                f"{self.llm.base_url}/api/generate",
                json={
                    "model": self.llm.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                    "options": {"num_predict": 64},
                },
                timeout=30.0,
            )
            result = resp.json()
            polished = result["response"].strip().strip("\"'")
            if polished:
                return polished
        except Exception:
            pass
        return suggestion.message


# ============================================================
# 全局单例
# ============================================================

comfort_engine = ComfortEngine()
comfort_polisher = ComfortPolisher()

"""形式化验证边界——物理安全约束，LLM 无法修改"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FormalGuard:
    """形式化约束：不是"校验"，是"不可能越界"

    这些边界在系统编译时就固定，LLM 输出无法修改。
    """

    # 物理安全边界
    TEMPERATURE_RANGE = (16, 30)       # °C
    BRIGHTNESS_RANGE = (1, 100)        # %
    COLOR_TEMP_RANGE = (2200, 6500)    # K
    HUMIDITY_RANGE = (30, 80)          # %
    POSITION_RANGE = (0, 100)          # % (窗帘等)

    SAFE_RANGES = {
        "temperature": TEMPERATURE_RANGE,
        "brightness": BRIGHTNESS_RANGE,
        "color_temp": COLOR_TEMP_RANGE,
        "humidity": HUMIDITY_RANGE,
        "position": POSITION_RANGE,
    }

    # 允许的动作白名单
    ALLOWED_ACTIONS = {
        "turn_on", "turn_off", "set_temperature",
        "set_brightness", "set_mode", "set_scene",
        "set_color_temp", "set_position",
    }

    @staticmethod
    def verify_parameter(name: str, value: Any) -> bool:
        """验证单个参数是否在安全范围内"""
        if name not in FormalGuard.SAFE_RANGES:
            return True  # 不在约束列表中的参数放行
        lo, hi = FormalGuard.SAFE_RANGES[name]
        if not isinstance(value, (int, float)):
            logger.warning(f"参数 {name}={value} 类型错误")
            return False
        if not (lo <= value <= hi):
            logger.warning(f"⚠️ 参数越界: {name}={value} 不在 [{lo}, {hi}] 范围内")
            return False
        return True

    @staticmethod
    def verify_action(action: str) -> bool:
        """验证动作是否在允许列表中"""
        return action in FormalGuard.ALLOWED_ACTIONS

    @classmethod
    def verify_intent(cls, intent: Dict[str, Any]) -> bool:
        """全量验证：动作 + 参数同时校验"""
        if not intent:
            return False

        action = intent.get("intent", "")
        if not cls.verify_action(action):
            logger.warning(f"禁止的动作: {action}")
            return False

        # 检查各种可能的参数名
        param_checks = [
            ("temperature", intent.get("temperature") or intent.get("value")),
            ("brightness", intent.get("brightness")),
            ("color_temp", intent.get("color_temp")),
            ("position", intent.get("position")),
        ]
        for param_name, param_value in param_checks:
            if param_value is not None and not cls.verify_parameter(param_name, param_value):
                return False

        return True

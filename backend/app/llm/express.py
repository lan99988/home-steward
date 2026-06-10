"""快速通道：纯规则匹配，零 LLM 调用，< 500ms"""

import re
from typing import Optional, Dict, Any


class ExpressMatcher:
    """快速通道匹配器——纯正则匹配，零延迟"""

    def __init__(self):
        self.PATTERNS = [
            # 基础开关
            (r"打开(.+)", lambda m: {"intent": "turn_on", "device": m.group(1).strip()}),
            (r"关闭(.+)", lambda m: {"intent": "turn_off", "device": m.group(1).strip()}),
            (r"关掉(.+)", lambda m: {"intent": "turn_off", "device": m.group(1).strip()}),
            (r"开一下(.+)", lambda m: {"intent": "turn_on", "device": m.group(1).strip()}),

            # 温度调节
            (r"(.+)调到(\d+)度", lambda m: {
                "intent": "set_temperature",
                "device": m.group(1).strip(),
                "value": int(m.group(2)),
            }),
            (r"(.+)温度设为(\d+)", lambda m: {
                "intent": "set_temperature",
                "device": m.group(1).strip(),
                "value": int(m.group(2)),
            }),
            (r"(.+)调高(\d+)度", lambda m: {
                "intent": "set_temperature_up",
                "device": m.group(1).strip(),
                "value": int(m.group(2)),
            }),
            (r"(.+)调低(\d+)度", lambda m: {
                "intent": "set_temperature_down",
                "device": m.group(1).strip(),
                "value": int(m.group(2)),
            }),

            # 亮度调节
            (r"(.+)亮度调到(\d+)", lambda m: {
                "intent": "set_brightness",
                "device": m.group(1).strip(),
                "value": int(m.group(2)),
            }),
            (r"(.+)调亮一点", lambda m: {
                "intent": "set_brightness",
                "device": m.group(1).strip(),
                "value": "brighter",
            }),
            (r"(.+)调暗一点", lambda m: {
                "intent": "set_brightness",
                "device": m.group(1).strip(),
                "value": "darker",
            }),

            # 模式切换
            (r"(.+)设为(.+)模式", lambda m: {
                "intent": "set_mode",
                "device": m.group(1).strip(),
                "mode": m.group(2).strip(),
            }),
            (r"(.+)切到(.+)模式", lambda m: {
                "intent": "set_mode",
                "device": m.group(1).strip(),
                "mode": m.group(2).strip(),
            }),

            # 批量操作
            (r"所有灯(打开|关闭)", lambda m: {
                "intent": "all_lights",
                "action": "turn_on" if m.group(1) == "打开" else "turn_off",
            }),
            (r"全(打开|关闭)", lambda m: {
                "intent": "all_lights",
                "action": "turn_on" if m.group(1) == "打开" else "turn_off",
            }),

            # 场景模式
            (r"(离家|回家|睡眠|早安)模式", lambda m: {
                "intent": "set_scene",
                "scene": m.group(1),
            }),
        ]

    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试匹配用户输入，返回结构化 intent 或 None"""
        if not text or not text.strip():
            return None

        text = text.strip()
        for pattern, builder in self.PATTERNS:
            m = re.match(pattern, text)
            if m:
                return builder(m)
        return None

    def add_pattern(self, regex: str, builder) -> None:
        """动态添加匹配模式（用于热更新）"""
        self.PATTERNS.append((re.compile(regex), builder))

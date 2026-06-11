"""快速通道：纯规则匹配 + 精确命令映射，零 LLM 调用，< 500ms

匹配优先级:
  1. EXACT_COMMANDS (O(1) 字典查) — 用于语音高频指令 "打开客厅灯"
  2. PATTERNS (正则匹配) — 用于灵活指令 ".+调到\d+度"
  3. 未命中 → 交给 LLM 标准通道
"""

import re
from typing import Optional, Dict, Any, Callable


class ExpressMatcher:
    """快速通道匹配器——精确命令 + 正则匹配，零延迟"""

    def __init__(self):
        # 精确命令字典（O(1) 查找，优先匹配）
        # 用于语音高频指令，加新设备只需在此注册
        self.EXACT_COMMANDS: Dict[str, Dict[str, Any]] = {
            # ---- 客厅灯 ----
            "打开客厅灯": {"intent": "turn_on", "device": "light_living"},
            "关闭客厅灯": {"intent": "turn_off", "device": "light_living"},
            "关掉客厅灯": {"intent": "turn_off", "device": "light_living"},
            "开一下客厅灯": {"intent": "turn_on", "device": "light_living"},
            # ---- 卧室灯 ----
            "打开卧室灯": {"intent": "turn_on", "device": "light_bedroom"},
            "关闭卧室灯": {"intent": "turn_off", "device": "light_bedroom"},
            "关掉卧室灯": {"intent": "turn_off", "device": "light_bedroom"},
            # ---- 厨房灯 ----
            "打开厨房灯": {"intent": "turn_on", "device": "light_kitchen"},
            "关闭厨房灯": {"intent": "turn_off", "device": "light_kitchen"},
            "关掉厨房灯": {"intent": "turn_off", "device": "light_kitchen"},
            # ---- 客厅空调 ----
            "打开空调": {"intent": "turn_on", "device": "ac_living"},
            "关闭空调": {"intent": "turn_off", "device": "ac_living"},
            "关掉空调": {"intent": "turn_off", "device": "ac_living"},
            "打开客厅空调": {"intent": "turn_on", "device": "ac_living"},
            "关闭客厅空调": {"intent": "turn_off", "device": "ac_living"},
            # ---- 客厅窗帘 ----
            "打开窗帘": {"intent": "turn_on", "device": "curtain_living"},
            "关闭窗帘": {"intent": "turn_off", "device": "curtain_living"},
            "关掉窗帘": {"intent": "turn_off", "device": "curtain_living"},
            # ---- 批量操作 ----
            "打开所有灯": {"intent": "all_lights", "action": "turn_on"},
            "关闭所有灯": {"intent": "all_lights", "action": "turn_off"},
            "关掉所有灯": {"intent": "all_lights", "action": "turn_off"},
            # ---- 场景 ----
            "离家模式": {"intent": "set_scene", "scene": "离家模式"},
            "回家模式": {"intent": "set_scene", "scene": "回家模式"},
            "睡眠模式": {"intent": "set_scene", "scene": "睡眠模式"},
            "早安模式": {"intent": "set_scene", "scene": "早安模式"},
        }

        self.PATTERNS = [
            # 基础开关（兜底）
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
        """三阶段匹配：精确命令 → 正则 → None"""
        if not text or not text.strip():
            return None

        text = text.strip()

        # 1. 精确命令匹配（O(1) 字典查，< 1μs）
        if text in self.EXACT_COMMANDS:
            return dict(self.EXACT_COMMANDS[text])  # 返回副本以免外部修改

        # 2. 正则模式匹配
        for pattern, builder in self.PATTERNS:
            m = re.match(pattern, text)
            if m:
                return builder(m)

        # 3. 未命中
        return None

    def add_exact(self, phrase: str, intent: Dict[str, Any]) -> None:
        """注册精确命令（用于语音高频指令）"""
        self.EXACT_COMMANDS[phrase] = intent

    def add_pattern(self, regex: str, builder: Callable) -> None:
        """动态添加正则匹配模式"""
        self.PATTERNS.append((re.compile(regex), builder))

    def remove_exact(self, phrase: str) -> bool:
        """移除精确命令"""
        return bool(self.EXACT_COMMANDS.pop(phrase, None))

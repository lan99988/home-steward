"""意图门——区分"这是指令"和"这只是说话" """

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class IntentGate:
    """判断用户输入是指令还是闲聊

    防止"好冷啊"被误执行为设备操作。
    """

    # 明确是非指令的模式
    NON_COMMAND_PATTERNS = [
        r"好(冷|热|暗|亮)啊",
        r"今天(天气|心情).*(好|差|不错)",
        r"(饿|困|累)了",
        r"这(个|灯|空调).*(太|有点|好)",
        r"(想|希望|要是).*(就|该|多)好",
        r"你觉得呢",
        r"你(会|能)做.*吗",
        r"吃了(吗|没)",
        r"早上好|中午好|晚上好|晚安",
        r"你好|你好啊|嗨|hello|hi",
        r"谢谢|多谢|感谢",
    ]

    # 明确是指令的模式
    COMMAND_PATTERNS = [
        r"(打开|关闭|关掉|开一下)\w*",
        r"调到?\d+",
        r"设为\w+模式",
        r"(把|帮我把|请).*(打开|关闭|调到|设为)",
        r"所有灯",
        r".*亮度.*\d+",
        r".*温度.*\d+",
    ]

    def is_command(self, text: str) -> Tuple[bool, float]:
        """
        判断是否指令。

        Returns:
            (是否指令, 置信度)
        """
        text = text.strip()

        for pat in self.COMMAND_PATTERNS:
            if re.search(pat, text):
                return True, 0.9

        for pat in self.NON_COMMAND_PATTERNS:
            if re.search(pat, text):
                return False, 0.8

        # 默认通过（宁放过，不误杀）
        return True, 0.5

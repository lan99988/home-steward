"""设备控制 Skill — 基础设备操作"""

import logging

logger = logging.getLogger(__name__)


async def handle(intent: dict, context: dict) -> dict:
    """处理设备控制意图

    Args:
        intent: 设备操作意图
        context: 执行上下文（含 safety_layer 等）

    Returns:
        执行结果
    """
    safety_layer = context.get("safety_layer")
    if not safety_layer:
        return {"error": "no_safety_layer", "message": "缺少安全执行层"}

    validated = safety_layer.validate(intent)
    if not validated:
        return {"error": "validation_failed", "message": f"指令被安全层拒绝: {intent}"}

    result = await safety_layer.execute(validated)
    return result

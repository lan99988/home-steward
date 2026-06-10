"""安全执行层——LLM 建议 → 安全层校验 → 设备执行"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SafetyLayer:
    """安全执行层：所有设备操作必须经过此层校验"""

    # 白名单——允许的指令类型
    WHITELIST_INTENTS = {
        "turn_on", "turn_off", "set_temperature", "set_brightness",
        "set_mode", "set_color_temp", "set_position", "all_lights",
        "set_scene",
    }

    # 速率限制
    RATE_LIMIT = 10  # 最多每秒 10 条指令

    def __init__(self, registry):
        self.registry = registry
        self.command_timestamps = []

    def validate(self, intent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """校验 intent 是否合法，返回清洗后的指令或 None"""
        if not intent:
            return None

        intent_type = intent.get("intent")

        # 1. 指令类型白名单
        if intent_type not in self.WHITELIST_INTENTS:
            logger.warning(f"❌ 非法指令类型: {intent_type}")
            return None

        # 2. 批量操作特殊处理
        if intent_type == "all_lights":
            return intent

        # 3. 设备解析
        device_id = intent.get("device")
        if not device_id:
            logger.warning("❌ 指令缺少设备")
            return None

        # 支持中文名或设备 ID
        resolved = self._resolve_device(device_id)
        if not resolved:
            logger.warning(f"❌ 未知设备: {device_id}")
            return None

        intent["device"] = resolved

        # 4. 参数范围校验（委托给 FormalGuard）
        from app.execution.formal_guard import FormalGuard
        if not FormalGuard.verify_intent(intent):
            logger.warning(f"❌ 参数越界: {intent}")
            return None

        return intent

    def _resolve_device(self, name: str) -> Optional[str]:
        """通过名称或 ID 模糊匹配设备"""
        # 先精确匹配 ID
        if name in self.registry.devices:
            return name
        # 再模糊匹配
        device = self.registry.find_by_name(name)
        if device:
            return device.device_id
        return None

    async def execute(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """执行校验后的指令"""
        intent_type = intent.get("intent")
        device_id = intent.get("device")

        if intent_type == "all_lights":
            return await self._execute_all_lights(intent.get("action", "turn_on"))

        device = self.registry.get(device_id)
        if not device:
            return {"error": f"设备 '{device_id}' 未找到", "success": False}

        try:
            result = await self._dispatch(device, intent_type, intent)
            return {"success": result, "device": device_id, "intent": intent_type}
        except Exception as e:
            logger.error(f"执行失败: {device_id}/{intent_type}: {e}")
            return {"error": str(e), "success": False}

    async def _dispatch(self, device, intent_type: str, intent: Dict) -> bool:
        """分发指令到具体设备方法"""
        kwargs = {k: v for k, v in intent.items()
                  if k in ("brightness", "color_temp", "mode",
                           "temperature", "position", "value")}

        if intent_type == "turn_on":
            return await device.turn_on(**kwargs)
        elif intent_type == "turn_off":
            return await device.turn_off()
        elif intent_type == "set_temperature":
            value = intent.get("value", intent.get("temperature", 24))
            return await device.turn_on(temperature=value)
        elif intent_type == "set_brightness":
            value = intent.get("value", intent.get("brightness", 50))
            return await device.turn_on(brightness=value)
        elif intent_type == "set_mode":
            mode = intent.get("mode", "cool")
            return await device.turn_on(mode=mode)
        elif intent_type == "set_position":
            return await device.turn_on(position=intent.get("value", 50))
        else:
            logger.warning(f"不支持的指令类型: {intent_type}")
            return False

    async def _execute_all_lights(self, action: str) -> Dict:
        """批量操作所有灯"""
        results = []
        for device in self.registry.get_devices_by_type("light"):
            if action == "turn_on":
                success = await device.turn_on()
            else:
                success = await device.turn_off()
            results.append({"device": device.device_id, "success": success})
        return {"success": all(r["success"] for r in results),
                "results": results, "intent": "all_lights"}

"""设备 API 路由——快慢路径分离"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.execution.safety import SafetyLayer
from app.llm.express import ExpressMatcher
from app.llm.router import LatencyRouter
from app.execution.sanitizer import sanitizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/devices", tags=["devices"])

# 运行时注入
safety_layer: SafetyLayer = None
matcher: ExpressMatcher = None
llm_router: LatencyRouter = None


class CommandRequest(BaseModel):
    text: str


class CommandResponse(BaseModel):
    success: bool
    message: str
    channel: Optional[str] = None
    intent: Optional[dict] = None


@router.get("/")
async def list_devices():
    """获取所有设备列表"""
    return {"devices": safety_layer.registry.list()}


@router.get("/{device_id}")
async def get_device(device_id: str):
    """获取单个设备状态"""
    device = safety_layer.registry.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {
        "id": device_id,
        "name": device.name,
        "status": await device.get_status(),
    }


@router.post("/command", response_model=CommandResponse)
async def command(req: CommandRequest):
    """发送设备控制指令

    快慢路径分离:
      快路径（设备指令）: ExpressMatcher → SafetyLayer → 执行 (跳过 Sanitizer)
      慢路径（LLM 解析）:  ExpressMatcher 未命中 → Sanitizer → LLM → 执行
    """
    if not req.text.strip():
        return CommandResponse(success=False, message="指令不能为空")

    text = req.text

    # ===== 快路径：精确命令 + 正则匹配（不走 Sanitizer，< 200ms） =====
    intent = matcher.match(text)
    if intent:
        validated = safety_layer.validate(intent)
        if not validated:
            return CommandResponse(
                success=False,
                message=f"指令被安全层拒绝: {intent}",
                channel="express",
                intent=intent,
            )
        result = await safety_layer.execute(validated)
        success = result.get("success", False)
        return CommandResponse(
            success=success,
            message=f"{'✅' if success else '❌'} 已执行: {validated['intent']} → {validated.get('device', '')}",
            channel="express",
            intent=validated,
        )

    # ===== 慢路径：LLM 解析（必经 Sanitizer 脱敏） =====
    # 1. 脱敏
    sanitized = sanitizer.clean(text, context="command")

    # 2. LLM 解析
    channel, intent = await llm_router.route_to_llm(sanitized)

    if not intent:
        return CommandResponse(
            success=False,
            message=f"无法理解指令: '{text}'",
            channel=channel.value if channel else "deep",
        )

    # 3. 安全层校验
    validated = safety_layer.validate(intent)
    if not validated:
        return CommandResponse(
            success=False,
            message=f"指令被安全层拒绝: {intent}",
            channel=channel.value if channel else None,
            intent=intent,
        )

    # 4. 执行
    result = await safety_layer.execute(validated)
    success = result.get("success", False)
    return CommandResponse(
        success=success,
        message=f"{'✅' if success else '❌'} 已执行: {validated['intent']} → {validated.get('device', '')}",
        channel=channel.value if channel else None,
        intent=validated,
    )

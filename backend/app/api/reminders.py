"""提醒 API 路由"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.execution.sanitizer import sanitizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reminders", tags=["reminders"])

# 运行时注入
reminder_service: Optional["ReminderService"] = None


class ReminderRequest(BaseModel):
    text: str


class ReminderResponse(BaseModel):
    success: bool
    message: str
    reminder: Optional[dict] = None


@router.post("/", response_model=ReminderResponse)
async def create_reminder(req: ReminderRequest):
    """从自然语言创建提醒（必经脱敏）"""
    if not req.text.strip():
        return ReminderResponse(success=False, message="内容不能为空")

    # 先脱敏
    sanitized = sanitizer.clean(req.text, context="reminder")

    if not reminder_service:
        return ReminderResponse(success=False, message="提醒服务未就绪")

    result = await reminder_service.create_from_text(sanitized)
    if not result:
        return ReminderResponse(
            success=False, message="无法解析您的提醒，请说得更具体一些，例如「每天8点开灯」"
        )

    return ReminderResponse(
        success=True,
        message=f"提醒已创建: {result['reminder']['cron']}",
        reminder=result['reminder'],
    )


@router.get("/")
async def list_reminders():
    """列出所有提醒"""
    if not reminder_service:
        return {"reminders": []}
    return {"reminders": reminder_service.list_reminders()}


@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: str):
    """删除提醒"""
    if not reminder_service:
        raise HTTPException(status_code=503, detail="提醒服务未就绪")
    ok = reminder_service.delete_reminder(reminder_id)
    if not ok:
        raise HTTPException(status_code=404, detail="提醒不存在")
    return {"success": True, "message": "提醒已删除"}

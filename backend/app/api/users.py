"""用户 API 路由"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])

# 运行时注入
user_manager = None


class UserCreate(BaseModel):
    user_id: str
    name: str
    role: str = "member"


class PreferenceUpdate(BaseModel):
    domain: str
    preferences: dict


@router.get("/")
async def list_users():
    """列出所有用户"""
    if not user_manager:
        return {"users": []}
    return {"users": user_manager.list_users()}


@router.post("/")
async def create_user(req: UserCreate):
    """创建用户"""
    if not user_manager:
        raise HTTPException(status_code=503, detail="用户管理未就绪")
    user = user_manager.add_user(req.user_id, req.name, req.role)
    return {"status": "created", "user": user.to_dict()}


@router.get("/{user_id}")
async def get_user(user_id: str):
    """获取用户详情"""
    if not user_manager:
        raise HTTPException(status_code=503, detail="用户管理未就绪")
    user = user_manager.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


@router.post("/{user_id}/preferences")
async def update_preferences(user_id: str, req: PreferenceUpdate):
    """更新用户偏好"""
    if not user_manager:
        raise HTTPException(status_code=503, detail="用户管理未就绪")
    user = user_manager.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.preferences[req.domain] = req.preferences
    return {"status": "updated", "preferences": user.preferences}

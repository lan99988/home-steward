"""记忆 API 路由"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memory", tags=["memory"])

# 运行时注入
memory_system = None


@router.get("/")
async def get_memories():
    """获取记忆列表"""
    return {"memories": []}


@router.get("/insights")
async def get_insights():
    """获取系统洞察"""
    return {"insights": []}


@router.post("/recall")
async def recall(query: str = "", limit: int = 10):
    """按需检索记忆"""
    return {"results": []}

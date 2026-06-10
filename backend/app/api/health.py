"""系统健康 API"""

import json
import logging
import os
import shutil
import time

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])

START_TIME = time.time()

# 运行时注入
mqtt_client = None
registry = None
health_monitor = None
llm_router = None


@router.get("/")
async def health():
    """简单健康检查"""
    uptime_s = time.time() - START_TIME
    days, remainder = divmod(int(uptime_s), 86400)
    hours = remainder // 3600

    return {
        "status": "ok",
        "version": "0.1.0",
        "uptime": f"{days}d {hours}h",
        "devices": len(registry.devices) if registry else 0,
        "mqtt": "connected" if mqtt_client and mqtt_client.connected else "disconnected",
    }


@router.get("/detailed")
async def health_detailed():
    """详细健康状态"""
    uptime_s = time.time() - START_TIME
    days, remainder = divmod(int(uptime_s), 86400)
    hours = remainder // 3600

    disk = shutil.disk_usage("/data" if os.path.exists("/data") else ".")

    active_model = "unknown"
    try:
        with open("data/active_model.json") as f:
            active_model = json.load(f).get("model", "unknown")
    except Exception:
        pass

    # LLM 通道统计
    channel_stats = {}
    if llm_router:
        channel_stats = llm_router.get_stats()

    return {
        "backend": {
            "status": "running",
            "uptime": f"{days}d {hours}h",
            "version": "0.1.0",
        },
        "mqtt": {
            "status": "connected" if mqtt_client and mqtt_client.connected else "disconnected",
            "messages": getattr(mqtt_client, "message_count", 0) if mqtt_client else 0,
        },
        "llm": {
            "status": "configured" if active_model != "unknown" else "not_configured",
            "model": active_model,
            "channels": channel_stats,
        },
        "devices": {
            "count": len(registry.devices) if registry else 0,
        },
        "disk": {
            "total": f"{disk.total / (1024**3):.1f}GB",
            "used": f"{disk.used / (1024**3):.1f}GB",
            "free": f"{disk.free / (1024**3):.1f}GB",
        },
    }

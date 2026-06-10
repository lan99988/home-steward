"""Home Steward Agent — FastAPI 应用入口"""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.execution.mqtt import MQTTClient
from app.execution.device_registry import DeviceRegistry
from app.execution.safety import SafetyLayer
from app.llm.express import ExpressMatcher
from app.llm.standard import LocalLLM
from app.llm.router import LatencyRouter
from app.llm.provisioner import ModelProvisioner
from app.skill.registry import SkillRegistry
from app.skill.conflict_predictor import ConflictPredictor
from app.skill.health import HealthMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("home-steward")

mqtt_client = MQTTClient()
device_registry = DeviceRegistry()
express_matcher = ExpressMatcher()
local_llm = LocalLLM()
llm_router = LatencyRouter(express_matcher, local_llm)
safety_layer = SafetyLayer(device_registry)
skill_registry = SkillRegistry()
conflict_predictor = ConflictPredictor()
health_monitor = HealthMonitor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🐌 Home Steward Agent 启动中...")
    logger.info(f"  版本: {settings.app_version}")
    logger.info(f"  数据目录: {settings.data_dir}")

    init_db()
    logger.info("✅ 数据库初始化完成")

    mqtt_client.connect()
    logger.info(f"✅ MQTT 连接 (-> {settings.mqtt_host}:{settings.mqtt_port})")

    device_registry.register_virtual_devices(mqtt_client)
    logger.info(f"✅ 已注册 {len(device_registry.devices)} 个虚拟设备")

    active_model_path = Path("data/active_model.json")
    if not active_model_path.exists():
        logger.info("🔍 首次启动：硬件探测中...")
        provisioner = ModelProvisioner()
        spec = provisioner.probe()
        recommendation = provisioner.recommend(spec)
        logger.info(f"📋 推荐模型: {recommendation.name} ({recommendation.quality})")
        provisioner.save_active_model(recommendation)
        provisioner.deploy(recommendation)
    else:
        try:
            with open(active_model_path) as f:
                active = json.load(f)
            logger.info(f"📋 当前模型: {active.get('model')}")
        except Exception:
            pass

    skill_registry.discover_builtin()
    logger.info(f"✅ 已发现 {len(skill_registry.skills)} 个内置 Skill")

    import app.api.devices as devices_api
    devices_api.safety_layer = safety_layer
    devices_api.matcher = express_matcher
    devices_api.llm_router = llm_router

    import app.api.skills as skills_api
    skills_api.registry = skill_registry
    skills_api.conflict_predictor = conflict_predictor

    import app.api.memory as memory_api
    import app.api.health as health_api
    health_api.mqtt_client = mqtt_client
    health_api.registry = device_registry
    health_api.health_monitor = health_monitor
    health_api.llm_router = llm_router

    import app.api.users as users_api
    from app.user.profiles import UserManager
    users_api.user_manager = UserManager()

    logger.info("🐌 Home Steward Agent 就绪！")
    logger.info(f"  前端: http://localhost:8000/")
    logger.info(f"  API:  http://localhost:8000/docs")

    yield

    logger.info("🐌 Home Steward Agent 关闭中...")
    mqtt_client.disconnect()
    await local_llm.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 路由必须注册在 static mount 之前 =====
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version, "devices": len(device_registry.devices)}

import app.api.devices as devices_api
import app.api.skills as skills_api
import app.api.memory as memory_api
import app.api.health as health_api
import app.api.users as users_api

app.include_router(devices_api.router)
app.include_router(skills_api.router)
app.include_router(memory_api.router)
app.include_router(health_api.router)
app.include_router(users_api.router)

# ===== 前端界面（static mount 必须在最后） =====
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    logger.info(f"✅ 前端界面已挂载")

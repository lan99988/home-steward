"""系统配置管理"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 应用
    app_name: str = "Home Steward Agent"
    app_version: str = "0.1.0"
    debug: bool = True

    # 数据库
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/steward.db")

    # MQTT
    mqtt_host: str = os.getenv("MQTT_HOST", "localhost")
    mqtt_port: int = int(os.getenv("MQTT_PORT", "1883"))

    # Ollama
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # 数据目录
    data_dir: str = os.getenv("STEWARD_DATA_DIR", "./data")
    memory_dir: str = os.getenv("STEWARD_MEMORY_DIR", "./data/memory")

    # 模型
    active_model: str = "auto"  # auto 或具体模型名

    # Skill
    max_skills: int = 20
    skill_paths: Optional[List[str]] = None  # 在 post_init 中初始化

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 探测项目根目录
def _find_project_root() -> Path:
    """从当前文件位置向上查找项目根"""
    current = Path(__file__).resolve().parent  # app/core/
    # 向上找到 backend/ 或项目根
    for parent in [current.parent.parent.parent,  # backend/../../ -> 项目根
                   current.parent.parent,  # backend/ -> backend/
                   current.parent,  # app/ -> app/
                   ]:
        if (parent / "docker-compose.yml").exists() or \
           (parent / "skills").exists() or \
           (parent / "backend").exists():
            return parent
    return Path(".").resolve()


PROJECT_ROOT = _find_project_root()

settings = Settings()

# 初始化 Skill 路径
if settings.skill_paths is None:
    settings.skill_paths = [
        str(PROJECT_ROOT / "skills" / "built-in"),
        str(PROJECT_ROOT / "skills" / "user-installed"),
    ]

# 确保数据目录存在
data_path = Path(settings.data_dir)
if not data_path.is_absolute():
    data_path = PROJECT_ROOT / settings.data_dir
data_path.mkdir(parents=True, exist_ok=True)

memory_path = Path(settings.memory_dir)
if not memory_path.is_absolute():
    memory_path = PROJECT_ROOT / settings.memory_dir
memory_path.mkdir(parents=True, exist_ok=True)

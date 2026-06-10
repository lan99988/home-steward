"""Skill 运行时——Skill 加载、执行和生命周期管理"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SkillManifest(BaseModel):
    """Skill 元数据声明"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    domains: List[Dict[str, Any]] = []
    priority: int = 50
    conflict_resolution: str = "yield_on_user"
    compatible_with: Dict[str, str] = {}


class Skill:
    """单个 Skill 实例——从目录加载的自包含能力单元"""

    def __init__(self, path: Path):
        self.path = path
        self.manifest = self._load_manifest()
        self.module = self._load_module()
        self.enabled = True
        self.health_score = 1.0
        self.last_used: Optional[datetime] = None
        self.execution_count = 0

    def _load_manifest(self) -> SkillManifest:
        """从 SKILL.md 加载元数据"""
        manifest_path = self.path / "SKILL.md"
        if not manifest_path.exists():
            logger.warning(f"Skill {self.path.name} 缺少 SKILL.md")
            return SkillManifest(name=self.path.name)

        content = manifest_path.read_text(encoding="utf-8")
        try:
            # 解析 YAML frontmatter (--- 包裹的部分)
            parts = content.split("---")
            if len(parts) >= 2:
                data = yaml.safe_load(parts[1])
                if data:
                    return SkillManifest(**data)
        except Exception as e:
            logger.error(f"解析 SKILL.md 失败 ({self.path.name}): {e}")

        return SkillManifest(name=self.path.name)

    def _load_module(self):
        """动态加载 main.py 中的 Python 代码"""
        main_py = self.path / "main.py"
        if not main_py.exists():
            logger.warning(f"Skill {self.manifest.name} 缺少 main.py")
            return None

        try:
            spec = importlib.util.spec_from_file_location(
                f"skill_{self.manifest.name}",
                str(main_py),
            )
            module = importlib.util.module_from_spec(spec)
            # 注入依赖
            module._skill_path = str(self.path)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"加载 Skill '{self.manifest.name}' 失败: {e}")
            return None

    async def execute(self, intent: Dict[str, Any], context: Dict = None) -> Dict[str, Any]:
        """执行 Skill 的 handle 函数"""
        if not self.enabled:
            return {"error": "skill_disabled", "message": f"Skill '{self.manifest.name}' 已禁用"}

        if not self.module:
            return {"error": "no_module", "message": "Skill 代码未加载"}

        handler = getattr(self.module, "handle", None)
        if not handler:
            return {"error": "no_handler", "message": "Skill 没有 handle 函数"}

        try:
            self.execution_count += 1
            self.last_used = datetime.now()
            result = await handler(intent, context or {})
            return result
        except Exception as e:
            logger.error(f"执行 Skill '{self.manifest.name}' 异常: {e}")
            return {"error": str(e)}

    def get_info(self) -> dict:
        """获取 Skill 摘要信息"""
        return {
            "name": self.manifest.name,
            "version": self.manifest.version,
            "description": self.manifest.description or "",
            "priority": self.manifest.priority,
            "domains": self.manifest.domains,
            "enabled": self.enabled,
            "health_score": self.health_score,
            "execution_count": self.execution_count,
        }

    def __repr__(self):
        return f"<Skill '{self.manifest.name}' v{self.manifest.version}>"

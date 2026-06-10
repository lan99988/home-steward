"""Skill 仓库——Skill 的安装、卸载、发现和管理"""

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings
from app.skill.runtime import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Skill 仓库：管理所有 Skill 的注册、发现和生命周期"""

    def __init__(self):
        self.skills: Dict[str, Skill] = {}

    def discover(self, paths: List[Path] = None):
        """从目录中发现并加载所有 Skill"""
        if paths is None:
            paths = [Path(p) for p in settings.skill_paths]

        loaded = 0
        for base_path in paths:
            if not base_path.exists():
                logger.warning(f"Skill 路径不存在: {base_path}")
                continue
            for skill_dir in base_path.iterdir():
                if not skill_dir.is_dir():
                    continue
                if (skill_dir / "SKILL.md").exists() or (skill_dir / "main.py").exists():
                    try:
                        skill = Skill(skill_dir)
                        self.skills[skill.manifest.name] = skill
                        loaded += 1
                        logger.info(f"  📦 加载 Skill: {skill.manifest.name} v{skill.manifest.version}")
                    except Exception as e:
                        logger.error(f"  加载失败 ({skill_dir.name}): {e}")

        logger.info(f"📚 共加载 {loaded} 个 Skill")

    def discover_builtin(self):
        """仅发现内置 Skill"""
        from app.core.config import settings, PROJECT_ROOT
        builtin_paths = [Path(p) for p in settings.skill_paths
                        if 'built-in' in p]
        if not builtin_paths:
            # 回退：相对于项目根
            builtin_paths = [PROJECT_ROOT / "skills" / "built-in"]
        self.discover(builtin_paths)

    def get(self, name: str) -> Optional[Skill]:
        """根据名称获取 Skill"""
        return self.skills.get(name)

    def install(self, source: Path) -> Optional[Skill]:
        """从源码路径安装 Skill"""
        if not source.exists():
            logger.error(f"安装源路径不存在: {source}")
            return None
        if not (source / "main.py").exists():
            logger.error(f"安装源缺少 main.py: {source}")
            return None

        # 确定目标路径
        target_dir = Path("skills/user-installed") / source.name
        target_dir.mkdir(parents=True, exist_ok=True)

        # 复制文件
        try:
            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(source, target_dir)
            logger.info(f"📦 已复制 Skill 到 {target_dir}")
        except Exception as e:
            logger.error(f"复制 Skill 失败: {e}")
            return None

        # 加载
        skill = Skill(target_dir)
        self.skills[skill.manifest.name] = skill
        logger.info(f"✅ 已安装 Skill: {skill.manifest.name} v{skill.manifest.version}")
        return skill

    def uninstall(self, name: str) -> bool:
        """卸载 Skill"""
        skill = self.skills.pop(name, None)
        if not skill:
            logger.warning(f"Skill '{name}' 未找到")
            return False

        try:
            if skill.path.exists():
                shutil.rmtree(skill.path)
            logger.info(f"🗑️ 已卸载 Skill: {name}")
            return True
        except Exception as e:
            logger.error(f"卸载 Skill '{name}' 失败: {e}")
            # 即使文件删除失败也从内存移除
            return True

    def list_by_domain(self, domain: str) -> List[Skill]:
        """按操作域列出 Skill"""
        return [
            s for s in self.skills.values()
            if any(d.get("domain") == domain for d in s.manifest.domains)
        ]

    def list_enabled(self) -> List[Skill]:
        """列出所有启用的 Skill"""
        return [s for s in self.skills.values() if s.enabled]

    def count(self) -> int:
        """已安装 Skill 数量"""
        return len(self.skills)

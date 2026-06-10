"""版本契约——Skill 版本兼容性声明和回滚安全验证"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class VersionContract:
    """版本契约

    每个 Skill 声明它兼容的系统版本，回滚不再是"试试看"。
    在 SKILL.md 中用 compatible_with 字段声明。
    """

    def __init__(self, manifest: Dict[str, Any]):
        self.name = manifest.get("name", "unknown")
        self.version = manifest.get("version", "0.0.0")
        self.compatible_with = manifest.get("compatible_with", {})

    @classmethod
    def from_skill_dir(cls, skill_dir: Path) -> Optional["VersionContract"]:
        """从 Skill 目录加载版本契约"""
        manifest_path = skill_dir / "SKILL.md"
        if not manifest_path.exists():
            return None
        try:
            content = manifest_path.read_text(encoding="utf-8")
            parts = content.split("---")
            if len(parts) < 2:
                return None
            import yaml
            data = yaml.safe_load(parts[1])
            if not data:
                return None
            return cls(data)
        except Exception as e:
            logger.error(f"加载版本契约失败 ({skill_dir.name}): {e}")
            return None

    def can_rollback_to(self, target_contract: "VersionContract") -> Dict[str, Any]:
        """验证回滚到目标版本是否安全

        Returns:
            {
                "can_rollback": bool,
                "issues": [str],
                "migration_needed": bool,
            }
        """
        report = {
            "can_rollback": True,
            "issues": [],
            "migration_needed": False,
        }

        # 检查 API 版本兼容性
        current_api = self.compatible_with.get("api_version", "0.0.0")
        target_api = target_contract.compatible_with.get("api_version", "0.0.0")
        if current_api != target_api:
            report["issues"].append(
                f"API 版本不匹配: {target_api} → {current_api}"
            )
            report["can_rollback"] = False

        # 检查数据格式版本
        current_fmt = self.compatible_with.get("memory_format", "v1")
        target_fmt = target_contract.compatible_with.get("memory_format", "v1")
        if current_fmt != target_fmt:
            report["issues"].append(
                f"数据格式变化: {target_fmt} → {current_fmt}"
            )
            report["migration_needed"] = True
            # 有迁移脚本仍可回滚
            report["can_rollback"] = True

        # 检查系统版本
        current_sys = self.compatible_with.get("system", ">=0.1.0")
        target_sys = target_contract.compatible_with.get("system", ">=0.1.0")
        if current_sys != target_sys:
            report["issues"].append(
                f"系统版本要求变化: {target_sys} → {current_sys}"
            )

        return report

"""Skill fixtures — fake_skill() and skill_factory(profile=...) with 8 presets."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock
import pytest

from app.skill.runtime import Skill, SkillManifest


class FakeSkill(Skill):
    """Skill 的轻量替身，不加载文件系统。

    直接注入 manifest 和 mock handler，跳过 _load_manifest / _load_module。
    """

    def __init__(self, name: str = "test-skill", version: str = "1.0.0",
                 description: str = "A test skill",
                 domains: Optional[List[Dict]] = None,
                 priority: int = 50,
                 handler=None,
                 enabled: bool = True,
                 health_score: float = 1.0):
        # 不调用父类 __init__（避免文件系统操作）
        self.path = Path("/fake/path")
        self.manifest = SkillManifest(
            name=name, version=version, description=description,
            domains=domains or [], priority=priority,
        )
        self.module = None
        self.enabled = enabled
        self.health_score = health_score
        self.last_used = None
        self.execution_count = 0
        self._mock_handler = handler or AsyncMock(return_value={"ok": True})

    async def execute(self, intent: Dict, context: Dict = None) -> Dict:
        """覆写 execute 使用 mock handler。"""
        if not self.enabled:
            return {"error": "skill_disabled", "message": f"Skill '{self.manifest.name}' 已禁用"}
        if not self._mock_handler:
            return {"error": "no_handler", "message": "Skill 没有 handle 函数"}
        self.execution_count += 1
        self.last_used = __import__('datetime').datetime.now()
        try:
            result = self._mock_handler(intent, context or {})
            if __import__('inspect').isawaitable(result):
                result = await result
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_info(self) -> dict:
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


def skill_factory(profile: str = "normal",
                  overrides: Optional[Dict] = None) -> FakeSkill:
    """按预设模板创建 FakeSkill。

    Profiles:
        normal                — 标准合法 Skill
        missing_manifest      — 缺少 SKILL.md（用 FakeSkill 模拟）
        missing_main          — 缺少 main.py（模拟）
        crash                 — handle 执行抛异常
        conflict              — 与已有 Skill 域重叠（domains 含 "lighting"）
        incompatible_version  — 版本不兼容标记
        unhealthy             — 低健康度 (0.3)
    """
    if overrides is None:
        overrides = {}

    profile_map = {
        "normal": {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "A standard test skill",
            "domains": [{"domain": "lighting"}],
            "priority": 50,
        },
        "missing_manifest": {
            "name": "missing-manifest",
            "version": "0.0.0",
            "description": "",
            "domains": [],
            "priority": 50,
        },
        "missing_main": {
            "name": "missing-main",
            "version": "0.0.0",
            "description": "Skill without main.py",
            "domains": [],
            "priority": 50,
        },
        "crash": {
            "name": "crash-skill",
            "version": "1.0.0",
            "description": "Skill that crashes on execute",
            "domains": [{"domain": "lighting"}],
            "priority": 50,
            "handler": AsyncMock(side_effect=RuntimeError("intentional crash")),
        },
        "conflict": {
            "name": "conflict-skill",
            "version": "1.0.0",
            "description": "Skill with overlapping domain",
            "domains": [{"domain": "lighting"}],
            "priority": 50,
        },
        "incompatible_version": {
            "name": "incompatible-skill",
            "version": "99.0.0",
            "description": "Skill with incompatible version",
            "domains": [{"domain": "other"}],
            "priority": 50,
        },
        "unhealthy": {
            "name": "unhealthy-skill",
            "version": "1.0.0",
            "description": "Skill with low health",
            "domains": [{"domain": "lighting"}],
            "priority": 50,
            "health_score": 0.3,
        },
    }

    config = dict(profile_map.get(profile, profile_map["normal"]))
    config.update(overrides)
    return FakeSkill(**config)


@pytest.fixture
def fake_skill() -> FakeSkill:
    """返回一个标准 FakeSkill 实例。"""
    return skill_factory("normal")


@pytest.fixture
def crash_skill() -> FakeSkill:
    """返回一个执行时崩溃的 FakeSkill。"""
    return skill_factory("crash")

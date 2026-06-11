"""Integration: Install -> Load -> Execute chain."""
import pytest
from pathlib import Path
from app.skill.registry import SkillRegistry
from app.skill.runtime import Skill


@pytest.fixture
def real_skill_dir(tmp_path):
    d = tmp_path / "test-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: test-skill\nversion: 1.0.0\n---\n", encoding="utf-8"
    )
    (d / "main.py").write_text(
        "async def handle(intent, ctx): return {'ok': True, 'intent': intent.get('action')}\n",
        encoding="utf-8",
    )
    return d


class TestInstallLoadExecuteChain:
    """End-to-end chain: skill directory -> install -> load -> execute."""

    @pytest.mark.asyncio
    async def test_install_then_get(self, real_skill_dir):
        registry = SkillRegistry()
        skill = registry.install(real_skill_dir)
        assert skill is not None
        assert skill.manifest.name == "test-skill"
        assert registry.get("test-skill") is skill

    @pytest.mark.asyncio
    async def test_install_then_execute(self, real_skill_dir):
        registry = SkillRegistry()
        skill = registry.install(real_skill_dir)
        result = await skill.execute({"action": "turn_on"}, {})
        assert result.get("ok") is True
        assert result.get("intent") == "turn_on"

    @pytest.mark.asyncio
    async def test_double_install_overwrites(self, real_skill_dir):
        registry = SkillRegistry()
        registry.install(real_skill_dir)

        # Modify and create another version
        d2 = real_skill_dir.parent / "test-skill-v2"
        d2.mkdir()
        (d2 / "SKILL.md").write_text(
            "---\nname: test-skill\nversion: 2.0.0\n---\n", encoding="utf-8"
        )
        (d2 / "main.py").write_text(
            "async def handle(intent, ctx): return {'ok': True, 'version': '2.0.0'}\n",
            encoding="utf-8",
        )
        skill = registry.install(d2)
        assert skill.manifest.version == "2.0.0"
        result = await skill.execute({"action": "test"})
        assert result.get("version") == "2.0.0"

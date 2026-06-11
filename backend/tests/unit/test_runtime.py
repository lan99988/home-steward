"""Task 3: test_runtime.py — 21 tests for the Skill runtime.

Tests are organized into 4 layers:
  Layer A: Execute path tests (6 tests, mock-based)
  Layer B: Manifest loading tests (6 tests, tmp_path)
  Layer C: Module loading tests (6 tests, tmp_path)
  Layer D: Info + Reload tests (3 tests)
"""

import inspect
import logging
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from app.skill.runtime import Skill, SkillManifest


# =============================================================================
# Layer A: Execute path tests (6 tests, mock-based)
# =============================================================================
# These tests construct Skill objects via Skill.__new__(Skill) to avoid
# filesystem I/O, then manually set attributes and exercise the real
# Skill.execute() method.

class _FakeModule:
    """Minimal stand-in for a loaded Python module, exposing a handle attribute."""
    pass


@pytest.fixture
def mock_skill():
    """Create a Skill instance without calling __init__ (no file system access).

    All attributes are set manually. The returned Skill is "loaded" with a
    default async handler that returns {"ok": True, "result": "done"}.
    """
    s = Skill.__new__(Skill)
    s.path = Path("/fake/path")
    s.manifest = SkillManifest(name="test-skill", version="1.0.0")
    s.enabled = True
    s.health_score = 1.0
    s.last_used = None
    s.execution_count = 0

    mod = _FakeModule()
    async def handle(intent, context):
        return {"ok": True, "result": "done"}
    mod.handle = handle
    s.module = mod
    return s


class TestExecutePaths:
    """Layer A: The 6 execution paths through Skill.execute()."""

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_skill):
        """Normal execution returns the handler result."""
        result = await mock_skill.execute({"intent": "test"})
        assert result == {"ok": True, "result": "done"}
        assert mock_skill.execution_count == 1
        assert mock_skill.last_used is not None

    @pytest.mark.asyncio
    async def test_execute_disabled_skill(self, mock_skill):
        """enabled=False returns skill_disabled error."""
        mock_skill.enabled = False
        result = await mock_skill.execute({"intent": "test"})
        assert result["error"] == "skill_disabled"
        assert mock_skill.execution_count == 0  # not incremented

    @pytest.mark.asyncio
    async def test_execute_no_module(self, mock_skill):
        """module=None returns no_module error."""
        mock_skill.module = None
        result = await mock_skill.execute({"intent": "test"})
        assert result["error"] == "no_module"
        assert mock_skill.execution_count == 0

    @pytest.mark.asyncio
    async def test_execute_no_handler(self, mock_skill):
        """Module without a 'handle' attribute returns no_handler error."""
        mod = _FakeModule()
        # deliberately no handle attribute
        mock_skill.module = mod
        result = await mock_skill.execute({"intent": "test"})
        assert result["error"] == "no_handler"
        assert mock_skill.execution_count == 0

    @pytest.mark.asyncio
    async def test_execute_handler_exception(self, mock_skill):
        """Handler raising an exception returns {"error": str(e)}."""
        mod = _FakeModule()
        async def broken_handler(intent, ctx):
            raise RuntimeError("something broke")
        mod.handle = broken_handler
        mock_skill.module = mod

        result = await mock_skill.execute({"intent": "test"})
        assert result["error"] == "something broke"
        # execution_count IS incremented before the handler runs
        assert mock_skill.execution_count == 1

    @pytest.mark.asyncio
    async def test_execute_handler_returns_non_awaitable(self, mock_skill):
        """Sync (non-async) handler raises TypeError, caught and returned as error.

        The real Skill.execute() does `await handler(...)` without an
        inspect.isawaitable() guard.  Awaiting a sync function raises TypeError,
        which is a subclass of Exception and is caught by the except clause.
        """
        mod = _FakeModule()
        def sync_handler(intent, ctx):
            return {"sync": True}
        mod.handle = sync_handler
        mock_skill.module = mod

        result = await mock_skill.execute({"intent": "test"})
        # TypeError is caught by except Exception, returned as error string
        assert "error" in result
        assert "await" in result["error"]
        assert mock_skill.execution_count == 1


# =============================================================================
# Layer B: Manifest loading tests (6 tests, tmp_path)
# =============================================================================

class TestManifestLoading:
    """Layer B: Tests for _load_manifest() with real files on tmp_path."""

    @pytest.fixture
    def skill_dir(self, tmp_path):
        """Create a skill directory under tmp_path."""
        d = tmp_path / "test-skill"
        d.mkdir()
        return d

    def test_load_valid_manifest(self, skill_dir):
        """Valid YAML frontmatter in SKILL.md is parsed correctly."""
        sk_md = """---
name: my-skill
version: 2.0.0
description: A test skill
domains:
  - domain: lighting
priority: 80
conflict_resolution: ask_user
compatible_with:
  platform: ">=1.0"
---
Some documentation here.
"""
        (skill_dir / "SKILL.md").write_text(sk_md, encoding="utf-8")
        # Also create a stub main.py so Skill.__init__ doesn't log warnings
        (skill_dir / "main.py").write_text("", encoding="utf-8")

        skill = Skill(skill_dir)
        assert skill.manifest.name == "my-skill"
        assert skill.manifest.version == "2.0.0"
        assert skill.manifest.description == "A test skill"
        assert skill.manifest.domains == [{"domain": "lighting"}]
        assert skill.manifest.priority == 80
        assert skill.manifest.conflict_resolution == "ask_user"
        assert skill.manifest.compatible_with == {"platform": ">=1.0"}

    def test_missing_skill_md(self, skill_dir, caplog):
        """Missing SKILL.md falls back to directory name and logs a warning."""
        # No SKILL.md at all
        (skill_dir / "main.py").write_text("", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            skill = Skill(skill_dir)

        assert skill.manifest.name == "test-skill"
        assert skill.manifest.version == "1.0.0"  # default
        assert "缺少 SKILL.md" in caplog.text

    def test_invalid_yaml(self, skill_dir, caplog):
        """Malformed YAML frontmatter falls back gracefully."""
        (skill_dir / "SKILL.md").write_text("---\nname: foo\n  invalid_yaml: true\n---", encoding="utf-8")
        (skill_dir / "main.py").write_text("", encoding="utf-8")

        with caplog.at_level(logging.ERROR):
            skill = Skill(skill_dir)

        # Falls back to dir name
        assert skill.manifest.name == "test-skill"
        assert "失败" in caplog.text or "解析" in caplog.text

    def test_missing_required_manifest_field(self, skill_dir):
        """Empty frontmatter (just '---') returns default manifest."""
        (skill_dir / "SKILL.md").write_text("---\n---\n", encoding="utf-8")
        (skill_dir / "main.py").write_text("", encoding="utf-8")

        skill = Skill(skill_dir)
        assert skill.manifest.name == "test-skill"
        assert skill.manifest.version == "1.0.0"
        assert skill.manifest.description == ""

    def test_utf8_manifest(self, skill_dir):
        """Chinese characters in UTF-8 SKILL.md are handled."""
        content = """---
name: 中文技能
version: 1.0.0
description: 这是一个测试技能
---
# 文档内容
"""
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        (skill_dir / "main.py").write_text("", encoding="utf-8")

        skill = Skill(skill_dir)
        assert skill.manifest.name == "中文技能"
        assert skill.manifest.description == "这是一个测试技能"

    def test_non_utf8_manifest(self, skill_dir):
        """GBK-encoded file raises UnicodeDecodeError (not caught).

        Note: The current _load_manifest() implementation calls
        read_text(encoding='utf-8') *outside* the try/except block, so a
        non-UTF-8 file propagates UnicodeDecodeError to the caller.
        The design spec recommends wrapping read_text() in a try/except
        for robustness.
        """
        gbk_bytes = (
            b"---\nname: gbk-\xb2\xe2\xca\xd4\nversion: 1.0.0\n---\n"
        )
        (skill_dir / "SKILL.md").write_bytes(gbk_bytes)
        (skill_dir / "main.py").write_text("", encoding="utf-8")

        with pytest.raises(UnicodeDecodeError):
            Skill(skill_dir)


# =============================================================================
# Layer C: Module loading tests (6 tests, tmp_path)
# =============================================================================

class TestModuleLoading:
    """Layer C: Tests for _load_module() with real .py files on tmp_path."""

    @pytest.fixture
    def skill_dir(self, tmp_path):
        d = tmp_path / "module-skill"
        d.mkdir()
        # Always write a minimal SKILL.md so manifest loading doesn't interfere
        (d / "SKILL.md").write_text("---\nname: module-skill\n---\n", encoding="utf-8")
        return d

    def test_load_valid_main_py(self, skill_dir):
        """Valid main.py with an async handle function loads and runs."""
        code = """
async def handle(intent, context):
    return {"ok": True, "from_module": intent.get("key")}
"""
        (skill_dir / "main.py").write_text(code, encoding="utf-8")

        skill = Skill(skill_dir)
        assert skill.module is not None
        assert hasattr(skill.module, "handle")
        assert inspect.iscoroutinefunction(skill.module.handle)

    def test_missing_main_py(self, skill_dir, caplog):
        """No main.py → module is None, warning logged."""
        with caplog.at_level(logging.WARNING):
            skill = Skill(skill_dir)

        assert skill.module is None
        assert "缺少 main.py" in caplog.text

    def test_import_error_in_main_py(self, skill_dir, caplog):
        """Import of a nonexistent package is caught, module set to None."""
        code = """
import nonexistent_package_xyz123

async def handle(intent, context):
    return {"ok": True}
"""
        (skill_dir / "main.py").write_text(code, encoding="utf-8")

        with caplog.at_level(logging.ERROR):
            skill = Skill(skill_dir)

        assert skill.module is None
        assert "失败" in caplog.text or "Error" in caplog.text or "error" in caplog.text

    def test_syntax_error_in_main_py(self, skill_dir, caplog):
        """Broken Python syntax is caught, module set to None."""
        code = """def broken syntax{{{{
"""
        (skill_dir / "main.py").write_text(code, encoding="utf-8")

        with caplog.at_level(logging.ERROR):
            skill = Skill(skill_dir)

        assert skill.module is None

    def test_module_without_handle(self, skill_dir):
        """Module loads but has no handle function."""
        code = """
async def some_other_func():
    pass
"""
        (skill_dir / "main.py").write_text(code, encoding="utf-8")

        skill = Skill(skill_dir)
        assert skill.module is not None
        assert not hasattr(skill.module, "handle")

    def test_handle_not_async(self, skill_dir):
        """Sync handle function loads but execute() will fail with TypeError.

        The Skill.execute() method does not guard with inspect.isawaitable(),
        so awaiting a sync function raises TypeError (caught by the except
        clause and returned as an error dict).
        """
        code = """
def handle(intent, context):
    return {"sync": True}
"""
        (skill_dir / "main.py").write_text(code, encoding="utf-8")

        skill = Skill(skill_dir)
        assert skill.module is not None
        assert hasattr(skill.module, "handle")
        assert not inspect.iscoroutinefunction(skill.module.handle)


# =============================================================================
# Layer D: Info + Reload tests (3 tests)
# =============================================================================

class TestInfoAndReload:
    """Layer D: get_info() completeness and reload behavior."""

    def test_get_info_complete(self, tmp_path):
        """All fields populated: get_info returns every expected key."""
        d = tmp_path / "info-skill"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\nname: info-skill\nversion: 3.0.0\n"
            "description: Full skill\ndomains:\n  - domain: all\n"
            "priority: 90\n---\n",
            encoding="utf-8",
        )
        (d / "main.py").write_text(
            "async def handle(i, c): return {'ok': True}", encoding="utf-8"
        )

        skill = Skill(d)
        info = skill.get_info()

        assert info["name"] == "info-skill"
        assert info["version"] == "3.0.0"
        assert info["description"] == "Full skill"
        assert info["priority"] == 90
        assert info["domains"] == [{"domain": "all"}]
        assert info["enabled"] is True
        assert info["health_score"] == 1.0
        assert info["execution_count"] == 0

    def test_get_info_partial_manifest(self, tmp_path):
        """Minimal manifest returns sensible defaults in get_info."""
        d = tmp_path / "minimal-skill"
        d.mkdir()
        # Only the "name" field is set (fallback to dir name when SKILL.md
        # isn't present)
        (d / "main.py").write_text(
            "async def handle(i, c): return {'ok': True}", encoding="utf-8"
        )

        skill = Skill(d)
        info = skill.get_info()

        assert info["name"] == "minimal-skill"
        assert info["version"] == "1.0.0"  # default
        assert info["description"] == ""    # default
        assert info["priority"] == 50       # default
        assert info["domains"] == []        # default
        assert info["enabled"] is True
        assert info["health_score"] == 1.0

    def test_reload_after_file_change(self, tmp_path):
        """Change SKILL.md version on disk, create new Skill, verify updated.

        Note: Skill.__init__ loads data once.  To "reload" we create a new
        Skill instance pointing at the same directory.  This simulates what the
        registry does when a reload is triggered.
        """
        d = tmp_path / "reload-skill"
        d.mkdir()

        # Phase 1: create with version 1.0.0
        (d / "SKILL.md").write_text(
            "---\nname: reload-skill\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )
        (d / "main.py").write_text(
            "async def handle(i, c): return {'ok': True}", encoding="utf-8"
        )

        skill_v1 = Skill(d)
        assert skill_v1.manifest.version == "1.0.0"

        # Phase 2: update SKILL.md on disk
        (d / "SKILL.md").write_text(
            "---\nname: reload-skill\nversion: 2.5.0\n---\n",
            encoding="utf-8",
        )

        # Phase 3: create a new Skill instance — it should pick up the change
        skill_v2 = Skill(d)
        assert skill_v2.manifest.version == "2.5.0"

        # The old instance is not affected
        assert skill_v1.manifest.version == "1.0.0"

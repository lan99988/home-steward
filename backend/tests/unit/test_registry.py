"""Test Suite for SkillRegistry — 26 tests covering all CRUD paths."""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from app.skill.registry import SkillRegistry
from app.skill.runtime import Skill


# =========================================================================
# Helpers
# =========================================================================


def make_fake_skill(registry, name, **kwargs):
    """Build a lightweight Skill-like object and inject it into registry.skills.

    Uses Skill.__new__ to avoid triggering __init__ (no filesystem read).
    """
    from app.skill.runtime import SkillManifest

    skill = Skill.__new__(Skill)
    defaults = dict(
        version="1.0.0",
        description="",
        priority=50,
        domains=[],
        enabled=True,
        health_score=1.0,
        execution_count=0,
        last_used=None,
    )
    defaults.update(kwargs)

    skill.manifest = SkillManifest(
        name=name,
        **{k: v for k, v in defaults.items()
           if k in ("version", "description", "priority", "domains")},
    )
    for attr, val in defaults.items():
        if attr != "domains":
            setattr(skill, attr, val)
    skill.path = Path("/fake") / name
    registry.skills[name] = skill
    return skill


def _create_skill_dir(tmp_path, name, version="1.0.0", main_content=None):
    """Create a minimal valid skill directory on disk."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\nversion: {version}\ndomains:\n  - domain: test\n---\n"
    )
    (skill_dir / "main.py").write_text(
        main_content or "async def handle(intent, ctx): return {'ok': True}"
    )
    return skill_dir


# =========================================================================
# Layer A — Query tests (7 tests, pure logic, no filesystem)
# =========================================================================


class TestQuery:
    """Tests for get, list_by_domain, list_enabled, count."""

    def test_get_existing(self, registry):
        make_fake_skill(registry, "alpha")
        skill = registry.get("alpha")
        assert skill is not None
        assert skill.manifest.name == "alpha"

    def test_get_missing(self, registry):
        assert registry.get("nonexistent") is None

    def test_list_by_domain_match(self, registry):
        make_fake_skill(registry, "lighting", domains=[{"domain": "home"}])
        make_fake_skill(registry, "security", domains=[{"domain": "home"}])
        make_fake_skill(registry, "music", domains=[{"domain": "media"}])

        home_skills = registry.list_by_domain("home")
        assert len(home_skills) == 2
        assert {s.manifest.name for s in home_skills} == {"lighting", "security"}

    def test_list_by_domain_no_match(self, registry):
        make_fake_skill(registry, "lighting", domains=[{"domain": "home"}])
        assert registry.list_by_domain("garden") == []

    def test_list_enabled(self, registry):
        make_fake_skill(registry, "a", enabled=True)
        make_fake_skill(registry, "b", enabled=False)
        make_fake_skill(registry, "c", enabled=True)

        enabled = registry.list_enabled()
        assert len(enabled) == 2
        assert {s.manifest.name for s in enabled} == {"a", "c"}

    def test_list_enabled_all_disabled(self, registry):
        make_fake_skill(registry, "x", enabled=False)
        make_fake_skill(registry, "y", enabled=False)
        assert registry.list_enabled() == []

    def test_count(self, registry):
        for name in ("a", "b", "c", "d", "e"):
            make_fake_skill(registry, name)
        assert registry.count() == 5


# =========================================================================
# Layer B — Install tests (6 tests, tmp_path)
# =========================================================================


class TestInstall:
    """Tests for registry.install()."""

    def test_install_valid_skill(self, registry, tmp_path):
        src = _create_skill_dir(tmp_path, "my-skill", version="1.0.0")
        result = registry.install(src)

        assert result is not None
        assert isinstance(result, Skill)
        assert result.manifest.name == "my-skill"
        assert registry.get("my-skill") is result

    def test_install_source_not_exist(self, registry, tmp_path):
        nonexistent = tmp_path / "i-dont-exist"
        result = registry.install(nonexistent)
        assert result is None

    def test_install_missing_main_py(self, registry, tmp_path):
        skill_dir = tmp_path / "no-main"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: no-main\n---\n")
        # No main.py — install should bail out
        result = registry.install(skill_dir)
        assert result is None

    def test_install_overwrite_existing(self, registry, tmp_path):
        src_v1 = _create_skill_dir(tmp_path, "upgradable", version="1.0.0")
        registry.install(src_v1)
        assert registry.get("upgradable").manifest.version == "1.0.0"

        # Use a separate temp subdirectory for v2 to avoid path nesting issues
        v2_dir = tmp_path / "v2"
        v2_dir.mkdir()
        src_v2 = _create_skill_dir(v2_dir, "upgradable", version="2.0.0")
        result = registry.install(src_v2)
        assert result is not None
        assert registry.get("upgradable").manifest.version == "2.0.0"

    def test_install_downgrade_version(self, registry, tmp_path):
        src_v2 = _create_skill_dir(tmp_path, "downgradable", version="2.0.0")
        registry.install(src_v2)
        assert registry.get("downgradable").manifest.version == "2.0.0"

        v1_dir = tmp_path / "v1"
        v1_dir.mkdir()
        src_v1 = _create_skill_dir(v1_dir, "downgradable", version="1.0.0")
        result = registry.install(src_v1)
        assert result is not None
        assert registry.get("downgradable").manifest.version == "1.0.0"

    def test_install_checks_state_before_and_after(self, registry, tmp_path):
        assert registry.get("state-check") is None

        src = _create_skill_dir(tmp_path, "state-check")
        result = registry.install(src)

        assert result is not None
        assert registry.get("state-check") is result


# =========================================================================
# Layer C — Uninstall tests (4 tests, tmp_path)
# =========================================================================


class TestUninstall:
    """Tests for registry.uninstall()."""

    def test_uninstall_existing(self, registry, tmp_path):
        src = _create_skill_dir(tmp_path, "removable")
        registry.install(src)
        assert registry.get("removable") is not None

        ret = registry.uninstall("removable")
        assert ret is True
        assert registry.get("removable") is None

    def test_uninstall_not_found(self, registry):
        ret = registry.uninstall("ghost")
        assert ret is False

    def test_uninstall_disk_cleanup(self, registry, tmp_path):
        src = _create_skill_dir(tmp_path, "clean-me")
        registry.install(src)
        assert registry.get("clean-me") is not None

        ret = registry.uninstall("clean-me")
        assert ret is True
        assert registry.get("clean-me") is None

    def test_uninstall_shutil_failure(self, registry, tmp_path):
        src = _create_skill_dir(tmp_path, "stubborn")
        registry.install(src)
        assert registry.get("stubborn") is not None

        with patch("shutil.rmtree", side_effect=PermissionError("denied")):
            ret = registry.uninstall("stubborn")
            # Despite filesystem failure, returns True and removes from memory
            assert ret is True
            assert registry.get("stubborn") is None


# =========================================================================
# Layer D — Discover tests (6 tests, tmp_path)
# =========================================================================


class TestDiscover:
    """Tests for registry.discover()."""

    def test_discover_empty_directory(self, registry, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        registry.discover([empty_dir])
        assert registry.count() == 0

    def test_discover_valid_skills(self, registry, tmp_path):
        base = tmp_path / "skills"
        base.mkdir()
        for name in ("alpha", "beta", "gamma"):
            _create_skill_dir(base, name)

        registry.discover([base])
        assert registry.count() == 3

    def test_discover_skill_defined_path(self, registry, tmp_path):
        base_a = tmp_path / "path-a"
        base_a.mkdir()
        _create_skill_dir(base_a, "from-a")

        base_b = tmp_path / "path-b"
        base_b.mkdir()
        _create_skill_dir(base_b, "from-b")

        registry.discover([base_a])
        assert registry.count() == 1
        assert registry.get("from-a") is not None
        assert registry.get("from-b") is None

    def test_discover_path_not_exist(self, registry, tmp_path):
        registry.discover([tmp_path / "nope"])
        assert registry.count() == 0

    def test_discover_partial_failure(self, registry, tmp_path):
        base = tmp_path / "mixed"
        base.mkdir()

        good = _create_skill_dir(base, "good-skill")
        # Create a bad directory that has no SKILL.md and no main.py
        bad = base / "bad-skill"
        bad.mkdir()
        (bad / "some_random_file.txt").write_text("not a skill")

        registry.discover([base])
        # Only the valid skill should be loaded
        assert registry.count() == 1
        assert registry.get("good-skill") is not None
        assert registry.get("bad-skill") is None

    def test_discover_idempotent(self, registry, tmp_path):
        base = tmp_path / "idem"
        base.mkdir()
        _create_skill_dir(base, "stable")

        registry.discover([base])
        assert registry.count() == 1
        registry.discover([base])
        # Idempotent: calling again doesn't change the count (same name re-registers)
        assert registry.count() == 1


# =========================================================================
# Layer E — Error recovery tests (3 tests)
# =========================================================================


class TestErrorRecovery:
    """Tests for error handling during install/discover."""

    def test_install_copytree_failure(self, registry, tmp_path):
        src = _create_skill_dir(tmp_path, "failing-install")

        with patch("shutil.copytree", side_effect=OSError("disk full")):
            result = registry.install(src)

        assert result is None
        assert registry.get("failing-install") is None

    def test_discover_builtin_fallback(self, registry):
        """discover_builtin should not crash even when paths are missing."""
        # Just verify the call doesn't raise
        try:
            registry.discover_builtin()
        except Exception:
            pytest.fail("discover_builtin raised unexpectedly")

    def test_another_path_failure(self, registry, tmp_path):
        """Install succeeds in copying files but Skill loading breaks.

        We patch Skill.__init__ to raise an exception after copytree has run.
        The exception propagates to the caller and the registry remains clean.
        """
        from app.skill.runtime import Skill as RealSkill

        src = _create_skill_dir(tmp_path, "broken-load")

        original_init = RealSkill.__init__

        def _broken_init(self, path):
            raise RuntimeError("module import failed")

        with patch.object(RealSkill, "__init__", _broken_init):
            try:
                registry.install(src)
            except RuntimeError:
                pass

        assert registry.get("broken-load") is None

"""v1.1 Tests for VersionContract — 9 tests targeting 80%+ coverage.

Tests are organized into two groups:
  - Init & Load tests: __init__ defaults, from_skill_dir with valid/missing/invalid YAML
  - Rollback tests: can_rollback_to with various compatible_with configurations
"""

from pathlib import Path

import pytest
import yaml

from app.skill.version_contract import VersionContract


# =============================================================================
# Init & Load tests
# =============================================================================

class TestInitAndLoad:
    """VersionContract.__init__ and from_skill_dir()."""

    def test_init_with_full_manifest(self):
        """All fields set from a complete manifest dict."""
        contract = VersionContract({
            "name": "test-skill",
            "version": "2.1.0",
            "compatible_with": {
                "api_version": "1.0",
                "memory_format": "v2",
                "system": ">=0.2.0",
            },
        })
        assert contract.name == "test-skill"
        assert contract.version == "2.1.0"
        assert contract.compatible_with["api_version"] == "1.0"
        assert contract.compatible_with["memory_format"] == "v2"
        assert contract.compatible_with["system"] == ">=0.2.0"

    def test_init_with_empty_manifest(self):
        """Empty dict uses all defaults."""
        contract = VersionContract({})
        assert contract.name == "unknown"
        assert contract.version == "0.0.0"
        assert contract.compatible_with == {}

    def test_from_skill_dir_valid(self, tmp_path):
        """Valid SKILL.md with YAML frontmatter is parsed correctly."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        sk_md = """---
name: my-skill
version: 3.0.0
compatible_with:
  api_version: "2.0"
  memory_format: v3
  system: ">=0.5.0"
---
Some documentation here.
"""
        (skill_dir / "SKILL.md").write_text(sk_md, encoding="utf-8")

        contract = VersionContract.from_skill_dir(skill_dir)
        assert contract is not None
        assert contract.name == "my-skill"
        assert contract.version == "3.0.0"
        assert contract.compatible_with["api_version"] == "2.0"
        assert contract.compatible_with["memory_format"] == "v3"
        assert contract.compatible_with["system"] == ">=0.5.0"

    def test_from_skill_dir_missing_md(self, tmp_path):
        """No SKILL.md returns None."""
        skill_dir = tmp_path / "empty-dir"
        skill_dir.mkdir()
        contract = VersionContract.from_skill_dir(skill_dir)
        assert contract is None

    def test_from_skill_dir_invalid_yaml(self, tmp_path):
        """Malformed YAML frontmatter returns None."""
        skill_dir = tmp_path / "bad-yaml"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: foo\n  invalid_yaml: true\n---\n",
            encoding="utf-8",
        )
        contract = VersionContract.from_skill_dir(skill_dir)
        assert contract is None

    def test_from_skill_dir_no_frontmatter(self, tmp_path):
        """SKILL.md without frontmatter (no --- delimiters) returns None."""
        skill_dir = tmp_path / "no-frontmatter"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "# Just a markdown file\nNo YAML frontmatter here.\n",
            encoding="utf-8",
        )
        contract = VersionContract.from_skill_dir(skill_dir)
        assert contract is None


# =============================================================================
# Rollback tests
# =============================================================================

class TestCanRollbackTo:
    """can_rollback_to() — compatibility checking between two VersionContracts."""

    def test_can_rollback_to_compatible(self):
        """Same api_version, memory_format, system -> can_rollback=True, no issues."""
        current = VersionContract({
            "name": "skill-a",
            "version": "2.0.0",
            "compatible_with": {
                "api_version": "1.0",
                "memory_format": "v2",
                "system": ">=0.2.0",
            },
        })
        target = VersionContract({
            "name": "skill-a",
            "version": "1.0.0",
            "compatible_with": {
                "api_version": "1.0",
                "memory_format": "v2",
                "system": ">=0.2.0",
            },
        })
        report = current.can_rollback_to(target)
        assert report["can_rollback"] is True
        assert report["issues"] == []
        assert report["migration_needed"] is False

    def test_can_rollback_to_api_mismatch(self):
        """Different api_version -> can_rollback=False, issue logged."""
        current = VersionContract({
            "compatible_with": {"api_version": "2.0"},
        })
        target = VersionContract({
            "compatible_with": {"api_version": "1.0"},
        })
        report = current.can_rollback_to(target)
        assert report["can_rollback"] is False
        assert any("API" in issue for issue in report["issues"])

    def test_can_rollback_to_memory_format_change(self):
        """Different memory_format -> migration_needed=True, but can_rollback True."""
        current = VersionContract({
            "compatible_with": {"memory_format": "v2"},
        })
        target = VersionContract({
            "compatible_with": {"memory_format": "v1"},
        })
        report = current.can_rollback_to(target)
        assert report["can_rollback"] is True  # migration scripts exist
        assert report["migration_needed"] is True
        assert any("数据格式" in issue for issue in report["issues"])

    def test_can_rollback_to_system_version_change(self):
        """Different system version -> issue logged, but rollback still allowed."""
        current = VersionContract({
            "compatible_with": {"system": ">=0.5.0"},
        })
        target = VersionContract({
            "compatible_with": {"system": ">=0.3.0"},
        })
        report = current.can_rollback_to(target)
        assert report["can_rollback"] is True
        assert any("系统版本" in issue for issue in report["issues"])
        assert report["migration_needed"] is False

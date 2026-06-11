"""Integration: VersionContract backward compatibility checks."""
import pytest
from pathlib import Path
from app.skill.version_contract import VersionContract
from app.skill.runtime import Skill


class TestBackwardCompatibility:
    """Version compatibility detection chain."""

    def test_compatible_versions(self):
        v1 = VersionContract({
            "name": "skill",
            "compatible_with": {"api_version": "1.0"}
        })
        v2 = VersionContract({
            "name": "skill",
            "compatible_with": {"api_version": "1.0"}
        })
        report = v1.can_rollback_to(v2)
        assert report["can_rollback"] is True
        assert report["issues"] == []

    def test_incompatible_api_version(self):
        v1 = VersionContract({
            "name": "skill",
            "compatible_with": {"api_version": "2.0"}
        })
        v2 = VersionContract({
            "name": "skill",
            "compatible_with": {"api_version": "1.0"}
        })
        report = v1.can_rollback_to(v2)
        assert report["can_rollback"] is False
        assert any("API" in i for i in report["issues"])

    def test_memory_format_migration(self, tmp_path):
        v1 = VersionContract({
            "name": "skill",
            "compatible_with": {"api_version": "1.0", "memory_format": "v2"}
        })
        v2 = VersionContract({
            "name": "skill",
            "compatible_with": {"api_version": "1.0", "memory_format": "v1"}
        })
        report = v1.can_rollback_to(v2)
        assert report["migration_needed"] is True
        assert report["can_rollback"] is True  # Migration possible

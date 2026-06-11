"""Tests for SkillEcosystem — skill count limits, archive, merge suggestions."""

from datetime import datetime, timedelta

import pytest

from app.skill.ecosystem import SkillEcosystem
from tests.fixtures.skill_factory import FakeSkill, skill_factory


def skill(name: str, domain: str = "lighting") -> FakeSkill:
    """Helper: create a FakeSkill with a single domain."""
    return FakeSkill(
        name=name,
        domains=[{"domain": domain}],
    )


class TestCanInstall:
    def test_can_install_within_limit(self):
        """10 active + 1 new <= 20 → True."""
        eco = SkillEcosystem()
        eco.load_active({f"s{i}": skill(f"s{i}") for i in range(10)})

        assert eco.can_install(new_count=1) is True

    def test_can_install_at_limit(self):
        """19 active + 2 new = 21 > 20 → False."""
        eco = SkillEcosystem()
        eco.load_active({f"s{i}": skill(f"s{i}") for i in range(19)})

        assert eco.can_install(new_count=2) is False

    def test_can_install_exactly_at_max(self):
        """20 active → False (no room at all)."""
        eco = SkillEcosystem()
        eco.load_active({f"s{i}": skill(f"s{i}") for i in range(20)})

        assert eco.can_install() is False


class TestSuggestMerge:
    def test_suggest_merge_no_overlap(self):
        """Different domains → empty list."""
        eco = SkillEcosystem()
        eco.load_active({
            "light": skill("light", domain="lighting"),
            "temp": skill("temp", domain="climate"),
        })

        assert eco.suggest_merge() == []

    def test_suggest_merge_with_overlap(self):
        """Overlapping domains → one suggestion."""
        eco = SkillEcosystem()
        eco.load_active({
            "light-a": skill("light-a", domain="lighting"),
            "light-b": skill("light-b", domain="lighting"),
        })
        suggestions = eco.suggest_merge()

        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["skill_a"] == "light-a"
        assert s["skill_b"] == "light-b"
        assert s["overlap"] == "lighting"


class TestArchiveUnused:
    def test_archive_unused_skill(self):
        """Skill with last_used=None and execution_count=0 → archived."""
        eco = SkillEcosystem()
        s = FakeSkill(name="unused-skill", domains=[{"domain": "test"}])
        s.last_used = None
        s.execution_count = 0
        eco.load_active({"unused": s})

        eco.archive_unused()

        assert "unused" not in eco.active_skills
        assert "unused" in eco.archived_skills

    def test_archive_unused_recently_used(self):
        """Skill used yesterday → NOT archived."""
        eco = SkillEcosystem()
        s = FakeSkill(name="recent-skill", domains=[{"domain": "test"}])
        s.last_used = datetime.now() - timedelta(days=1)
        s.execution_count = 5
        eco.load_active({"recent": s})

        eco.archive_unused()

        assert "recent" in eco.active_skills
        assert "recent" not in eco.archived_skills

    def test_archive_unused_multiple(self):
        """Multiple unused skills all get archived."""
        eco = SkillEcosystem()
        skills = {}
        for i in range(3):
            s = FakeSkill(name=f"unused-{i}", domains=[{"domain": "test"}])
            s.last_used = None
            s.execution_count = 0
            skills[f"u{i}"] = s
        eco.load_active(skills)

        eco.archive_unused()

        assert len(eco.active_skills) == 0
        assert len(eco.archived_skills) == 3


class TestRestoreFromArchive:
    def test_restore_from_archive(self):
        """Archived skill comes back to active."""
        eco = SkillEcosystem()
        s = FakeSkill(name="archived-skill", domains=[{"domain": "test"}])
        eco.archived_skills["archived"] = s

        restored = eco.restore_from_archive("archived")

        assert restored is s
        assert "archived" in eco.active_skills
        assert "archived" not in eco.archived_skills

    def test_restore_nonexistent(self):
        """Non-existent name → None, no side effects."""
        eco = SkillEcosystem()
        assert eco.restore_from_archive("ghost") is None
        assert len(eco.active_skills) == 0


class TestGetStats:
    def test_get_stats(self):
        """Stats dict has expected keys and values."""
        eco = SkillEcosystem()
        eco.load_active({
            "a": skill("a"),
            "b": skill("b"),
        })
        eco.archived_skills["old"] = skill("old")

        stats = eco.get_stats()

        assert stats == {
            "active": 2,
            "archived": 1,
            "max": 20,
            "remaining": 18,
        }


class TestLoadActive:
    def test_load_active(self):
        """load_active replaces active_skills."""
        eco = SkillEcosystem()
        s = skill("loaded")
        eco.load_active({"loaded": s})

        assert eco.active_skills == {"loaded": s}


class TestDomainOverlap:
    def test_domain_overlap_matching(self):
        """Same domain → returns the domain string."""
        eco = SkillEcosystem()
        a = FakeSkill(name="a", domains=[{"domain": "power"}, {"domain": "lighting"}])
        b = FakeSkill(name="b", domains=[{"domain": "lighting"}, {"domain": "climate"}])

        result = eco._domain_overlap(a, b)

        assert result == "lighting"

    def test_domain_overlap_no_match(self):
        """No shared domain → None."""
        eco = SkillEcosystem()
        a = FakeSkill(name="a", domains=[{"domain": "power"}])
        b = FakeSkill(name="b", domains=[{"domain": "climate"}])

        assert eco._domain_overlap(a, b) is None

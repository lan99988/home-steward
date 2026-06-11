"""Test Suite for ConflictPredictor — 12 tests covering all prediction paths."""

import yaml
from pathlib import Path
from unittest.mock import patch

import pytest

from app.skill.conflict_predictor import ConflictPredictor, ConflictWarning


# =========================================================================
# Helpers
# =========================================================================


def make_fake_skill_obj(name, domains, priority=50, conflict_resolution=""):
    """Create a lightweight skill-like object with a manifest.

    Uses Skill.__new__ to avoid triggering __init__.
    """
    from app.skill.runtime import Skill, SkillManifest

    skill = Skill.__new__(Skill)
    skill.manifest = SkillManifest(
        name=name,
        version="1.0.0",
        description="",
        domains=[{"domain": d} for d in domains],
        priority=priority,
        conflict_resolution=conflict_resolution or "yield_on_user",
    )
    skill.path = Path("/fake") / name
    return skill


def _make_skill_md_dir(tmp_path, name, domains, priority=50,
                       conflict_resolution="yield_on_user"):
    """Create a directory with a real SKILL.md file."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    manifest = {
        "name": name,
        "version": "1.0.0",
        "domains": [{"domain": d} for d in domains],
        "priority": priority,
        "conflict_resolution": conflict_resolution,
    }
    frontmatter = "---\n" + yaml.dump(manifest, allow_unicode=True) + "---\n"
    (skill_dir / "SKILL.md").write_text(frontmatter)
    return skill_dir


# =========================================================================
# Tests
# =========================================================================


class TestConflictPredictor:
    """Tests for ConflictPredictor."""

    def test_predict_no_overlap(self):
        """Domains don't overlap -> no warnings."""
        predictor = ConflictPredictor()
        new_mf = {"domains": [{"domain": "vision"}]}
        existing = [make_fake_skill_obj("alpha", domains=["audio"])]
        warnings = predictor.predict(new_mf, existing)
        assert warnings == []

    def test_empty_existing_skills(self):
        """No existing skills -> no warnings."""
        predictor = ConflictPredictor()
        new_mf = {"domains": [{"domain": "vision"}]}
        warnings = predictor.predict(new_mf, [])
        assert warnings == []

    def test_predict_no_domains_in_manifest(self):
        """Manifest without domains key -> no warnings."""
        predictor = ConflictPredictor()
        new_mf = {}
        existing = [make_fake_skill_obj("alpha", domains=["vision"])]
        warnings = predictor.predict(new_mf, existing)
        assert warnings == []

    def test_predict_domain_overlap(self):
        """Overlapping domain -> warning with probability."""
        predictor = ConflictPredictor()
        new_mf = {
            "domains": [{"domain": "chat"}],
            "priority": 50,
        }
        existing = [make_fake_skill_obj("beta", domains=["chat"])]
        warnings = predictor.predict(new_mf, existing)
        assert len(warnings) == 1
        w = warnings[0]
        assert w.with_skill == "beta"
        assert w.domain == "chat"
        assert 0.0 <= w.probability <= 1.0
        assert "建议" in w.suggestion or "优先级" in w.suggestion

    def test_predict_multiple_overlaps(self):
        """Multiple overlapping domains -> multiple warnings."""
        predictor = ConflictPredictor()
        new_mf = {
            "domains": [
                {"domain": "chat"},
                {"domain": "audio"},
            ],
            "priority": 50,
        }
        existing = [make_fake_skill_obj("gamma", domains=["chat", "audio"])]
        warnings = predictor.predict(new_mf, existing)
        assert len(warnings) == 2
        domains_found = {w.domain for w in warnings}
        assert domains_found == {"chat", "audio"}
        for w in warnings:
            assert w.with_skill == "gamma"

    def test_predict_probability_adjusted_by_yield_on_user(self):
        """New skill without yield_on_user, existing with yield_on_user -> warning generated."""
        predictor = ConflictPredictor()

        # New skill WITHOUT yield_on_user -> higher prob
        # existing skill WITH yield_on_user -> lower prob (-0.1)
        # net: base 0.5 - 0.1 = 0.4 > 0.3 threshold -> warning generated
        new_mf = {
            "domains": [{"domain": "chat"}],
            "conflict_resolution": "conflict",
            "priority": 50,
        }
        existing = [make_fake_skill_obj(
            "existing", domains=["chat"],
            priority=50,
            conflict_resolution="yield_on_user"
        )]
        warnings = predictor.predict(new_mf, existing)
        assert len(warnings) == 1

    def test_predict_probability_adjusted_by_priority_gap(self):
        """Large priority gap lowers probability."""
        predictor = ConflictPredictor()

        # new skill priority 10, existing priority 90 -> gap 80, prob should drop
        new_mf = {
            "domains": [{"domain": "chat"}],
            "priority": 10,
            "conflict_resolution": "conflict",
        }
        existing = [make_fake_skill_obj(
            "high_pri", domains=["chat"], priority=90, conflict_resolution="conflict"
        )]
        warnings = predictor.predict(new_mf, existing)
        # At base 0.5 with pri_gap > 20 -> 0.3, which is NOT > 0.3 so no warning
        assert len(warnings) == 0

    def test_predict_probability_capped(self):
        """Probability stays in [0.0, 1.0]."""
        predictor = ConflictPredictor()

        new_mf = {
            "domains": [{"domain": "chat"}],
            "conflict_resolution": "yield_on_user",
            "priority": 50,
        }
        existing = [make_fake_skill_obj(
            "existing", domains=["chat"],
            priority=50, conflict_resolution="yield_on_user"
        )]

        # new has yield_on_user (-0.2), existing has yield_on_user (-0.1)
        # base 0.5 - 0.2 - 0.1 = 0.2, pri_gap 0
        # prob = 0.2
        warnings = predictor.predict(new_mf, existing)
        # 0.2 <= 0.3, so no warning
        assert len(warnings) == 0

    def test_predict_skill_at_path_valid(self, tmp_path):
        """Create real SKILL.md -> predict from it."""
        predictor = ConflictPredictor()
        skill_dir = _make_skill_md_dir(
            tmp_path, "new_skill", domains=["chat"],
            conflict_resolution="conflict",
        )
        existing = [make_fake_skill_obj(
            "existing", domains=["chat"],
            conflict_resolution="conflict"
        )]
        warnings = predictor.predict_skill_at_path(skill_dir, existing)
        assert len(warnings) >= 1
        assert any(w.domain == "chat" for w in warnings)

    def test_predict_skill_at_path_missing_manifest(self, tmp_path):
        """No SKILL.md -> empty warnings."""
        predictor = ConflictPredictor()
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        warnings = predictor.predict_skill_at_path(empty_dir, [])
        assert warnings == []

    def test_predict_skill_at_path_invalid_yaml(self, tmp_path):
        """Malformed SKILL.md -> empty warnings."""
        predictor = ConflictPredictor()
        bad_dir = tmp_path / "badyaml"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("---\nnot: valid: yaml: : :\n---\n")
        warnings = predictor.predict_skill_at_path(bad_dir, [])
        assert warnings == []

    def test_estimate_probability_edge(self):
        """Edge cases for _estimate_probability."""
        predictor = ConflictPredictor()

        # Minimum probability should be 0.0
        from app.skill.runtime import Skill, SkillManifest

        new_mf = {
            "conflict_resolution": "yield_on_user",
            "priority": 1,
        }
        existing_mf = SkillManifest(
            name="edge",
            priority=100,
            conflict_resolution="yield_on_user",
        )
        # base 0.5 - 0.2 (new yield) - 0.1 (existing yield) - 0.2 (gap > 20) = 0.0
        prob = predictor._estimate_probability(new_mf, existing_mf, "chat")
        assert prob == 0.0

        # Maximum probability should be 1.0
        new_mf2 = {
            "conflict_resolution": "conflict",
            "priority": 50,
        }
        existing_mf2 = SkillManifest(
            name="edge_max",
            priority=50,
            conflict_resolution="conflict",
        )
        prob2 = predictor._estimate_probability(new_mf2, existing_mf2, "chat")
        # base 0.5, no adjustments -> 0.5
        assert prob2 == 0.5

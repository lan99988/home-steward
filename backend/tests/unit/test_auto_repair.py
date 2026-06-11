"""v1.1 Tests for AutoRepair — 7 tests targeting 70%+ coverage.

Uses Skill.__new__(Skill) + manual attribute setup (same pattern as
test_runtime.py) to avoid filesystem I/O.  HealthMonitor is used
as a real class to record execution metrics.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.skill.auto_repair import AutoRepair
from app.skill.health import HealthMonitor
from app.skill.runtime import Skill, SkillManifest
from app.skill.sandbox import RollbackSandbox


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def fake_skill():
    """A minimal Skill instance without filesystem dependencies.

    Uses Skill.__new__(Skill), then sets only the attributes that
    AutoRepair accesses: path, manifest (.name, .version).
    """
    s = Skill.__new__(Skill)
    s.path = Path("/fake/skill/path")
    s.manifest = SkillManifest(name="test-skill", version="1.0.0")
    return s


@pytest.fixture
def healthy_health(fake_skill):
    """HealthMonitor with mostly successful records (health > 0.5)."""
    hm = HealthMonitor()
    for i in range(5):
        hm.record_execution(fake_skill.manifest.name, success=True, latency_ms=50)
    return hm


@pytest.fixture
def unhealthy_health(fake_skill):
    """HealthMonitor with mostly failed records (health <= 0.5)."""
    hm = HealthMonitor()
    for i in range(5):
        hm.record_execution(fake_skill.manifest.name, success=False, latency_ms=50,
                            error=f"Error #{i}")
    return hm


@pytest.fixture
def mixed_health(fake_skill):
    """HealthMonitor with mixed records, some failures logged."""
    hm = HealthMonitor()
    # 3 successes, 2 failures -> health < 1.0
    hm.record_execution(fake_skill.manifest.name, success=True, latency_ms=100)
    hm.record_execution(fake_skill.manifest.name, success=True, latency_ms=100)
    hm.record_execution(fake_skill.manifest.name, success=False, latency_ms=100,
                        error="timeout")
    hm.record_execution(fake_skill.manifest.name, success=True, latency_ms=100)
    hm.record_execution(fake_skill.manifest.name, success=False, latency_ms=100,
                        error="crash")
    return hm


# =============================================================================
# Repair attempt tests
# =============================================================================

class TestAttemptRepair:
    """AutoRepair.attempt_repair() — the main entry point."""

    @pytest.mark.asyncio
    async def test_attempt_repair_healthy_skill(self, fake_skill, healthy_health):
        """Health > 0.5 -> returns True immediately, no repair needed."""
        repairer = AutoRepair(health=healthy_health)
        result = await repairer.attempt_repair(fake_skill)
        assert result is True

    @pytest.mark.asyncio
    async def test_attempt_repair_no_health_monitor(self, fake_skill):
        """Health is None -> treated as healthy (score=1.0), returns True."""
        repairer = AutoRepair(llm=None, health=None)
        result = await repairer.attempt_repair(fake_skill)
        assert result is True

    @pytest.mark.asyncio
    async def test_attempt_repair_unhealthy_no_llm(self, fake_skill, unhealthy_health):
        """Health <= 0.5, no LLM -> returns False (needs manual intervention)."""
        repairer = AutoRepair(llm=None, health=unhealthy_health)
        result = await repairer.attempt_repair(fake_skill)
        assert result is False

    @pytest.mark.asyncio
    async def test_attempt_repair_unhealthy_with_llm_stub(self, fake_skill, unhealthy_health):
        """Health <= 0.5, with LLM but _generate_fix stubbed -> returns False."""
        repairer = AutoRepair(llm=AsyncMock(), health=unhealthy_health)
        # _generate_fix returns False by default, so repair fails
        result = await repairer.attempt_repair(fake_skill)
        assert result is False


# =============================================================================
# Diagnostic tests
# =============================================================================

class TestCollectDiagnostic:
    """_collect_diagnostic() — diagnostic dict structure."""

    def test_collect_diagnostic_structure(self, fake_skill, mixed_health):
        """Verify diagnostic dict contains expected keys and values."""
        repairer = AutoRepair(health=mixed_health)
        diagnostic = repairer._collect_diagnostic(fake_skill)

        assert diagnostic["skill_name"] == "test-skill"
        assert diagnostic["version"] == "1.0.0"
        assert isinstance(diagnostic["health_score"], float)
        assert "failures" in diagnostic
        assert "code_path" in diagnostic
        assert diagnostic["code_path"].endswith("main.py")

    def test_collect_diagnostic_after_failures(self, fake_skill, mixed_health):
        """Failures from HealthMonitor are included in diagnostic."""
        repairer = AutoRepair(health=mixed_health)
        diagnostic = repairer._collect_diagnostic(fake_skill)

        assert len(diagnostic["failures"]) == 2  # two failures recorded
        assert "timeout" in diagnostic["failures"]
        assert "crash" in diagnostic["failures"]

    def test_collect_diagnostic_no_health(self, fake_skill):
        """Without health monitor, health_score defaults to 1.0, failures empty."""
        repairer = AutoRepair(health=None)
        diagnostic = repairer._collect_diagnostic(fake_skill)

        assert diagnostic["health_score"] == 1.0
        assert diagnostic["failures"] == []


# =============================================================================
# Generate fix tests
# =============================================================================

class TestGenerateFix:
    """_generate_fix() — LLM-driven fix generation (stub)."""

    @pytest.mark.asyncio
    async def test_generate_fix_stub_returns_false(self, fake_skill, mixed_health):
        """Default stub implementation returns False."""
        repairer = AutoRepair(llm=AsyncMock(), health=mixed_health)
        diagnostic = repairer._collect_diagnostic(fake_skill)
        result = await repairer._generate_fix(fake_skill, diagnostic)
        assert result is False

    @pytest.mark.asyncio
    async def test_generate_fix_handles_missing_code_file(self, tmp_path):
        """If main.py doesn't exist, _generate_fix catches FileNotFoundError."""
        skill_dir = tmp_path / "no-code"
        skill_dir.mkdir()
        # No main.py file

        s = Skill.__new__(Skill)
        s.path = skill_dir
        s.manifest = SkillManifest(name="no-code", version="0.0.0")

        repairer = AutoRepair(llm=AsyncMock(), health=None)
        diagnostic = repairer._collect_diagnostic(s)
        result = await repairer._generate_fix(s, diagnostic)
        assert result is False


# =============================================================================
# Init tests
# =============================================================================

class TestInit:
    """AutoRepair.__init__()."""

    def test_init_creates_sandbox(self):
        """Sandbox is not None after init."""
        repairer = AutoRepair()
        assert repairer.sandbox is not None
        assert isinstance(repairer.sandbox, RollbackSandbox)

    def test_init_with_llm_and_health(self, fake_skill, healthy_health):
        """LLM and health monitor are stored correctly."""
        llm = AsyncMock()
        repairer = AutoRepair(llm=llm, health=healthy_health)
        assert repairer.llm is llm
        assert repairer.health is healthy_health

    def test_init_defaults(self):
        """All defaults: llm=None, health=None."""
        repairer = AutoRepair()
        assert repairer.llm is None
        assert repairer.health is None

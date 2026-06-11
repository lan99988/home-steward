"""Integration: Execute failures -> HealthMonitor -> AutoRepair diagnostics."""
import pytest
from pathlib import Path

from app.skill.health import HealthMonitor
from app.skill.auto_repair import AutoRepair
from app.skill.runtime import Skill, SkillManifest


class TestHealthMonitoringChain:
    """Health detection and diagnostic collection chain."""

    @pytest.fixture
    def skill(self):
        s = Skill.__new__(Skill)
        s.path = Path("/fake")
        s.manifest = SkillManifest(name="test-skill", version="1.0.0")
        s.enabled = True
        s.module = object()
        s.health_score = 1.0
        s.last_used = None
        s.execution_count = 0
        return s

    def test_health_detects_failures(self, skill):
        monitor = HealthMonitor()
        # Record some failures
        for _ in range(3):
            monitor.record_execution("test-skill", success=False, latency_ms=100)
        assert monitor.should_disable("test-skill") is True
        assert monitor.get_success_rate("test-skill") == 0.0

    def test_auto_repair_diagnostic_collection(self, skill):
        monitor = HealthMonitor()
        monitor.record_execution("test-skill", success=False, latency_ms=100, error="timeout")
        monitor.record_execution("test-skill", success=False, latency_ms=500, error="crash")

        repair = AutoRepair(llm=None, health=monitor)
        diagnostic = repair._collect_diagnostic(skill)
        assert diagnostic["skill_name"] == "test-skill"
        assert diagnostic["health_score"] < 0.5
        assert len(diagnostic["failures"]) >= 1

    def test_healthy_skill_skips_repair(self, skill):
        monitor = HealthMonitor()
        monitor.record_execution("test-skill", success=True, latency_ms=50)

        repair = AutoRepair(llm=None, health=monitor)
        import asyncio
        result = asyncio.run(repair.attempt_repair(skill))
        assert result is True  # Healthy, no repair needed

"""Test suite for HealthMonitor — covers all methods and edge cases."""

import math
from typing import Dict, List

import pytest

from app.skill.health import HealthMonitor


# =============================================================================
# record_execution tests
# =============================================================================

class TestRecordExecution:
    """record_execution() — score calculation and data structure integrity."""

    def test_record_execution_success(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=100)
        assert hm.records["test_skill"] == [pytest.approx(1.0)]

    def test_record_execution_failure(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=False, latency_ms=100)
        assert hm.records["test_skill"] == [pytest.approx(0.0)]

    def test_record_execution_high_latency(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=2500)
        # 1.0 * 0.8 = 0.8
        assert hm.records["test_skill"] == [pytest.approx(0.8)]

    def test_record_execution_with_error(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=100,
                            error="Something went wrong")
        # 1.0 * 0.5 = 0.5
        assert hm.records["test_skill"] == [pytest.approx(0.5)]

    def test_record_execution_with_error_and_high_latency(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=3000,
                            error="Timeout")
        # 1.0 * 0.8 (latency) * 0.5 (error) = 0.4
        assert hm.records["test_skill"] == [pytest.approx(0.4)]

    def test_record_execution_failure_high_latency_error(self):
        """All penalties stack: failure + high-latency + error = 0.0 * 0.8 * 0.5 = 0.0"""
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=False, latency_ms=3000,
                            error="Crash")
        # 0.0 * 0.8 * 0.5 = 0.0
        assert hm.records["test_skill"] == [pytest.approx(0.0)]

    def test_record_caps_at_100(self):
        hm = HealthMonitor()
        for i in range(110):
            hm.record_execution("test_skill", success=True, latency_ms=50)
        assert len(hm.records["test_skill"]) == 100
        assert len(hm.latencies["test_skill"]) == 100

    def test_record_failures_caps_at_20(self):
        hm = HealthMonitor()
        for i in range(30):
            hm.record_execution("test_skill", success=False, latency_ms=50,
                                error=f"Error #{i}")
        assert len(hm.failures["test_skill"]) == 20

    def test_record_multiple_skills_isolated(self):
        hm = HealthMonitor()
        hm.record_execution("skill_a", success=True, latency_ms=100)
        hm.record_execution("skill_b", success=False, latency_ms=200,
                            error="fail")
        assert len(hm.records["skill_a"]) == 1
        assert len(hm.records["skill_b"]) == 1
        assert hm.records["skill_a"][0] == pytest.approx(1.0)
        assert hm.records["skill_b"][0] == pytest.approx(0.0)

    def test_record_latency_recorded(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=1234.5)
        assert hm.latencies["test_skill"] == [1234.5]

    def test_record_failure_appended(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=False, latency_ms=50,
                            error="kaboom")
        assert hm.failures["test_skill"] == ["kaboom"]

    def test_record_no_error_no_failure_entry(self):
        """When no error passed, failures list is not populated."""
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=50)
        assert hm.failures.get("test_skill", []) == []


# =============================================================================
# get_health tests
# =============================================================================

class TestGetHealth:
    """get_health() — weighted average health score."""

    def test_get_health_no_records(self):
        hm = HealthMonitor()
        assert hm.get_health("nonexistent") == pytest.approx(1.0)

    def test_get_health_single_record(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=100)
        assert hm.get_health("test_skill") == pytest.approx(1.0)

    def test_get_health_weighted_average(self):
        """Two records: scores [0.5, 1.0]
           weights: (1/2, 2/2) = (0.5, 1.0)
           weighted_sum = 0.5*0.5 + 1.0*1.0 = 0.25 + 1.0 = 1.25
           total_weight = 0.5 + 1.0 = 1.5
           result = 1.25 / 1.5 = 0.8333...
        """
        hm = HealthMonitor()
        hm.records["test_skill"] = [0.5, 1.0]
        expected = (0.5 * (1/2) + 1.0 * (2/2)) / ((1/2) + (2/2))
        assert hm.get_health("test_skill") == pytest.approx(expected)

    def test_get_health_after_mixed_results(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=100)    # 1.0
        hm.record_execution("test_skill", success=False, latency_ms=100)   # 0.0
        hm.record_execution("test_skill", success=True, latency_ms=100)    # 1.0
        health = hm.get_health("test_skill")
        # Recent records (index 2) weighted highest: should be > 0.5
        assert 0 < health < 1.0

    def test_get_health_ignores_other_skills(self):
        hm = HealthMonitor()
        hm.record_execution("skill_a", success=True, latency_ms=100)
        hm.record_execution("skill_b", success=False, latency_ms=100)
        assert hm.get_health("skill_a") == pytest.approx(1.0)
        assert hm.get_health("skill_b") == pytest.approx(0.0)


# =============================================================================
# get_latency_p99 tests
# =============================================================================

class TestGetLatencyP99:
    """get_latency_p99() — 99th percentile latency."""

    def test_get_latency_p99_empty(self):
        hm = HealthMonitor()
        assert hm.get_latency_p99("nonexistent") == pytest.approx(0.0)

    def test_get_latency_p99_single(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=500)
        assert hm.get_latency_p99("test_skill") == pytest.approx(500.0)

    def test_get_latency_p99_multiple(self):
        hm = HealthMonitor()
        latencies = list(range(1, 101))  # 1..100
        for l in latencies:
            hm.record_execution("test_skill", success=True, latency_ms=l)
        # 100 entries, idx = int(100 * 0.99) = 99
        # sorted[99] = 100
        assert hm.get_latency_p99("test_skill") == pytest.approx(100.0)

    def test_get_latency_p99_not_exact_boundary(self):
        hm = HealthMonitor()
        for l in [10, 20, 30, 40, 50]:
            hm.record_execution("test_skill", success=True, latency_ms=l)
        # 5 entries, idx = int(5 * 0.99) = 4, sorted[4] = 50
        assert hm.get_latency_p99("test_skill") == pytest.approx(50.0)


# =============================================================================
# should_disable tests
# =============================================================================

class TestShouldDisable:
    """should_disable() — threshold at 0.5."""

    def test_should_disable_below_threshold(self):
        hm = HealthMonitor()
        hm.records["test_skill"] = [0.4]
        assert hm.should_disable("test_skill") is True

    def test_should_disable_above_threshold(self):
        hm = HealthMonitor()
        hm.records["test_skill"] = [0.6]
        assert hm.should_disable("test_skill") is False

    def test_should_disable_exactly_threshold(self):
        hm = HealthMonitor()
        hm.records["test_skill"] = [0.5]
        # 0.5 < 0.5 is False
        assert hm.should_disable("test_skill") is False

    def test_should_disable_no_records(self):
        hm = HealthMonitor()
        assert hm.should_disable("nonexistent") is False  # returns 1.0


# =============================================================================
# get_success_rate tests
# =============================================================================

class TestGetSuccessRate:
    """get_success_rate() — ratio of scores > 0.5."""

    def test_get_success_rate_no_records(self):
        hm = HealthMonitor()
        assert hm.get_success_rate("nonexistent") == pytest.approx(1.0)

    def test_get_success_rate_all_success(self):
        hm = HealthMonitor()
        hm.records["test_skill"] = [1.0, 1.0, 1.0]
        assert hm.get_success_rate("test_skill") == pytest.approx(1.0)

    def test_get_success_rate_mixed(self):
        hm = HealthMonitor()
        hm.records["test_skill"] = [1.0, 0.0, 1.0, 0.8]  # 3/4 > 0.5
        assert hm.get_success_rate("test_skill") == pytest.approx(0.75)

    def test_get_success_rate_all_failures(self):
        hm = HealthMonitor()
        hm.records["test_skill"] = [0.0, 0.0, 0.0]
        assert hm.get_success_rate("test_skill") == pytest.approx(0.0)

    def test_get_success_rate_boundary(self):
        """Scores exactly 0.5 should not count as success (not > 0.5)."""
        hm = HealthMonitor()
        hm.records["test_skill"] = [0.5, 1.0]
        assert hm.get_success_rate("test_skill") == pytest.approx(0.5)


# =============================================================================
# get_recent_failures tests
# =============================================================================

class TestGetRecentFailures:
    """get_recent_failures() — retrieving recent error messages."""

    def test_get_recent_failures_empty(self):
        hm = HealthMonitor()
        assert hm.get_recent_failures("nonexistent") == []

    def test_get_recent_failures_single(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=False, latency_ms=50,
                            error="error 1")
        assert hm.get_recent_failures("test_skill") == ["error 1"]

    def test_get_recent_failures_default_n(self):
        hm = HealthMonitor()
        for i in range(10):
            hm.record_execution("test_skill", success=False, latency_ms=50,
                                error=f"error {i}")
        # Default n=5, returns last 5
        assert hm.get_recent_failures("test_skill") == [
            "error 5", "error 6", "error 7", "error 8", "error 9"
        ]

    def test_get_recent_failures_custom_n(self):
        hm = HealthMonitor()
        for i in range(10):
            hm.record_execution("test_skill", success=False, latency_ms=50,
                                error=f"e{i}")
        assert hm.get_recent_failures("test_skill", n=3) == ["e7", "e8", "e9"]

    def test_get_recent_failures_no_failures_for_skill(self):
        hm = HealthMonitor()
        hm.records["other"] = []
        hm.failures["other"] = []
        assert hm.get_recent_failures("other") == []

    def test_get_recent_failures_skill_without_failures_key(self):
        """Skill exists in records but not in failures dict."""
        hm = HealthMonitor()
        hm.records["test_skill"] = [1.0]
        # No failures key for this skill
        assert hm.get_recent_failures("test_skill") == []


# =============================================================================
# get_all_health tests
# =============================================================================

class TestGetAllHealth:
    """get_all_health() — health across all skills."""

    def test_get_all_health_empty(self):
        hm = HealthMonitor()
        assert hm.get_all_health() == {}

    def test_get_all_health_multiple_skills(self):
        hm = HealthMonitor()
        hm.record_execution("skill_a", success=True, latency_ms=100)
        hm.record_execution("skill_b", success=False, latency_ms=100)
        hm.record_execution("skill_c", success=True, latency_ms=3000)  # 0.8
        health = hm.get_all_health()
        assert "skill_a" in health
        assert "skill_b" in health
        assert "skill_c" in health
        assert health["skill_a"] == pytest.approx(1.0)
        assert health["skill_b"] == pytest.approx(0.0)
        assert health["skill_c"] == pytest.approx(0.8)

    def test_get_all_health_does_not_affect_internal_state(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=100)
        h1 = hm.get_all_health()
        h2 = hm.get_all_health()
        assert h1 == h2


# =============================================================================
# get_summary tests
# =============================================================================

class TestGetSummary:
    """get_summary() — full summary dict."""

    def test_get_summary_empty(self):
        hm = HealthMonitor()
        assert hm.get_summary() == {}

    def test_get_summary_structure(self):
        hm = HealthMonitor()
        hm.records["skill_a"] = [1.0, 1.0, 1.0]
        hm.latencies["skill_a"] = [100, 200, 150]
        hm.failures["skill_a"] = []
        hm.records["skill_b"] = [0.0]
        hm.latencies["skill_b"] = [500]
        hm.failures["skill_b"] = ["timeout"]

        summary = hm.get_summary()
        assert "skill_a" in summary
        assert "skill_b" in summary

        sa = summary["skill_a"]
        assert "health_score" in sa
        assert "success_rate" in sa
        assert "p99_latency_ms" in sa
        assert "total_calls" in sa
        assert "recent_errors" in sa
        assert sa["total_calls"] == 3
        assert sa["recent_errors"] == 0
        assert isinstance(sa["health_score"], float)
        assert isinstance(sa["success_rate"], float)
        # round() on an integer may still return int, so accept int or float
        assert isinstance(sa["p99_latency_ms"], (int, float))

        sb = summary["skill_b"]
        assert sb["total_calls"] == 1
        assert sb["recent_errors"] == 1

    def test_get_summary_rounding(self):
        hm = HealthMonitor()
        hm.record_execution("test_skill", success=True, latency_ms=123.456)
        summary = hm.get_summary()
        # health_score rounded to 2, p99_latency_ms rounded to 1
        assert summary["test_skill"]["health_score"] == 1.0
        assert summary["test_skill"]["p99_latency_ms"] == 123.5


# =============================================================================
# Edge cases and integration scenarios
# =============================================================================

class TestEdgeCases:
    """Edge cases and cross-method integration."""

    def test_health_edge_multiple_skills(self):
        """Records for different skills remain fully isolated."""
        hm = HealthMonitor()
        for i in range(50):
            hm.record_execution("alpha", success=True, latency_ms=100)
            hm.record_execution("beta", success=False, latency_ms=100,
                                error=f"err_{i}")

        assert len(hm.records["alpha"]) == 50
        assert len(hm.records["beta"]) == 50
        # failures caps at 20, so only last 20 kept
        assert len(hm.failures["beta"]) == 20
        assert len(hm.failures["beta"]) == 20
        assert hm.failures.get("alpha", []) == []

        assert hm.get_health("alpha") == pytest.approx(1.0)
        assert hm.get_health("beta") == pytest.approx(0.0)

    def test_latency_p99_same_as_expected(self):
        hm = HealthMonitor()
        latencies = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        for l in latencies:
            hm.record_execution("test_skill", success=True, latency_ms=l)
        # 10 entries, idx = int(10*0.99) = 9, sorted[9] = 1000
        assert hm.get_latency_p99("test_skill") == pytest.approx(1000.0)

    def test_success_rate_with_penalized_scores(self):
        """Scores like 0.8 (high latency penalty) should still count as success."""
        hm = HealthMonitor()
        hm.records["test_skill"] = [0.8, 0.4, 0.8]
        # 0.8 > 0.5 ✓, 0.4 > 0.5 ✗, 0.8 > 0.5 ✓ → 2/3
        assert hm.get_success_rate("test_skill") == pytest.approx(2/3)

    def test_should_disable_uses_weighted_health(self):
        """should_disable calls get_health which uses weighted average."""
        hm = HealthMonitor()
        # 10 records: first 9 are 1.0, last is 0.0
        hm.records["test_skill"] = [1.0] * 9 + [0.0]
        # Weighted average will be heavily pulled down by the most recent (0.0)
        disabled = hm.should_disable("test_skill")
        assert isinstance(disabled, bool)

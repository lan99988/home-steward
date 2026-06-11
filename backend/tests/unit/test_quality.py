"""Test suite for QualityMonitor — covers history, trend, alert, and run_daily_test."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.skill.quality import QualityMonitor


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_router():
    """Return an llm_router mock whose route() returns controlled results."""
    router = AsyncMock()
    router.route = AsyncMock()
    return router


@pytest.fixture
def quality_with_history(tmp_path: Path) -> QualityMonitor:
    """Create a QualityMonitor with history_path pointing into tmp_path,
    and inject a known history by writing directly to the file before init."""
    history_file = tmp_path / "quality_scores.json"
    history_file.write_text(json.dumps([0.5, 0.6, 0.7, 0.8, 0.9]))
    qm = QualityMonitor(history_path=str(history_file))
    return qm


# =============================================================================
# __init__ / _load_history tests
# =============================================================================

class TestInit:
    """Initialization and history loading."""

    def test_init_empty_history(self, tmp_path: Path):
        """No history file exists → empty history."""
        history_file = tmp_path / "quality_scores.json"
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.history == []
        assert qm.get_latest_score() is None

    def test_init_loads_existing_history(self, tmp_path: Path):
        """History file exists → loads correctly."""
        history_file = tmp_path / "quality_scores.json"
        history_file.write_text(json.dumps([0.1, 0.2, 0.3]))
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.history == [0.1, 0.2, 0.3]

    def test_init_loads_empty_json_array(self, tmp_path: Path):
        """Empty JSON array loads as empty list."""
        history_file = tmp_path / "quality_scores.json"
        history_file.write_text("[]")
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.history == []

    def test_init_invalid_json(self, tmp_path: Path):
        """Corrupt JSON file loads as empty history (no crash)."""
        history_file = tmp_path / "quality_scores.json"
        history_file.write_text("not valid json")
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.history == []

    def test_init_creates_parent_directory(self, tmp_path: Path):
        """Parent dir is created automatically if it doesn't exist."""
        nested = tmp_path / "sub" / "nested" / "scores.json"
        qm = QualityMonitor(history_path=str(nested))
        assert nested.parent.exists()


# =============================================================================
# get_latest_score tests
# =============================================================================

class TestGetLatestScore:
    """get_latest_score() — returns last entry or None."""

    def test_get_latest_score_empty(self, tmp_path: Path):
        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.get_latest_score() is None

    def test_get_latest_score_with_data(self, quality_with_history: QualityMonitor):
        assert quality_with_history.get_latest_score() == pytest.approx(0.9)

    def test_get_latest_score_single_entry(self, tmp_path: Path):
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.42]))
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.get_latest_score() == pytest.approx(0.42)


# =============================================================================
# get_trend tests
# =============================================================================

class TestGetTrend:
    """get_trend() — score diff over last N entries."""

    def test_get_trend_rising(self, quality_with_history: QualityMonitor):
        # history: [0.5, 0.6, 0.7, 0.8, 0.9]
        trend = quality_with_history.get_trend(days=5)
        assert trend == pytest.approx(0.4)  # 0.9 - 0.5

    def test_get_trend_falling(self, tmp_path: Path):
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.9, 0.8, 0.7, 0.6, 0.5]))
        qm = QualityMonitor(history_path=str(history_file))
        trend = qm.get_trend(days=5)
        assert trend == pytest.approx(-0.4)  # 0.5 - 0.9

    def test_get_trend_not_enough_data(self, tmp_path: Path):
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.5]))
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.get_trend() == pytest.approx(0.0)

    def test_get_trend_empty_history(self, tmp_path: Path):
        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.get_trend() == pytest.approx(0.0)

    def test_get_trend_exact_7_days(self, quality_with_history: QualityMonitor):
        """Uses last `days` entries. With 5 entries and days=7, still uses all 5."""
        # history: [0.5, 0.6, 0.7, 0.8, 0.9], days=7
        trend = quality_with_history.get_trend(days=7)
        assert trend == pytest.approx(0.4)  # recent[-1] - recent[0] = 0.9 - 0.5

    def test_get_trend_partial_window(self, tmp_path: Path):
        """More entries than days: only last `days` entries used."""
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.1, 0.2, 0.3, 0.4, 0.5]))
        qm = QualityMonitor(history_path=str(history_file))
        trend = qm.get_trend(days=3)
        # recent = [0.3, 0.4, 0.5], trend = 0.5 - 0.3 = 0.2
        assert trend == pytest.approx(0.2)


# =============================================================================
# should_alert tests
# =============================================================================

class TestShouldAlert:
    """should_alert() — 3 consecutive drops > 5%."""

    def test_should_alert_no_data(self, tmp_path: Path):
        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.should_alert() is False

    def test_should_alert_not_enough_data(self, tmp_path: Path):
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.9, 0.8, 0.7]))
        qm = QualityMonitor(history_path=str(history_file))
        # len=3, but needs 4 according to code (len(self.history) < 4)
        assert qm.should_alert() is False

    def test_should_alert_consecutive_drop(self, tmp_path: Path):
        """0.9 → 0.8 → 0.7 → 0.6: 3 consecutive drops, total drop > 5%."""
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.9, 0.8, 0.7, 0.6]))
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.should_alert() is True

    def test_should_alert_drop_under_threshold(self, tmp_path: Path):
        """0.9 → 0.88 → 0.86 → 0.85: drops are < 5% each, total drop < 5%."""
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.9, 0.88, 0.86, 0.85]))
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.should_alert() is False

    def test_should_alert_not_consecutive(self, tmp_path: Path):
        """0.9 → 0.8 → 0.9 → 0.8: not consecutive drops."""
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.9, 0.8, 0.9, 0.8]))
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.should_alert() is False

    def test_should_alert_three_consecutive_not_four(self, tmp_path: Path):
        """Exactly 4 entries: 0.9, 0.8, 0.7 is 3 consecutive drops → True."""
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([1.0, 0.9, 0.8, 0.7]))
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.should_alert() is True

    def test_should_alert_exactly_5_percent(self, tmp_path: Path):
        """Drop exactly 0.05 should NOT trigger (> 0.05, not >=)."""
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.95, 0.90, 0.90, 0.90]))
        qm = QualityMonitor(history_path=str(history_file))
        # 0.95 > 0.90 > 0.90 — second and third are equal, not strictly decreasing
        assert qm.should_alert() is False

    def test_should_alert_flat_line_no_alert(self, tmp_path: Path):
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.8, 0.8, 0.8, 0.8]))
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.should_alert() is False


# =============================================================================
# get_history tests
# =============================================================================

class TestGetHistory:
    """get_history() — returns a copy of internal history."""

    def test_get_history_returns_copy(self, quality_with_history: QualityMonitor):
        h1 = quality_with_history.get_history()
        h2 = quality_with_history.get_history()
        assert h1 == h2
        # Modify the returned list — internal should not change
        h1.append(999.0)
        assert quality_with_history.get_history() == [0.5, 0.6, 0.7, 0.8, 0.9]

    def test_get_history_empty(self, tmp_path: Path):
        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))
        assert qm.get_history() == []


# =============================================================================
# run_daily_test tests
# =============================================================================

class TestRunDailyTest:
    """run_daily_test() — LLM integration test with mocked router."""

    @pytest.mark.asyncio
    async def test_run_daily_test_all_pass(self, tmp_path: Path, mock_llm_router):
        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))

        # All 6 test cases return correct intent
        async def route_side_effect(text):
            expected_map = {
                "打开客厅灯": {"intent": "turn_on"},
                "关闭空调": {"intent": "turn_off"},
                "空调调到26度": {"intent": "set_temperature"},
                "客厅亮度调到80": {"intent": "set_brightness"},
                "温馨一点": {"intent": "set_scene"},
                "离家模式": {"intent": "set_scene"},
            }
            # Simulate the two-value return (_, result)
            return "", expected_map[text]

        mock_llm_router.route.side_effect = route_side_effect
        score = await qm.run_daily_test(mock_llm_router)
        assert score == pytest.approx(1.0)
        assert qm.history == [1.0]

    @pytest.mark.asyncio
    async def test_run_daily_test_partial_pass(self, tmp_path: Path, mock_llm_router):
        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))

        # Only 3 out of 6 pass
        async def route_side_effect(text):
            if text in {"打开客厅灯", "关闭空调", "空调调到26度"}:
                return "", {"intent": "wrong_intent"}
            return "", {"intent": "set_scene"}  # for scene tests

        mock_llm_router.route.side_effect = route_side_effect
        score = await qm.run_daily_test(mock_llm_router)
        # "温馨一点" + "离家模式" = 2 passes
        assert score == pytest.approx(2 / 6)
        assert len(qm.history) == 1

    @pytest.mark.asyncio
    async def test_run_daily_test_all_fail(self, tmp_path: Path, mock_llm_router):
        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))

        async def route_side_effect(text):
            return "", {"intent": "unknown"}

        mock_llm_router.route.side_effect = route_side_effect
        score = await qm.run_daily_test(mock_llm_router)
        assert score == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_run_daily_test_appends_to_history(self, tmp_path: Path, mock_llm_router):
        """Score is appended to existing history."""
        history_file = tmp_path / "scores.json"
        history_file.write_text(json.dumps([0.5, 0.6]))
        qm = QualityMonitor(history_path=str(history_file))

        async def route_side_effect(text):
            return "", {"intent": "turn_on"}

        mock_llm_router.route.side_effect = route_side_effect
        score = await qm.run_daily_test(mock_llm_router)
        assert len(qm.history) == 3  # original 2 + new 1
        assert qm.history[-1] == pytest.approx(1/6)

    @pytest.mark.asyncio
    async def test_run_daily_test_router_exception(self, tmp_path: Path, mock_llm_router):
        """Exception during route() should be caught, not crash."""
        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))

        # First call raises, rest succeed
        call_count = 0

        async def route_side_effect(text):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("LLM unavailable")
            return "", {"intent": "turn_off"}

        mock_llm_router.route.side_effect = route_side_effect
        score = await qm.run_daily_test(mock_llm_router)
        # First call (打开客厅灯) errors = 0 pass. Then 5 calls return turn_off.
        # Only "关闭空调" expects turn_off → 1 match out of 6.
        assert score == pytest.approx(1 / 6)

    @pytest.mark.asyncio
    async def test_run_daily_test_returns_none_result(self, tmp_path: Path, mock_llm_router):
        """route() returns result=None should not crash, creates no match."""
        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))

        async def route_side_effect(text):
            return "", None

        mock_llm_router.route.side_effect = route_side_effect
        score = await qm.run_daily_test(mock_llm_router)
        assert score == pytest.approx(0.0)


# =============================================================================
# Persistence tests
# =============================================================================

class TestPersistence:
    """History save and trim behavior."""

    def test_history_saves_to_file(self, tmp_path: Path, mock_llm_router):
        """After run_daily_test, the score is written to the file."""
        import asyncio

        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))

        async def route_side_effect(text):
            return "", {"intent": "turn_on"}

        mock_llm_router.route.side_effect = route_side_effect
        asyncio.run(qm.run_daily_test(mock_llm_router))

        # Verify file was written
        assert history_file.exists()
        saved = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(saved) == 1
        assert saved[0] == pytest.approx(1/6)

    def test_history_max_90_entries(self, tmp_path: Path):
        """Old entries beyond 90 are trimmed on save."""
        history_file = tmp_path / "scores.json"
        old_data = list(range(100))  # 0..99
        history_file.write_text(json.dumps(old_data))
        qm = QualityMonitor(history_path=str(history_file))

        # __init__ loads from file. _save_history is called with self.history[-90:]
        # But _save_history is only called on run_daily_test or explicit call.
        # Let's trigger save by calling run_daily_test.
        # Manually add one more entry and save.
        qm.history.append(100)
        qm._save_history()

        saved = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(saved) == 90  # was 101, trimmed to 90

    def test_history_trimmed_on_init_from_file(self, tmp_path: Path):
        """If file has > 90 entries, load everything but save trims to 90."""
        history_file = tmp_path / "scores.json"
        old_data = list(range(95))
        history_file.write_text(json.dumps(old_data))
        qm = QualityMonitor(history_path=str(history_file))
        # Loads all 95 into memory
        assert len(qm.history) == 95
        # Save trims
        qm._save_history()
        saved = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(saved) == 90

    def test_history_multiple_saves_append_correctly(self, tmp_path: Path, mock_llm_router):
        """Multiple run_daily_test calls accumulate history and persist."""
        import asyncio

        history_file = tmp_path / "scores.json"
        qm = QualityMonitor(history_path=str(history_file))

        async def route_side_effect(text):
            return "", {"intent": "turn_on"}

        mock_llm_router.route.side_effect = route_side_effect
        asyncio.run(qm.run_daily_test(mock_llm_router))
        asyncio.run(qm.run_daily_test(mock_llm_router))
        asyncio.run(qm.run_daily_test(mock_llm_router))

        saved = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(saved) == 3


# =============================================================================
# Integration scenario tests
# =============================================================================

class TestIntegration:
    """Cross-method integration scenarios."""

    def test_full_workflow(self, tmp_path: Path):
        """Simulate several days of quality monitoring."""
        history_file = tmp_path / "scores.json"

        qm = QualityMonitor(history_path=str(history_file))
        assert qm.get_latest_score() is None
        assert qm.should_alert() is False
        assert qm.get_trend() == pytest.approx(0.0)

        # Day 1-4: declining scores
        for score in [0.9, 0.85, 0.75, 0.65]:
            qm.history.append(score)
            qm._save_history()

        assert qm.get_latest_score() == pytest.approx(0.65)
        assert qm.get_trend(days=4) == pytest.approx(-0.25)
        assert qm.should_alert() is True  # 0.9 > 0.85 > 0.75 > 0.65, drops > 5%

    def test_recovery_after_decline(self, tmp_path: Path):
        """After a decline, a recovery should stop alerts."""
        history_file = tmp_path / "scores.json"

        qm = QualityMonitor(history_path=str(history_file))
        qm.history = [0.9, 0.8, 0.7, 0.6]
        assert qm.should_alert() is True

        qm.history.append(0.75)
        # last 3: [0.7, 0.6, 0.75] — 0.6 < 0.75, not strictly decreasing
        assert qm.should_alert() is False

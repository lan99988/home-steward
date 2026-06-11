"""三层冲突仲裁器 — 28 tests (目标 95%+ 分支覆盖)"""

import random
import concurrent.futures
import pytest
from freezegun import freeze_time
from hypothesis import given, strategies as st

from app.skill.arbiter import ConflictArbiter


@pytest.fixture
def arbiter():
    """每个测试函数使用独立的仲裁器实例。"""
    return ConflictArbiter(history_size=50)


# ═══════════════════════════════════════════════════
# Layer 1: 用户指令无条件放行
# ═══════════════════════════════════════════════════

class TestLayer1UserOverride:
    """第一层：source='user' 的意图永远通过仲裁。"""

    def test_user_always_passes(self, arbiter):
        intent = {"device": "light", "domain": "lighting",
                  "intent": "turn_on", "source": "user"}
        assert arbiter.resolve(intent, skill_priority=1) is intent

    def test_user_bypasses_existing_higher_priority(self, arbiter):
        arbiter.resolve({"device": "light", "domain": "lighting",
                         "intent": "turn_off", "source": "auto"}, skill_priority=80)
        user_intent = {"device": "light", "domain": "lighting",
                       "intent": "turn_on", "source": "user"}
        assert arbiter.resolve(user_intent, skill_priority=1) is user_intent

    def test_user_bypasses_oscillation_block(self, arbiter):
        """用户指令不受防震荡限制。"""
        for _ in range(4):
            arbiter.resolve({"device": "light", "domain": "lighting",
                             "intent": "toggle", "source": "auto"}, skill_priority=50)
        user = {"device": "light", "domain": "lighting",
                "intent": "stable", "source": "user"}
        assert arbiter.resolve(user) is user


class TestLayer2Priority:
    """第二层：静态优先级比较。"""

    def test_no_conflict_passes(self, arbiter):
        intent = {"device": "light", "domain": "lighting", "intent": "turn_on"}
        assert arbiter.resolve(intent, skill_priority=50) is intent

    def test_different_device_no_conflict(self, arbiter):
        arbiter.resolve({"device": "light_a", "domain": "lighting", "intent": "on"}, skill_priority=50)
        intent_b = {"device": "light_b", "domain": "lighting", "intent": "off"}
        assert arbiter.resolve(intent_b, skill_priority=50) is intent_b

    def test_different_domain_no_conflict(self, arbiter):
        arbiter.resolve({"device": "light", "domain": "lighting", "intent": "on"}, skill_priority=50)
        intent_ac = {"device": "light", "domain": "climate", "intent": "set_temp"}
        assert arbiter.resolve(intent_ac, skill_priority=50) is intent_ac

    def test_higher_priority_overrides(self, arbiter):
        arbiter.resolve({"device": "light", "domain": "lighting",
                         "intent": "off"}, skill_priority=30)
        intent = {"device": "light", "domain": "lighting", "intent": "on"}
        assert arbiter.resolve(intent, skill_priority=80) is intent

    def test_lower_priority_blocked(self, arbiter):
        arbiter.resolve({"device": "light", "domain": "lighting",
                         "intent": "on"}, skill_priority=80)
        result = arbiter.resolve({"device": "light", "domain": "lighting",
                                  "intent": "off"}, skill_priority=20)
        assert result is None

    def test_priority_edge_extremes(self, arbiter):
        arbiter.resolve({"device": "light", "domain": "lighting",
                         "intent": "min"}, skill_priority=1)
        intent = {"device": "light", "domain": "lighting", "intent": "max"}
        assert arbiter.resolve(intent, skill_priority=100) is intent


class TestLayer3AntiOscillation:
    """第三层：同优先级防震荡检测。

    防震荡逻辑：recent_toggles 统计 30 秒窗口内 intent 与当前 intent
    不同的记录数。达到 >= 2 次才阻止。因此序列 on -> off -> on 中
    第 3 个 on 只有 1 次不同 (off != on)，通过；第 4 个 off 有 2 次
    不同 (on != off, on != off)，被阻挡。
    """

    def test_two_toggles_does_not_block_third(self, arbiter):
        """
        on -> off -> on: 只有 1 次切换 (off -> on)，不足 2，不阻止。
        第 4 次 off 才会被阻止。
        """
        base = {"device": "light", "domain": "lighting", "intent": "on"}
        toggle = {"device": "light", "domain": "lighting", "intent": "off"}
        arbiter.resolve(base, skill_priority=50)   # on: passes (no conflict)
        arbiter.resolve(toggle, skill_priority=50)  # off: passes (1 toggle seen)
        result = arbiter.resolve(base, skill_priority=50)  # on: 1 toggle, passes
        assert result is base  # 3rd call passes because recent_toggles=1 < 2

    def test_three_toggles_blocks_fourth(self, arbiter):
        """
        on -> off -> on -> off: 前 3 次通过，第 4 次被阻止。
        """
        for i, intent_str in enumerate(["on", "off", "on", "off"]):
            intent = {"device": "light", "domain": "lighting", "intent": intent_str}
            result = arbiter.resolve(intent, skill_priority=50)
            if i < 3:
                assert result is not None, f"Toggle {i} should pass"
            else:
                assert result is None, f"Toggle {i} should be blocked"

    def test_rapid_toggles_blocked(self, arbiter):
        """
        on -> off -> on -> off -> on: 第 4 次 (off) 被阻挡。
        """
        for i, intent_str in enumerate(["on", "off", "on", "off", "on"]):
            intent = {"device": "light", "domain": "lighting", "intent": intent_str}
            result = arbiter.resolve(intent, skill_priority=50)
            if i != 3:
                assert result is not None, f"Toggle {i} should pass"
            else:
                assert result is None, f"Toggle {i} (4th) should be blocked"

    def test_same_intent_not_counted_as_toggle(self, arbiter):
        """同一个意图重复执行不算切换。"""
        intent = {"device": "light", "domain": "lighting", "intent": "on"}
        for _ in range(5):
            assert arbiter.resolve(intent, skill_priority=50) is intent


class TestTimeWindow:
    """30 秒冲突窗口测试（含 29s/30s/31s 精确边界）。"""

    @freeze_time("2026-06-11 12:00:00")
    def test_29s_still_in_window(self, arbiter):
        arbiter.resolve({"device": "light", "domain": "lighting", "intent": "on"}, skill_priority=50)
        with freeze_time("2026-06-11 12:00:29"):
            intent2 = {"device": "light", "domain": "lighting", "intent": "off"}
            assert arbiter.resolve(intent2, skill_priority=30) is None

    @freeze_time("2026-06-11 12:00:00")
    def test_30s_exact_boundary(self, arbiter):
        """30 秒整，now - ts = 30，条件 < 30 不满足，应过期。"""
        arbiter.resolve({"device": "light", "domain": "lighting", "intent": "on"}, skill_priority=50)
        with freeze_time("2026-06-11 12:00:30"):
            intent2 = {"device": "light", "domain": "lighting", "intent": "off"}
            assert arbiter.resolve(intent2, skill_priority=30) is intent2

    @freeze_time("2026-06-11 12:00:00")
    def test_31s_expired(self, arbiter):
        arbiter.resolve({"device": "light", "domain": "lighting", "intent": "on"}, skill_priority=50)
        with freeze_time("2026-06-11 12:00:31"):
            intent2 = {"device": "light", "domain": "lighting", "intent": "off"}
            assert arbiter.resolve(intent2, skill_priority=30) is intent2

    @freeze_time("2026-06-11 12:00:00")
    def test_30s_memory_block_properly(self, arbiter):
        """在同 30 秒窗口内多次切换被阻止。"""
        arbiter.resolve({"device": "light", "domain": "lighting", "intent": "on"})  # 1st pass
        with freeze_time("2026-06-11 12:00:05"):
            arbiter.resolve({"device": "light", "domain": "lighting", "intent": "off"})  # 2nd pass
        with freeze_time("2026-06-11 12:00:10"):
            arbiter.resolve({"device": "light", "domain": "lighting", "intent": "on"})  # 3rd pass (1 toggle)
        with freeze_time("2026-06-11 12:00:15"):
            assert arbiter.resolve({"device": "light", "domain": "lighting", "intent": "off"}) is None  # 4th blocked (2 toggles)

    @freeze_time("2026-06-11 12:00:00")
    def test_mixed_timestamps_expiry_partial(self, arbiter):
        """部分记录过期，部分仍在窗口内。"""
        arbiter.resolve({"device": "light", "domain": "lighting", "intent": "a"}, skill_priority=80)
        with freeze_time("2026-06-11 12:00:29"):
            arbiter.resolve({"device": "light", "domain": "lighting", "intent": "b"}, skill_priority=80)
        with freeze_time("2026-06-11 12:01:00"):
            intent_c = {"device": "light", "domain": "lighting", "intent": "c"}
            assert arbiter.resolve(intent_c, skill_priority=50) is intent_c


class TestEdgeCases:
    """异常输入和边界条件。"""

    def test_empty_device_key(self, arbiter):
        intent = {"device": "", "domain": "lighting", "intent": "on"}
        assert arbiter.resolve(intent) is intent

    def test_missing_device_key(self, arbiter):
        intent = {"domain": "lighting", "intent": "on"}
        assert arbiter.resolve(intent) is intent

    def test_empty_domain_key(self, arbiter):
        intent = {"device": "light", "domain": "", "intent": "on"}
        result = arbiter.resolve(intent)
        assert result is intent

    def test_invalid_priority_type_str(self, arbiter):
        """str 与 int 比较时抛出 TypeError（需先建立冲突记录）。"""
        intent = {"device": "light", "domain": "lighting", "intent": "on"}
        arbiter.resolve(intent, skill_priority=50)
        intent2 = {"device": "light", "domain": "lighting", "intent": "off"}
        with pytest.raises(TypeError):
            arbiter.resolve(intent2, skill_priority="high")

    def test_invalid_priority_type_none(self, arbiter):
        """None 与 int 比较时抛出 TypeError。"""
        intent = {"device": "light", "domain": "lighting", "intent": "on"}
        arbiter.resolve(intent, skill_priority=50)
        intent2 = {"device": "light", "domain": "lighting", "intent": "off"}
        with pytest.raises(TypeError):
            arbiter.resolve(intent2, skill_priority=None)

    def test_intent_is_none(self, arbiter):
        with pytest.raises(AttributeError):
            arbiter.resolve(None)


class TestConcurrency:
    """并发安全测试。"""

    def test_concurrent_resolve_thread_safety(self, arbiter):
        """10 线程并发调用 resolve()，验证内部 deque 不损坏。"""
        devices = [f"device_{i}" for i in range(5)]
        intents_list = ["on", "off", "toggle"]

        def worker():
            for _ in range(20):
                d = random.choice(devices)
                intent = {"device": d, "domain": "lighting",
                          "intent": random.choice(intents_list)}
                arbiter.resolve(intent, skill_priority=random.randint(1, 100))
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            futures = [ex.submit(worker) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(results)
        assert arbiter.history.maxlen == 50
        assert len(arbiter.history) <= 50


class TestGetRecent:
    """冲突历史查询。"""

    @freeze_time("2026-06-11 12:00:00")
    def test_get_recent_by_device(self, arbiter):
        arbiter.resolve({"device": "a", "domain": "x", "intent": "on"}, skill_name="s1")
        arbiter.resolve({"device": "b", "domain": "x", "intent": "off"}, skill_name="s2")
        result = arbiter.get_recent(device_id="a")
        assert len(result) == 1
        assert result[0]["device_id"] == "a"

    def test_get_recent_empty_when_no_conflicts(self, arbiter):
        assert arbiter.get_recent() == []


class TestArbiterHypothesis:
    """随机组合冲突验证不变性。

    注意：每个测试方法内部创建独立的 ConflictArbiter 实例，
    避免 @given 多次调用间状态泄漏。
    """

    @given(
        priorities=st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=2, max_size=10
        ),
    )
    def test_priority_ordering_invariance(self, priorities):
        """
        不变性：高优先级覆盖低优先级后，低优先级操作被拒绝。

        注意：按优先级降序处理，确保最高优先级最先调用（否则第一个
        调用因为历史为空总是会放行，导致测试失败）。
        """
        arbiter = ConflictArbiter(history_size=50)
        sorted_priorities = sorted(priorities, reverse=True)
        device_intent = {"device": "light", "domain": "lighting", "intent": "set"}
        for p in sorted_priorities:
            result = arbiter.resolve(dict(device_intent), skill_priority=p)
            if p == max(priorities):
                assert result is not None, f"Highest priority {p} should pass"
            else:
                assert result is None, f"Lower priority {p} should be blocked (max={max(priorities)})"

    @given(
        n_toggles=st.integers(min_value=0, max_value=6),
    )
    def test_oscillation_budget(self, n_toggles):
        """
        不变性：同优先级 30 秒窗口内交替操作时，第 3 次起每 2 次
        阻挡 1 次（因为阻挡时记录不写入历史，下一次调用恢复通过）。

        模式: on(通), off(通), on(通), off(阻), on(通), off(阻), ...
        """
        arbiter = ConflictArbiter(history_size=50)
        results = []
        for i in range(n_toggles):
            intent_str = "on" if i % 2 == 0 else "off"
            intent = {"device": "light", "domain": "lighting", "intent": intent_str}
            result = arbiter.resolve(intent, skill_priority=50)
            results.append(result is not None)

        # 计算预期通过数：前 3 次总是通过，第 4 次开始每 2 次中
        # 1 次通过（阻挡不写记录，下一次调用恢复通过）
        if n_toggles <= 3:
            expected_passes = n_toggles
        else:
            extra = n_toggles - 3
            expected_passes = 3 + extra // 2
        assert sum(results) == expected_passes, (
            f"Expected {expected_passes} passes for {n_toggles} toggles, got {sum(results)} "
            f"(results: {results})"
        )

    @given(st.data())
    def test_user_always_wins_invariant(self, data):
        """不变性：任何冲突下 source='user' 均放行。"""
        arbiter = ConflictArbiter(history_size=50)
        device = data.draw(st.sampled_from(["light_a", "light_b"]))
        intent_str = data.draw(st.sampled_from(["on", "off", "toggle"]))
        priority = data.draw(st.integers(min_value=1, max_value=100))

        arbiter.resolve({"device": device, "domain": "lighting", "intent": "auto_1", "source": "auto"})
        user_intent = {"device": device, "domain": "lighting",
                       "intent": intent_str, "source": "user"}
        result = arbiter.resolve(user_intent, skill_priority=priority)
        assert result is user_intent

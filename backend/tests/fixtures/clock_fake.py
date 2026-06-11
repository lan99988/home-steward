"""Fake clock — freezegun wrapper for time-dependent tests."""

from datetime import datetime
import pytest
import freezegun


class FakeClock:
    """可控的时间工具，封装 freezegun。

    用法:
        clock.tick(seconds=30)  # 前进 30 秒
        clock.freeze("2026-01-01 12:00:00")  # 跳转到指定时间
    """

    def __init__(self, start_time: str = "2026-06-11 12:00:00"):
        self._frozen = freezegun.freeze_time(start_time)
        self._frozen.start()
        self._current = datetime.fromisoformat(start_time)

    def tick(self, seconds: float = 1):
        """让时间前进指定秒数。"""
        self._frozen.stop()
        from datetime import timedelta
        self._current += timedelta(seconds=seconds)
        self._frozen = freezegun.freeze_time(self._current.isoformat())
        self._frozen.start()

    def freeze(self, time_str: str):
        """跳转到指定时间。"""
        self._frozen.stop()
        self._current = datetime.fromisoformat(time_str)
        self._frozen = freezegun.freeze_time(time_str)
        self._frozen.start()

    def cleanup(self):
        """清理 freezegun 状态。"""
        self._frozen.stop()


@pytest.fixture
def fake_clock():
    """提供可控的 FakeClock 实例，测试结束后自动清理。"""
    clock = FakeClock()
    yield clock
    clock.cleanup()

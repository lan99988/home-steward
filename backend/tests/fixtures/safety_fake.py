"""Fake safety layer — configurable validate/execute behavior for testing."""

from typing import Any, Dict, Optional
import pytest


class FakeSafetyLayer:
    """模拟安全执行层。

    validate() 和 execute() 的行为可通过配置控制：

        safety.validate_should_pass = True   # validate 返回 intent 本身
        safety.validate_should_pass = False  # validate 返回 None（拒绝）
        safety.execute_should_fail = True    # execute 返回 {"success": False}
    """

    def __init__(self):
        self.validate_should_pass: bool = True
        self.execute_should_fail: bool = False
        self.validate_calls: list = []
        self.execute_calls: list = []

    def validate(self, intent: Dict) -> Optional[Dict]:
        """模拟意图校验。"""
        self.validate_calls.append(intent)
        if self.validate_should_pass:
            return intent
        return None

    async def execute(self, validated: Dict) -> Dict:
        """模拟执行。"""
        self.execute_calls.append(validated)
        if self.execute_should_fail:
            return {"success": False, "error": "simulated_failure"}
        return {"success": True, "result": "simulated_ok"}

    def clear_history(self):
        """清空调用记录。"""
        self.validate_calls.clear()
        self.execute_calls.clear()


@pytest.fixture
def fake_safety_layer():
    """提供 FakeSafetyLayer 实例。"""
    return FakeSafetyLayer()

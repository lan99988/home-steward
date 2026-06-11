"""Runtime fixture — Skill 运行时实例，依赖显式注入。"""

from typing import Optional, Dict
import pytest
from app.skill.runtime import Skill


class TestRuntime:
    """模拟 Skill 运行时的轻量封装，用于 execute() 测试。

    不依赖文件系统，直接操作 Skill 实例。
    """

    def __init__(self, skill: Skill):
        self.skill = skill
        self.execution_history: list = []

    async def execute(self, intent: Dict, context: Optional[Dict] = None) -> Dict:
        """执行 Skill，记录执行历史。"""
        result = await self.skill.execute(intent, context or {})
        self.execution_history.append({
            "intent": intent,
            "result": result,
        })
        return result

    async def execute_raw(self, handler, intent: Dict, context: Optional[Dict] = None) -> Dict:
        """直接执行 handler 函数（绕过 Skill 对象），用于测试非标准 handler 行为。"""
        if not callable(handler):
            return {"error": "no_handler"}
        try:
            result = handler(intent, context or {})
            if __import__('inspect').isawaitable(result):
                result = await result
            return result or {"ok": True}
        except Exception as e:
            return {"error": str(e)}


@pytest.fixture
def runtime(fake_skill) -> TestRuntime:
    """返回绑定到 fake_skill 的 TestRuntime 实例。"""
    return TestRuntime(fake_skill)

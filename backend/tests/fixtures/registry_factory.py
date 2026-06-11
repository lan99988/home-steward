"""Registry fixture — 空 SkillRegistry 实例，不预注册任何 Skill。"""

import pytest
from app.skill.registry import SkillRegistry


@pytest.fixture
def registry():
    """返回一个空的 SkillRegistry 实例。

    设计原则: 不预注册任何 Skill，测试自行通过 registry.install() 控制状态。
    这样 install/uninstall 的前后状态对比测试可以精确验证。"""
    return SkillRegistry()

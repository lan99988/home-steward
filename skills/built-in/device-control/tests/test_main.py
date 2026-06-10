"""device-control Skill 测试"""

import pytest


@pytest.mark.asyncio
async def test_handle_turn_on():
    """测试打开设备"""
    from skills.built_in.device_control.main import handle
    result = await handle(
        {"intent": "turn_on", "device": "light_living"},
        {"safety_layer": None},
    )
    assert "error" in result  # 没有 safety_layer 时应有错误


@pytest.mark.asyncio
async def test_handle_turn_off():
    """测试关闭设备"""
    from skills.built_in.device_control.main import handle
    result = await handle(
        {"intent": "turn_off", "device": "light_living"},
        {"safety_layer": None},
    )
    assert "error" in result

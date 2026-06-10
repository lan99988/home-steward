"""引导引擎——安装即用的场景包，零冷启动"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class BootstrapScenario:
    """预置场景定义"""
    name: str
    description: str
    steps: List[Dict[str, Any]]


BOOTSTRAP_SCENARIOS = {
    "离家模式": BootstrapScenario(
        name="离家模式",
        description="一键关闭所有灯光和空调",
        steps=[
            {"intent": "all_lights", "action": "turn_off"},
            {"intent": "turn_off", "device": "ac_living"},
        ]
    ),
    "回家模式": BootstrapScenario(
        name="回家模式",
        description="打开客厅灯（40% 亮度）",
        steps=[
            {"intent": "turn_on", "device": "light_living",
             "brightness": 40},
        ]
    ),
    "睡眠模式": BootstrapScenario(
        name="睡眠模式",
        description="关闭所有灯，空调设为睡眠模式",
        steps=[
            {"intent": "all_lights", "action": "turn_off"},
            {"intent": "set_mode", "device": "ac_living", "mode": "sleep"},
        ]
    ),
    "早安模式": BootstrapScenario(
        name="早安模式",
        description="卧室灯渐亮",
        steps=[
            {"intent": "turn_on", "device": "light_bedroom",
             "brightness": "gradual"},
        ]
    ),
}


class BootstrapEngine:
    """安装即用的场景引擎——用户第一天就能用"""

    def __init__(self, safety_layer):
        self.scenarios = BOOTSTRAP_SCENARIOS
        self.safety_layer = safety_layer

    def get_scenarios(self) -> dict:
        """返回所有可用场景"""
        return {
            k: {"name": v.name, "description": v.description}
            for k, v in self.scenarios.items()
        }

    async def execute(self, scenario_name: str) -> Dict[str, Any]:
        """执行场景中的每一步"""
        scenario = self.scenarios.get(scenario_name)
        if not scenario:
            return {"error": f"未知场景: {scenario_name}"}

        results = []
        for step in scenario.steps:
            validated = self.safety_layer.validate(step)
            if validated:
                result = await self.safety_layer.execute(validated)
                results.append(result)
            else:
                results.append({"error": f"校验失败: {step}", "success": False})

        return {
            "scenario": scenario_name,
            "steps": results,
            "all_success": all(r.get("success", False) for r in results),
        }

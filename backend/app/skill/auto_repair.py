"""自动修复——健康度低于阈值时尝试 LLM 驱动的自动修复"""

import logging
from pathlib import Path
from typing import Optional

from app.skill.runtime import Skill
from app.skill.health import HealthMonitor
from app.skill.sandbox import RollbackSandbox

logger = logging.getLogger(__name__)


class AutoRepair:
    """Skill 自动修复流水线

    1. 收集诊断信息
    2. LLM 生成修复方案
    3. 在沙箱中验证修复
    4. 通知用户审批
    """

    def __init__(self, llm=None, health: HealthMonitor = None):
        self.llm = llm
        self.health = health
        self.sandbox = RollbackSandbox()

    async def attempt_repair(self, skill: Skill) -> bool:
        """尝试自动修复一个低健康度的 Skill"""
        score = self.health.get_health(skill.manifest.name) if self.health else 1.0

        if score > 0.5:
            logger.info(f"✅ Skill '{skill.manifest.name}' 健康 ({score:.1%})，无需修复")
            return True

        logger.warning(f"🔧 尝试自动修复 Skill '{skill.manifest.name}' (健康度 {score:.1%})")

        # 1. 收集诊断信息
        diagnostic = self._collect_diagnostic(skill)
        logger.info(f"📋 诊断: {len(diagnostic['failures'])} 条失败记录")

        # 2. 如果有 LLM，尝试生成修复
        if self.llm:
            fix_result = await self._generate_fix(skill, diagnostic)
            if fix_result:
                logger.info(f"✅ 自动修复成功: {skill.manifest.name}")
                return True
            logger.warning(f"❌ 自动修复失败: {skill.manifest.name}")

        # 3. 无 LLM 或修复失败 → 通知人工
        logger.info(f"📢 Skill '{skill.manifest.name}' 需要人工介入检查")
        return False

    def _collect_diagnostic(self, skill: Skill) -> dict:
        """收集诊断信息"""
        failures = []
        if self.health:
            failures = self.health.get_recent_failures(skill.manifest.name)
        return {
            "skill_name": skill.manifest.name,
            "version": skill.manifest.version,
            "health_score": self.health.get_health(skill.manifest.name) if self.health else 1.0,
            "failures": failures,
            "code_path": str(skill.path / "main.py"),
        }

    async def _generate_fix(self, skill: Skill, diagnostic: dict) -> bool:
        """用 LLM 生成修复方案（暂未完整实现）"""
        try:
            code = (skill.path / "main.py").read_text(encoding="utf-8")
            prompt = (
                f"Skill '{skill.manifest.name}' 健康度已降至 "
                f"{diagnostic['health_score']:.1%}。\n"
                f"最近失败: {diagnostic['failures']}\n\n"
                f"代码:\n```python\n{code}\n```\n\n"
                f"请分析问题并生成修复后的代码。"
            )
            # 实际场景中这里调用 LLM
            logger.debug(f"修复提示:\n{prompt[:200]}...")
            return False
        except Exception as e:
            logger.error(f"修复生成失败: {e}")
            return False

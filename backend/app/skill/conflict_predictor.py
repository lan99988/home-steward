"""冲突预测器——安装新 Skill 前预判冲突，而非事后检测"""

import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConflictWarning:
    """冲突警告"""
    with_skill: str
    domain: str
    probability: float
    suggestion: str


class ConflictPredictor:
    """安装前预测冲突

    在安装新 Skill 前，分析其 manifest 与已有 Skill 的域重叠，
    预判冲突概率并给出建议。
    """

    def predict(self, new_manifest: dict, existing_skills: list) -> List[ConflictWarning]:
        """预测新 Skill 与已有 Skill 的冲突"""
        warnings = []
        new_domains = {d["domain"] for d in new_manifest.get("domains", [])}

        for existing in existing_skills:
            if not hasattr(existing, "manifest"):
                continue
            existing_domains = {d["domain"] for d in existing.manifest.domains}
            overlap = new_domains & existing_domains

            for domain in overlap:
                prob = self._estimate_probability(
                    new_manifest, existing.manifest, domain
                )
                if prob > 0.3:
                    warnings.append(ConflictWarning(
                        with_skill=existing.manifest.name,
                        domain=domain,
                        probability=round(prob, 2),
                        suggestion=(
                            f"安装时设置合适的优先级，避免与 "
                            f"'{existing.manifest.name}' 在 {domain} 域冲突"
                        ),
                    ))
        return warnings

    def predict_skill_at_path(self, skill_path: Path,
                               existing_skills: list) -> List[ConflictWarning]:
        """对指定路径的 Skill 进行冲突预测"""
        try:
            import yaml
            manifest_path = skill_path / "SKILL.md"
            if not manifest_path.exists():
                return []

            content = manifest_path.read_text(encoding="utf-8")
            parts = content.split("---")
            if len(parts) < 2:
                return []

            manifest = yaml.safe_load(parts[1])
            if not manifest:
                return []

            return self.predict(manifest, existing_skills)
        except Exception as e:
            logger.error(f"冲突预测失败: {e}")
            return []

    def _estimate_probability(self, new_mf: dict, existing_mf, domain: str) -> float:
        """估算冲突概率"""
        prob = 0.5  # 基准

        # 冲突解决策略降低概率
        if new_mf.get("conflict_resolution") == "yield_on_user":
            prob -= 0.2
        if getattr(existing_mf, "conflict_resolution", "") == "yield_on_user":
            prob -= 0.1

        # 优先级差距降低概率
        new_pri = new_mf.get("priority", 50)
        old_pri = getattr(existing_mf, "priority", 50)
        pri_gap = abs(new_pri - old_pri)
        if pri_gap > 20:
            prob -= 0.2
        elif pri_gap > 10:
            prob -= 0.1

        return max(0.0, min(1.0, prob))

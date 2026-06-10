"""Skill 生态收敛——数量上限 + 自动归档 + 建议合并"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.skill.runtime import Skill

logger = logging.getLogger(__name__)


class SkillEcosystem:
    """Skill 生态管理器

    核心约束:
    - MAX_SKILLS: 硬上限（默认 20 个）
    - ARCHIVE_DAYS: 30 天未使用自动归档
    - 定期检查域重叠，建议合并相似 Skill
    """

    MAX_SKILLS = 20
    ARCHIVE_DAYS = 30

    def __init__(self):
        self.active_skills: Dict[str, Skill] = {}
        self.archived_skills: Dict[str, Skill] = {}

    def load_active(self, skills: Dict[str, Skill]):
        """从注册表加载活跃 Skill"""
        self.active_skills = dict(skills)

    def can_install(self, new_count: int = 1) -> bool:
        """是否还能安装新 Skill"""
        return (len(self.active_skills) + new_count) <= self.MAX_SKILLS

    def suggest_merge(self) -> List[dict]:
        """检测域重叠，建议合并"""
        suggestions = []
        skill_list = list(self.active_skills.values())

        for i in range(len(skill_list)):
            for j in range(i + 1, len(skill_list)):
                overlap = self._domain_overlap(skill_list[i], skill_list[j])
                if overlap:
                    suggestions.append({
                        "skill_a": skill_list[i].manifest.name,
                        "skill_b": skill_list[j].manifest.name,
                        "overlap": overlap,
                        "message": (
                            f"'{skill_list[i].manifest.name}' 和 "
                            f"'{skill_list[j].manifest.name}' "
                            f"在 {overlap} 域功能重叠，建议合并"
                        ),
                    })
        return suggestions

    def archive_unused(self):
        """归档 30 天未使用的 Skill"""
        now = datetime.now()
        to_archive = []

        for name, skill in self.active_skills.items():
            if skill.last_used and (now - skill.last_used).days > self.ARCHIVE_DAYS:
                to_archive.append(name)
            elif not skill.last_used and skill.execution_count == 0:
                # 从未使用过且安装超过 7 天
                to_archive.append(name)

        for name in to_archive:
            skill = self.active_skills.pop(name)
            self.archived_skills[name] = skill
            logger.info(f"📦 已归档未使用 Skill: '{name}'")

    def restore_from_archive(self, name: str) -> Optional[Skill]:
        """从归档恢复"""
        skill = self.archived_skills.pop(name, None)
        if skill:
            self.active_skills[name] = skill
            logger.info(f"♻️ 已恢复 Skill: '{name}'")
        return skill

    def get_stats(self) -> dict:
        """获取生态统计"""
        return {
            "active": len(self.active_skills),
            "archived": len(self.archived_skills),
            "max": self.MAX_SKILLS,
            "remaining": self.MAX_SKILLS - len(self.active_skills),
        }

    def _domain_overlap(self, a: Skill, b: Skill) -> Optional[str]:
        """检测两个 Skill 的域重叠"""
        a_domains = {d["domain"] for d in a.manifest.domains}
        b_domains = {d["domain"] for d in b.manifest.domains}
        overlap = a_domains & b_domains
        return list(overlap)[0] if overlap else None

"""Skill API 路由"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.skill.registry import SkillRegistry
from app.skill.runtime import Skill
from app.skill.conflict_predictor import ConflictPredictor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills"])

# 运行时注入
registry: SkillRegistry = None
conflict_predictor: ConflictPredictor = None


class SkillInfo(BaseModel):
    name: str
    version: str
    description: str
    priority: int
    domains: list
    enabled: bool
    health_score: float


class InstallRequest(BaseModel):
    source_path: str


@router.get("/", response_model=List[SkillInfo])
async def list_skills():
    """获取所有已安装的 Skill"""
    return [
        SkillInfo(
            name=s.manifest.name,
            version=s.manifest.version,
            description=s.manifest.description or "",
            priority=s.manifest.priority,
            domains=s.manifest.domains,
            enabled=s.enabled,
            health_score=s.health_score,
        )
        for s in registry.skills.values()
    ]


@router.get("/{skill_name}", response_model=SkillInfo)
async def get_skill(skill_name: str):
    """获取单个 Skill 详情"""
    skill = registry.get(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 未找到")
    return SkillInfo(
        name=skill.manifest.name,
        version=skill.manifest.version,
        description=skill.manifest.description or "",
        priority=skill.manifest.priority,
        domains=skill.manifest.domains,
        enabled=skill.enabled,
        health_score=skill.health_score,
    )


@router.post("/install")
async def install_skill(req: InstallRequest):
    """安装新 Skill"""
    from pathlib import Path
    source = Path(req.source_path)
    if not source.exists():
        raise HTTPException(status_code=400, detail=f"路径不存在: {req.source_path}")

    # 冲突预测
    if conflict_predictor:
        warnings = conflict_predictor.predict_skill_at_path(source, list(registry.skills.values()))
        if warnings:
            return {
                "status": "warnings",
                "message": "检测到潜在冲突",
                "warnings": [
                    {"with_skill": w.with_skill, "domain": w.domain,
                     "probability": w.probability, "suggestion": w.suggestion}
                    for w in warnings
                ],
            }

    skill = registry.install(source)
    return {
        "status": "installed",
        "skill": skill.manifest.name,
        "version": skill.manifest.version,
    }


@router.delete("/{skill_name}")
async def uninstall_skill(skill_name: str):
    """卸载 Skill"""
    success = registry.uninstall(skill_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 未找到")
    return {"status": "uninstalled", "skill": skill_name}


@router.post("/{skill_name}/toggle")
async def toggle_skill(skill_name: str, enable: bool = True):
    """启用/禁用 Skill"""
    skill = registry.get(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' 未找到")
    skill.enabled = enable
    return {"status": "enabled" if enable else "disabled", "skill": skill_name}

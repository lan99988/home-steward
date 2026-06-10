"""Skill 数据库模型"""

from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base


class SkillRecord(Base):
    """Skill 注册表"""
    __tablename__ = "skills"

    name = Column(String, primary_key=True)
    version = Column(String, nullable=False)
    description = Column(Text, default="")
    priority = Column(Integer, default=50)
    domains = Column(JSON, default=list)
    enabled = Column(Boolean, default=True)
    health_score = Column(Integer, default=100)  # 0-100
    install_path = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class SkillVersion(Base):
    """Skill 版本历史"""
    __tablename__ = "skill_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    changelog = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())


class ConflictRecord(Base):
    """冲突记录"""
    __tablename__ = "conflicts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    intent_a = Column(String, nullable=False)
    skill_a = Column(String, nullable=False)
    intent_b = Column(String, nullable=True)
    skill_b = Column(String, nullable=True)
    resolution = Column(String, default="blocked")
    created_at = Column(DateTime, server_default=func.now())

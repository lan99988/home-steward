"""记忆数据库模型"""

from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Memory(Base):
    """长期记忆（结构化摘要）"""
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    summary = Column(Text, nullable=False)
    memory_type = Column(String, default="habit")  # habit, preference, insight
    domain = Column(String, nullable=True)
    confidence = Column(Float, default=0.5)
    source = Column(String, default="system")  # system, user, accelerator
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class Insight(Base):
    """系统洞察（从记忆分析中提取的更高层认知）"""
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    category = Column(String, default="pattern")  # pattern, anomaly, suggestion
    confidence = Column(Float, default=0.5)
    related_events = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())

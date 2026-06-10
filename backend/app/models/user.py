"""用户数据库模型"""

from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    """用户账号"""
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(String, default="member")  # owner, member, guest
    preferences = Column(JSON, default=dict)
    voice_embedding = Column(String, nullable=True)  # base64 编码的声纹
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

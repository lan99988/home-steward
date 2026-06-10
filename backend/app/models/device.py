"""设备数据库模型"""

from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class Device(Base):
    """设备注册表"""
    __tablename__ = "devices"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # light, ac, switch, sensor...
    room = Column(String, default="unknown")
    protocol = Column(String, default="mqtt")  # mqtt, zigbee, ir...
    is_virtual = Column(Boolean, default=True)
    properties = Column(JSON, default=dict)
    online = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class DeviceState(Base):
    """设备状态缓存"""
    __tablename__ = "device_states"

    device_id = Column(String, primary_key=True)
    status = Column(String, default="unknown")  # online, offline, unknown
    properties = Column(JSON, default=dict)
    last_seen = Column(DateTime, server_default=func.now())
    cached_at = Column(DateTime, server_default=func.now())


class CommandLog(Base):
    """操作审计日志"""
    __tablename__ = "commands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, nullable=False)
    intent = Column(String, nullable=False)
    source = Column(String, default="user")  # user, skill, system
    parameters = Column(JSON, default=dict)
    success = Column(Boolean, default=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

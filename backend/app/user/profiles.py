"""用户画像——多用户偏好管理"""

import hashlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class UserProfile:
    """单个用户的完整画像"""

    def __init__(self, user_id: str, name: str):
        self.user_id = user_id
        self.name = name
        self.preferences: Dict[str, Any] = {
            "climate": {"temperature": 24, "mode": "cool"},
            "light": {"brightness": 70, "color_temp": 4000},
        }
        self.role: str = "member"  # owner | member | guest
        self.voice_embedding: Optional[list] = None

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "role": self.role,
            "preferences": self.preferences,
        }


class UserManager:
    """多用户管理器——用户注册、识别、偏好解析"""

    def __init__(self):
        self.users: Dict[str, UserProfile] = {}
        self._last_active: Optional[str] = None

    def add_user(self, user_id: str, name: str, role: str = "member") -> UserProfile:
        """添加用户"""
        if user_id in self.users:
            logger.warning(f"用户 {user_id} 已存在")
        user = UserProfile(user_id, name)
        user.role = role
        self.users[user_id] = user
        logger.info(f"👤 已添加用户: {name} ({user_id}, {role})")
        return user

    def get_user(self, user_id: str) -> Optional[UserProfile]:
        return self.users.get(user_id)

    def set_last_active(self, user_id: str):
        """记录最近活跃用户"""
        if user_id in self.users:
            self._last_active = user_id

    def get_last_active(self, max_minutes: int = 30) -> Optional[UserProfile]:
        """获取最近活跃用户"""
        if self._last_active:
            return self.users.get(self._last_active)
        return None

    def resolve_preference(self, domain: str,
                           current_user: Optional[str] = None) -> Any:
        """解析某个域的用户偏好"""
        if current_user and current_user in self.users:
            return self.users[current_user].preferences.get(domain, {})

        last_active = self.get_last_active()
        if last_active:
            return last_active.preferences.get(domain, {})

        # 默认值
        defaults = {
            "climate": {"temperature": 24, "mode": "cool"},
            "light": {"brightness": 70, "color_temp": 4000},
        }
        return defaults.get(domain, {})

    def list_users(self) -> list:
        return [u.to_dict() for u in self.users.values()]

    def remove_user(self, user_id: str) -> bool:
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False

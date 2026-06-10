"""设备抽象层——所有设备的统一接口"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DeviceAdapter(ABC):
    """所有设备的抽象基类"""

    def __init__(self, device_id: str, name: str, mqtt_client=None):
        self.device_id = device_id
        self.name = name
        self.mqtt = mqtt_client
        self.status: Dict[str, Any] = {}

    @abstractmethod
    async def turn_on(self, **kwargs) -> bool:
        """打开设备"""

    @abstractmethod
    async def turn_off(self, **kwargs) -> bool:
        """关闭设备"""

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """获取设备状态"""

    def _publish_status(self):
        """发布状态到 MQTT"""
        if self.mqtt:
            self.mqtt.publish(f"steward/{self.device_id}/status", self.status)


class VirtualLight(DeviceAdapter):
    """虚拟灯——用于开发测试"""

    async def turn_on(self, **kwargs) -> bool:
        self.status["on"] = True
        if "brightness" in kwargs:
            self.status["brightness"] = min(int(kwargs["brightness"]), 100)
        if "color_temp" in kwargs:
            self.status["color_temp"] = int(kwargs["color_temp"])
        logger.info(f"💡 {self.name} 已打开"
                    f"(亮度={self.status.get('brightness', 'default')})")
        self._publish_status()
        return True

    async def turn_off(self, **kwargs) -> bool:
        self.status["on"] = False
        logger.info(f"💡 {self.name} 已关闭")
        self._publish_status()
        return True

    async def get_status(self) -> Dict[str, Any]:
        return self.status

    async def set_brightness(self, value: int) -> bool:
        return await self.turn_on(brightness=value)

    async def set_color_temp(self, value: int) -> bool:
        return await self.turn_on(color_temp=value)


class VirtualAC(DeviceAdapter):
    """虚拟空调"""

    async def turn_on(self, **kwargs) -> bool:
        self.status["on"] = True
        self.status["mode"] = kwargs.get("mode", "cool")
        self.status["temperature"] = kwargs.get("temperature", 24)
        logger.info(f"❄️ {self.name} 已打开 ({self.status['mode']}, {self.status['temperature']}°C)")
        self._publish_status()
        return True

    async def turn_off(self, **kwargs) -> bool:
        self.status["on"] = False
        logger.info(f"❄️ {self.name} 已关闭")
        self._publish_status()
        return True

    async def get_status(self) -> Dict[str, Any]:
        return self.status

    async def set_temperature(self, value: int) -> bool:
        self.status["temperature"] = value
        logger.info(f"❄️ {self.name} 温度设为 {value}°C")
        self._publish_status()
        return True

    async def set_mode(self, mode: str) -> bool:
        self.status["mode"] = mode
        logger.info(f"❄️ {self.name} 模式设为 {mode}")
        self._publish_status()
        return True


class VirtualCurtain(DeviceAdapter):
    """虚拟窗帘"""

    async def turn_on(self, **kwargs) -> bool:
        return await self.set_position(kwargs.get("position", 100))

    async def turn_off(self, **kwargs) -> bool:
        return await self.set_position(0)

    async def get_status(self) -> Dict[str, Any]:
        return self.status

    async def set_position(self, position: int) -> bool:
        position = max(0, min(100, position))
        self.status["position"] = position
        self.status["on"] = position > 0
        logger.info(f"🪟 {self.name} 开合度设为 {position}%")
        self._publish_status()
        return True


DEVICE_TYPE_MAP = {
    "light": VirtualLight,
    "ac": VirtualAC,
    "curtain": VirtualCurtain,
}


def create_device(device_type: str, device_id: str, name: str, mqtt=None) -> Optional[DeviceAdapter]:
    """工厂方法：根据设备类型创建设备实例"""
    cls = DEVICE_TYPE_MAP.get(device_type)
    if cls:
        return cls(device_id, name, mqtt)
    logger.warning(f"未知设备类型: {device_type}")
    return None

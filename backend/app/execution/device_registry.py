"""设备注册表——管理所有设备实例"""

import logging
from typing import Dict, Optional, List

from app.execution.device import DeviceAdapter, create_device

logger = logging.getLogger(__name__)


class DeviceRegistry:
    """设备注册表：管理所有设备实例的注册、查找和生命周期"""

    def __init__(self):
        self.devices: Dict[str, DeviceAdapter] = {}

    def register(self, device: DeviceAdapter) -> bool:
        """注册一个设备"""
        if device.device_id in self.devices:
            logger.warning(f"设备 {device.device_id} 已存在，将被覆盖")
        self.devices[device.device_id] = device
        logger.info(f"已注册设备: {device.name} ({device.device_id})")
        return True

    def register_virtual_devices(self, mqtt=None):
        """注册开发测试用的虚拟设备"""
        devices_config = [
            {"id": "light_living", "name": "客厅灯", "type": "light"},
            {"id": "light_bedroom", "name": "卧室灯", "type": "light"},
            {"id": "light_kitchen", "name": "厨房灯", "type": "light"},
            {"id": "ac_living", "name": "客厅空调", "type": "ac"},
            {"id": "curtain_living", "name": "客厅窗帘", "type": "curtain"},
        ]
        for cfg in devices_config:
            device = create_device(cfg["type"], cfg["id"], cfg["name"], mqtt)
            if device:
                self.register(device)

    def get(self, device_id: str) -> Optional[DeviceAdapter]:
        """根据设备 ID 获取设备"""
        return self.devices.get(device_id)

    def remove(self, device_id: str) -> bool:
        """移除设备"""
        if device_id in self.devices:
            del self.devices[device_id]
            return True
        return False

    def list(self) -> List[dict]:
        """列出所有设备"""
        return [
            {
                "id": did,
                "name": d.name,
                "type": d.__class__.__name__.replace("Virtual", "").lower(),
            }
            for did, d in self.devices.items()
        ]

    def find_by_name(self, name: str) -> Optional[DeviceAdapter]:
        """通过名称模糊查找设备"""
        for device in self.devices.values():
            if name in device.name or name in device.device_id:
                return device
        return None

    def get_devices_by_type(self, device_type: str) -> List[DeviceAdapter]:
        """按类型获取设备"""
        return [d for d in self.devices.values()
                if d.__class__.__name__.lower().find(device_type) >= 0]

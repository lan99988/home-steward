"""设备发现服务——自动发现网络中的新设备"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredDevice:
    """自动发现的设备信息"""
    serial: str
    type: str
    model: str
    ip: str
    protocol: str = "mqtt"
    capabilities: List[str] = field(default_factory=list)
    name: str = ""


class DiscoveryService:
    """设备发现服务：扫描网络 → Web UI 通知 → 用户确认注册"""

    def __init__(self):
        self.pending: List[DiscoveredDevice] = []
        self.registered_serials: set = set()
        self._on_discover_callbacks: List[Callable] = []
        self._scanning = False

    def on_discover(self, callback: Callable):
        """注册发现回调（用于 WebSocket 推送）"""
        self._on_discover_callbacks.append(callback)

    async def scan(self, interval: int = 30):
        """持续扫描网络中的新设备"""
        self._scanning = True
        logger.info("📡 设备发现服务启动（每 %ds 扫描一次）", interval)
        while self._scanning:
            try:
                discovered = await self._mdns_scan()
                for device in discovered:
                    if device.serial not in self.registered_serials:
                        self.pending.append(device)
                        logger.info(f"📡 发现新设备: {device.type} ({device.serial})")
                        for cb in self._on_discover_callbacks:
                            try:
                                await cb(device)
                            except Exception:
                                pass
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"设备扫描异常: {e}")
                await asyncio.sleep(interval)

    def stop(self):
        """停止扫描"""
        self._scanning = False

    async def _mdns_scan(self) -> List[DiscoveredDevice]:
        """模拟 mDNS 扫描（实际使用 zeroconf 库）"""
        # Phase 1 暂用模拟返回
        return []

    def get_pending(self) -> List[DiscoveredDevice]:
        """获取待注册设备"""
        return list(self.pending)

    def register(self, serial: str) -> Optional[DiscoveredDevice]:
        """用户确认注册设备"""
        for device in self.pending:
            if device.serial == serial:
                self.registered_serials.add(serial)
                self.pending.remove(device)
                return device
        return None

    def reject(self, serial: str):
        """用户拒绝注册"""
        self.pending = [d for d in self.pending if d.serial != serial]

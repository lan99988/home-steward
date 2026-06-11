"""Fake MQTT client — records all publish/subscribe events for verification."""

from dataclasses import dataclass, field
from typing import List, Optional, Callable
from datetime import datetime
import pytest


@dataclass
class MQTTCall:
    """记录一次 MQTT 操作。"""
    method: str          # "publish" | "subscribe" | "connect" | "disconnect"
    topic: Optional[str] = None
    payload: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class FakeMQTTClient:
    """模拟 MQTT 客户端，记录所有操作到 events 列表。

    用法:
        client = FakeMQTTClient()
        client.publish("home/light", "on")
        assert client.events[0].method == "publish"

    可配置行为:
        client.should_fail_on_publish = True  # publish 调用会抛异常
        client.connected = False              # 模拟断线
    """

    def __init__(self):
        self.events: List[MQTTCall] = []
        self.connected: bool = True
        self.should_fail_on_publish: bool = False
        self.should_fail_on_subscribe: bool = False
        self._message_handler: Optional[Callable] = None

    def connect(self) -> bool:
        self.events.append(MQTTCall(method="connect"))
        self.connected = True
        return True

    def disconnect(self):
        self.events.append(MQTTCall(method="disconnect"))
        self.connected = False

    def publish(self, topic: str, payload: str, **kwargs) -> bool:
        if self.should_fail_on_publish:
            raise RuntimeError(f"MQTT publish failed: {topic}")
        self.events.append(MQTTCall(method="publish", topic=topic, payload=payload))
        return True

    def subscribe(self, topic: str, **kwargs) -> bool:
        if self.should_fail_on_subscribe:
            raise RuntimeError(f"MQTT subscribe failed: {topic}")
        self.events.append(MQTTCall(method="subscribe", topic=topic))
        return True

    def on_message(self, handler: Callable):
        self._message_handler = handler

    def clear_events(self):
        """清空事件记录（用于测试间隔离）。"""
        self.events.clear()


@pytest.fixture
def fake_mqtt_client():
    """提供 FakeMQTTClient 实例。"""
    return FakeMQTTClient()

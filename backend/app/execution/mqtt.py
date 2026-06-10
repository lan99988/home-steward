"""MQTT 通信层"""

import asyncio
import json
import logging
from typing import Callable, Dict, Any, Optional

from paho.mqtt import client as mqtt_client
from paho.mqtt.enums import CallbackAPIVersion

from app.core.config import settings

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT 客户端——设备通信枢纽"""

    def __init__(self, broker_host: str = None, broker_port: int = None):
        self.broker_host = broker_host or settings.mqtt_host
        self.broker_port = broker_port or settings.mqtt_port
        self.client = mqtt_client.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.subscribers: Dict[str, Callable] = {}
        self.connected = False
        self.message_count = 0
        self._loop = None

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info(f"✅ MQTT 已连接 ({self.broker_host}:{self.broker_port})")
            for topic in self.subscribers:
                client.subscribe(topic)
        else:
            logger.error(f"❌ MQTT 连接失败 (rc={rc})")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning("⚠️ MQTT 意外断开，即将重连...")

    def _on_message(self, client, userdata, msg):
        handler = self.subscribers.get(msg.topic)
        if handler:
            try:
                payload = json.loads(msg.payload.decode())
                self.message_count += 1
                # 尝试在已有事件循环中运行
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(handler(payload))
                    else:
                        asyncio.run(handler(payload))
                except RuntimeError:
                    asyncio.run(handler(payload))
            except Exception as e:
                logger.error(f"MQTT handler error: {e}")

    def connect(self):
        """连接 MQTT Broker"""
        try:
            self.client.connect(self.broker_host, self.broker_port)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"MQTT 连接异常: {e}")
            self.connected = False

    def publish(self, topic: str, payload: Dict[str, Any], qos: int = 1):
        """发布消息到 MQTT 主题"""
        if not self.connected:
            logger.warning(f"MQTT 未连接，无法发布到 {topic}")
            return False
        try:
            self.client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=qos)
            return True
        except Exception as e:
            logger.error(f"MQTT 发布失败: {e}")
            return False

    def subscribe(self, topic: str, handler: Callable):
        """订阅 MQTT 主题"""
        self.subscribers[topic] = handler
        if self.connected:
            self.client.subscribe(topic)
        logger.info(f"订阅 MQTT 主题: {topic}")

    def unsubscribe(self, topic: str):
        """取消订阅"""
        self.subscribers.pop(topic, None)
        if self.connected:
            self.client.unsubscribe(topic)

    def disconnect(self):
        """断开 MQTT 连接"""
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
        logger.info("MQTT 已断开")

"""标准通道：本地小模型推理（Ollama）"""

import json
import logging
from typing import Dict, Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LocalLLM:
    """本地模型推理客户端——由 ModelProvisioner 自动选择模型"""

    INTENT_SYSTEM_PROMPT = """你是一个智能家居管家。请将用户的指令解析为结构化意图。
只输出 JSON，不要多余文字。

输出格式:
{
  "intent": "turn_on|turn_off|set_temperature|set_brightness|set_mode|set_scene|unknown",
  "device": "设备名称（中文）",
  "domain": "light|climate|scene|curtain",
  "parameters": {}
}

示例:
用户说: "打开客厅灯" → {"intent": "turn_on", "device": "客厅灯", "domain": "light", "parameters": {}}
用户说: "把客厅弄得温馨一点" → {"intent": "set_scene", "device": "客厅", "domain": "scene", "parameters": {"scene": "cozy"}}
用户说: "空调调到26度" → {"intent": "set_temperature", "device": "空调", "domain": "climate", "parameters": {"temperature": 26}}
用户说: "好冷啊" → {"intent": "unknown", "device": "", "domain": "", "parameters": {}}
"""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or self._resolve_model()
        self.client = httpx.AsyncClient(timeout=120.0)
        self.healthy: Optional[bool] = None  # None=未检测, True=正常, False=不可达

    async def check_health(self) -> bool:
        """检测 Ollama 是否可达，3 秒超时"""
        if self.healthy is not None:
            return self.healthy
        try:
            resp = await self.client.get(
                f"{self.base_url}/api/tags",
                timeout=3.0,
            )
            self.healthy = resp.status_code == 200
            return self.healthy
        except Exception:
            self.healthy = False
            return False

    def _resolve_model(self) -> str:
        """从配置文件或自动探测获取当前激活的模型"""
        try:
            with open("data/active_model.json") as f:
                return json.load(f).get("model", "qwen3:3b")
        except (FileNotFoundError, json.JSONDecodeError):
            return "qwen3:3b"

    async def parse_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """将自然语言解析为结构化意图"""
        # 快速失败：Ollama 不可达时直接返回，避免 120s 超时
        if self.healthy is False:
            return None

        prompt = f"{self.INTENT_SYSTEM_PROMPT}\n用户说: \"{text}\"\n"
        try:
            resp = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,
                    "options": {"num_predict": 2048},
                },
                timeout=30.0,  # 从 120s 降到 30s
            )
            resp.raise_for_status()
            result = resp.json()
            response_text = result["response"].strip()
            return self._extract_json(response_text)
        except httpx.TimeoutException:
            logger.warning(f"LLM 超时（{self.model}），请检查 Ollama 是否运行")
            self.healthy = False
            return None
        except Exception as e:
            logger.error(f"LLM 解析失败: {e}")
            self.healthy = False
            return None

    def _extract_json(self, text: str) -> Optional[Dict]:
        """从 LLM 回复中提取 JSON"""
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 尝试提取 ```json ... ``` 包裹的内容
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            logger.error(f"无法从 LLM 回复中提取 JSON: {text[:100]}")
            return None

    async def close(self):
        await self.client.aclose()

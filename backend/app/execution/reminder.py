"""提醒系统——LLM 解析自然语言 → crontab 执行"""

import json
import logging
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

class Reminder:
    """一条提醒"""

    def __init__(self, rid: str, raw_text: str, parsed: Dict[str, Any]):
        self.id = rid
        self.raw_text = raw_text
        self.parsed = parsed
        self.created_at = datetime.now().isoformat()

    @property
    def cron_expr(self) -> str:
        """生成 cron 表达式"""
        p = self.parsed
        time_str = p.get("time", "08:00")
        hour, minute = time_str.split(":") if ":" in time_str else ("08", "00")
        repeat = p.get("repeat", "once")

        if repeat == "daily":
            return f"{minute} {hour} * * *"
        elif repeat == "weekdays":
            return f"{minute} {hour} * * 1-5"
        elif repeat == "weekends":
            return f"{minute} {hour} * * 6,0"
        elif repeat.startswith("weekly"):
            day_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 0, "天": 0}
            for k, v in day_map.items():
                if k in repeat:
                    return f"{minute} {hour} * * {v}"
            return f"{minute} {hour} * * 1"
        else:  # once
            return f"{minute} {hour} {datetime.now().day} {datetime.now().month} *"

    @property
    def command(self) -> str:
        """生成要执行的命令"""
        action = self.parsed.get("action", "")
        device = self.parsed.get("device", "")
        if action == "turn_on" and device:
            return f"curl -s -X POST http://localhost:8000/api/devices/command -H 'Content-Type: application/json' -d '{{\"text\":\"打开{device}\"}}'"
        if action == "turn_off" and device:
            return f"curl -s -X POST http://localhost:8000/api/devices/command -H 'Content-Type: application/json' -d '{{\"text\":\"关闭{device}\"}}'"
        if action == "set_temperature" and device:
            temp = self.parsed.get("value", 24)
            return f"curl -s -X POST http://localhost:8000/api/devices/command -H 'Content-Type: application/json' -d '{{\"text\":\"{device}调到{temp}度\"}}'"
        # 纯文本提醒
        message = self.parsed.get("message", self.raw_text)
        return f'echo "{message}"'

    def to_cron_entry(self) -> str:
        """生成 crontab 条目"""
        return f"{self.cron_expr} {self.command}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "raw_text": self.raw_text,
            "parsed": self.parsed,
            "cron": self.cron_expr,
            "created_at": self.created_at,
        }


# ============================================================
# LLM 解析器
# ============================================================

class ReminderParser:
    """将自然语言提醒解析为结构化 Reminder"""

    PROMPT = """解析用户的提醒/定时指令为结构化数据。只输出JSON。

示例:
用户说: "每天8点开灯"  
输出: {"action":"turn_on","device":"light_living","time":"08:00","repeat":"daily"}

用户说: "每晚10点关灯"
输出: {"action":"turn_off","device":"light_living","time":"22:00","repeat":"daily"}

用户说: "每周一早上7点开空调"
输出: {"action":"turn_on","device":"ac_living","time":"07:00","repeat":"weekly_一"}

用户说: "明天下午3点提醒我吃药"
输出: {"action":"remind","message":"吃药","time":"15:00","repeat":"once"}

用户说: "工作日8点半开灯"
输出: {"action":"turn_on","device":"light_living","time":"08:30","repeat":"weekdays"}

可能的action: turn_on, turn_off, set_temperature, remind
可能的repeat: once, daily, weekdays, weekends, weekly_X

只输出JSON，不要多余文字。"""

    def __init__(self, llm):
        self.llm = llm

    async def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """解析自然语言为结构化提醒"""
        prompt = f"{self.PROMPT}\n用户说: \"{text}\"\n"
        try:
            resp = await self.llm.client.post(
                f"{self.llm.base_url}/api/generate",
                json={
                    "model": self.llm.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,
                    "options": {"num_predict": 256},
                },
                timeout=60.0,
            )
            result = resp.json()
            raw = result["response"].strip()
            # 提取 JSON
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            return json.loads(raw.strip())
        except Exception as e:
            logger.error(f"提醒解析失败: {e}")
            return None


# ============================================================
# Cron 调度器
# ============================================================

class CronScheduler:
    """写入系统 crontab（Linux/macOS）或回退到文件存储"""

    STORAGE_PATH = Path("data/reminders.json")

    def __init__(self):
        self.STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._reminders: List[Reminder] = []
        self._load()

    def _load(self):
        """从文件加载提醒"""
        if self.STORAGE_PATH.exists():
            try:
                data = json.loads(self.STORAGE_PATH.read_text(encoding="utf-8"))
                for item in data:
                    r = Reminder(item["raw_text"], item["parsed"], "")
                    r.id = item["id"]
                    r.created_at = item.get("created_at", "")
                    self._reminders.append(r)
            except Exception:
                pass

    def _save(self):
        """保存提醒到文件"""
        self.STORAGE_PATH.write_text(
            json.dumps([r.to_dict() for r in self._reminders],
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add(self, reminder: Reminder) -> bool:
        """添加提醒并写入 crontab"""
        self._reminders.append(reminder)
        self._save()
        return self._write_cron()

    def remove(self, rid: str) -> bool:
        """删除提醒"""
        self._reminders = [r for r in self._reminders if r.id != rid]
        self._save()
        return self._write_cron()

    def list(self) -> List[dict]:
        """列出所有提醒"""
        return [r.to_dict() for r in self._reminders]

    def _write_cron(self) -> bool:
        """将提醒写入 crontab"""
        try:
            entries = [r.to_cron_entry() for r in self._reminders]
            # 添加 Home Steward 标识
            cron_content = "# Home Steward Agent Reminders\n"
            cron_content += "\n".join(entries) + "\n"

            if os.name == "posix":
                # Linux/macOS: 写入 crontab
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                    f.write(cron_content)
                    tmp_path = f.name
                result = subprocess.run(
                    ["crontab", tmp_path],
                    capture_output=True, text=True, timeout=10,
                )
                os.unlink(tmp_path)
                return result.returncode == 0
            else:
                # Windows 或不支持 crontab 的环境：文件存储即可
                logger.info("当前环境不支持 crontab，提醒已保存到文件")
                return True
        except FileNotFoundError:
            logger.info("crontab 不可用，提醒已保存到文件")
            return True
        except Exception as e:
            logger.warning(f"写入 crontab 失败: {e}")
            return True  # 文件已保存，不阻塞


# ============================================================
# 提醒 API 逻辑
# ============================================================

class ReminderService:
    """提醒服务——整合 LLM 解析 + 调度"""

    def __init__(self, llm):
        self.parser = ReminderParser(llm)
        self.scheduler = CronScheduler()
        self.counter = 0

    async def create_from_text(self, text: str) -> Optional[dict]:
        """从自然语言创建提醒"""
        parsed = await self.parser.parse(text)
        if not parsed:
            return None

        self.counter += 1
        reminder = Reminder(
            rid=f"rem_{int(datetime.now().timestamp())}_{self.counter}",
            raw_text=text,
            parsed=parsed,
        )
        ok = self.scheduler.add(reminder)
        return {
            "success": ok,
            "reminder": reminder.to_dict(),
        }

    def list_reminders(self) -> List[dict]:
        return self.scheduler.list()

    def delete_reminder(self, rid: str) -> bool:
        return self.scheduler.remove(rid)


# ============================================================
# 全局单例
# ============================================================

reminder_service: Optional[ReminderService] = None

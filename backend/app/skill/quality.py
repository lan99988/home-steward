"""AI 质量监测——持续评分系统智能程度，发现退化主动告警"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class QualityMonitor:
    """持续评分：AI 能力是否在退化

    每天跑一组标准测试用例，计算准确率，追踪趋势。
    如果连续 3 天下降超过 5% 则告警。
    """

    # 标准测试用例
    TEST_CASES = [
        ("打开客厅灯", {"intent": "turn_on"}),
        ("关闭空调", {"intent": "turn_off"}),
        ("空调调到26度", {"intent": "set_temperature"}),
        ("客厅亮度调到80", {"intent": "set_brightness"}),
        ("温馨一点", {"intent": "set_scene"}),
        ("离家模式", {"intent": "set_scene"}),
    ]

    def __init__(self, history_path: str = "data/quality_scores.json"):
        self.history_path = Path(history_path)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[float] = self._load_history()

    def _load_history(self) -> List[float]:
        if self.history_path.exists():
            try:
                return json.loads(self.history_path.read_text())
            except (json.JSONDecodeError, Exception):
                return []
        return []

    def _save_history(self):
        self.history_path.write_text(
            json.dumps(self.history[-90:]), encoding="utf-8"
        )

    async def run_daily_test(self, llm_router) -> float:
        """每天跑一组标准测试，计算准确率"""
        passed = 0
        for text, expected in self.TEST_CASES:
            try:
                _, result = await llm_router.route(text)
                if result and result.get("intent") == expected.get("intent"):
                    passed += 1
                else:
                    logger.warning(f"QA 失败: '{text}' → 期望 {expected.get('intent')}, 得到 {result}")
            except Exception as e:
                logger.error(f"QA 测试异常: {e}")

        score = passed / len(self.TEST_CASES) if self.TEST_CASES else 1.0
        self.history.append(score)
        self._save_history()
        logger.info(f"📊 日质量评分: {score:.0%} ({passed}/{len(self.TEST_CASES)})")
        return score

    def get_trend(self, days: int = 7) -> float:
        """最近 N 天的评分趋势（正数=上升，负数=下降）"""
        if len(self.history) < 2:
            return 0.0
        recent = self.history[-days:]
        if len(recent) < 2:
            return 0.0
        return recent[-1] - recent[0]

    def should_alert(self) -> bool:
        """如果连续 3 天下降超过 5% 则告警"""
        if len(self.history) < 4:
            return False
        recent_3 = self.history[-3:]
        if recent_3[0] > recent_3[1] > recent_3[2]:
            drop = recent_3[0] - recent_3[2]
            if drop > 0.05:
                logger.warning(f"⚠️ 质量连续下降 {drop:.1%}，建议检查系统")
                return True
        return False

    def get_latest_score(self) -> Optional[float]:
        """获取最新评分"""
        return self.history[-1] if self.history else None

    def get_history(self) -> List[float]:
        """获取完整历史"""
        return list(self.history)

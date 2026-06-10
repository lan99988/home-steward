"""健康监测——三层监测：被动 + 主动 + 集成"""

import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Skill 健康监测

    三层监测策略:
    1. 被动监测（每次调用时记录成功率、延迟）
    2. 主动监测（定时运行测试用例）
    3. 集成监测（跨 Skill 调用链检测）
    """

    def __init__(self):
        self.records: Dict[str, List[float]] = {}  # skill_name → [scores]
        self.latencies: Dict[str, List[float]] = {}  # skill_name → [latency_ms]
        self.failures: Dict[str, List[str]] = {}  # skill_name → [error messages]

    def record_execution(self, skill_name: str, success: bool,
                         latency_ms: float, error: str = None):
        """记录一次 Skill 执行"""
        # 评分
        score = 1.0 if success else 0.0
        if latency_ms > 2000:
            score *= 0.8  # 延迟惩罚
        if error:
            score *= 0.5

        if skill_name not in self.records:
            self.records[skill_name] = []
            self.latencies[skill_name] = []
            self.failures[skill_name] = []

        self.records[skill_name].append(score)
        self.latencies[skill_name].append(latency_ms)

        if error:
            self.failures[skill_name].append(error)

        # 只保留最近 100 次
        self.records[skill_name] = self.records[skill_name][-100:]
        self.latencies[skill_name] = self.latencies[skill_name][-100:]
        self.failures[skill_name] = self.failures[skill_name][-20:]

    def get_health(self, skill_name: str) -> float:
        """获取 Skill 健康评分 (0.0 - 1.0)"""
        scores = self.records.get(skill_name, [1.0])
        if not scores:
            return 1.0
        # 加权平均：最近记录权重更高
        total_weight = 0
        weighted_sum = 0
        for i, score in enumerate(scores):
            weight = (i + 1) / len(scores)  # 越近权重越高
            weighted_sum += score * weight
            total_weight += weight
        return weighted_sum / total_weight if total_weight > 0 else 1.0

    def get_latency_p99(self, skill_name: str) -> float:
        """获取 P99 延迟 (ms)"""
        latencies = sorted(self.latencies.get(skill_name, [0]))
        if not latencies:
            return 0
        idx = int(len(latencies) * 0.99)
        return latencies[min(idx, len(latencies) - 1)]

    def should_disable(self, skill_name: str) -> bool:
        """是否应自动禁用（健康度低于 0.5）"""
        return self.get_health(skill_name) < 0.5

    def get_success_rate(self, skill_name: str) -> float:
        """获取成功率"""
        scores = self.records.get(skill_name, [])
        if not scores:
            return 1.0
        return sum(1 for s in scores if s > 0.5) / len(scores)

    def get_recent_failures(self, skill_name: str, n: int = 5) -> List[str]:
        """获取最近 N 条失败记录"""
        return (self.failures.get(skill_name) or [])[-n:]

    def get_all_health(self) -> Dict[str, float]:
        """获取所有 Skill 的健康评分"""
        return {name: self.get_health(name) for name in self.records}

    def get_summary(self) -> Dict:
        """获取健康监测摘要"""
        summary = {}
        for name in self.records:
            summary[name] = {
                "health_score": round(self.get_health(name), 2),
                "success_rate": round(self.get_success_rate(name), 2),
                "p99_latency_ms": round(self.get_latency_p99(name), 1),
                "total_calls": len(self.records[name]),
                "recent_errors": len(self.failures.get(name, [])),
            }
        return summary

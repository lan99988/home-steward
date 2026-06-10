"""记忆持久化——三重冗余：SQLite + ChromaDB + JSON 快照日志"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryPersistence:
    """记忆持久化管理器

    三重冗余:
    1. SQLite 主存储（由 SQLAlchemy 管理）
    2. ChromaDB 向量索引（语义检索）
    3. JSON 追加日志（永不删除的审计轨迹）
    """

    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir = self.storage_dir / "snapshots"
        self.snapshot_dir.mkdir(exist_ok=True)
        self.max_snapshots = 30

    def save(self, memory: dict):
        """写三份：主存储 + 向量索引 + 追加日志"""
        # 1. SQLite 主存储（外部管理）
        # 2. ChromaDB 向量索引（外部管理）
        # 3. 追加 JSON 日志（永远不删）
        log_path = self.storage_dir / "memory_log.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(memory, ensure_ascii=False) + "\n")

    def create_snapshot(self):
        """创建可恢复的快照"""
        source = self.storage_dir / "long_term.json"
        if not source.exists():
            logger.warning("无长期记忆文件，跳过快照")
            return

        snapshot_path = (
            self.snapshot_dir
            / f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        shutil.copy(source, snapshot_path)
        logger.info(f"📸 记忆快照已创建: {snapshot_path.name}")

        # 清理旧快照
        snapshots = sorted(self.snapshot_dir.glob("snapshot_*.json"))
        for old in snapshots[:-self.max_snapshots]:
            old.unlink()
            logger.debug(f"删除旧快照: {old.name}")

    def restore(self, snapshot_name: str = "latest") -> bool:
        """从快照恢复记忆"""
        if snapshot_name == "latest":
            snapshots = sorted(self.snapshot_dir.glob("snapshot_*.json"))
            if not snapshots:
                logger.warning("无可用快照")
                return False
            source = snapshots[-1]
        else:
            source = self.snapshot_dir / snapshot_name

        if source.exists():
            shutil.copy(source, self.storage_dir / "long_term.json")
            logger.info(f"♻️ 记忆已从 {source.name} 恢复")
            return True
        logger.error(f"快照不存在: {snapshot_name}")
        return False

    def export_profile(self, path: str = "steward_profile.json") -> str:
        """导出完整用户画像（可迁移到新设备）"""
        profile = {
            "exported_at": datetime.now().isoformat(),
            "version": "1.0",
            "habits": {},
            "preferences": {},
        }

        long_term_path = self.storage_dir / "long_term.json"
        if long_term_path.exists():
            try:
                profile["habits"] = json.loads(long_term_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        prefs_path = self.storage_dir / "preferences.json"
        if prefs_path.exists():
            try:
                profile["preferences"] = json.loads(prefs_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        output_path = Path(path)
        output_path.write_text(
            json.dumps(profile, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"📦 用户画像已导出: {output_path}")
        return str(output_path)

    def import_profile(self, path: str) -> bool:
        """从导出文件导入用户画像"""
        source = Path(path)
        if not source.exists():
            logger.error(f"导入文件不存在: {path}")
            return False

        try:
            profile = json.loads(source.read_text(encoding="utf-8"))
            if profile.get("version") != "1.0":
                logger.warning(f"版本不匹配: {profile.get('version')}")
                return False

            # 写回长期记忆
            if profile.get("habits"):
                (self.storage_dir / "long_term.json").write_text(
                    json.dumps(profile["habits"], indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            # 写回偏好
            if profile.get("preferences"):
                (self.storage_dir / "preferences.json").write_text(
                    json.dumps(profile["preferences"], indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

            logger.info(f"📦 用户画像已导入: {path}")
            return True
        except Exception as e:
            logger.error(f"导入失败: {e}")
            return False

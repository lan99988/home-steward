"""Fake storage — in-memory persistence simulation for skill/registry/health data."""

import json
from pathlib import Path
from typing import Any, Dict, Optional
import pytest


class FakeStorage:
    """模拟文件持久化，全部在内存中操作，不写磁盘。

    提供与 json.load/json.dump 兼容的接口，
    用于 registry/quality/health 等模块的持久化模拟。
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._files: Dict[str, str] = {}

    def write_json(self, path: str, data: Any):
        """模拟写入 JSON 文件。"""
        self._files[path] = json.dumps(data, ensure_ascii=False)

    def read_json(self, path: str, default: Any = None) -> Optional[Any]:
        """模拟读取 JSON 文件。"""
        content = self._files.get(path)
        if content is None:
            return default
        return json.loads(content)

    def exists(self, path: str) -> bool:
        """模拟文件存在检查。"""
        return path in self._files

    def delete(self, path: str):
        """模拟文件删除。"""
        self._files.pop(path, None)

    def set_skill_data(self, skill_name: str, key: str, value: Any):
        """快捷设置 Skill 关联数据。"""
        if skill_name not in self._data:
            self._data[skill_name] = {}
        self._data[skill_name][key] = value

    def get_skill_data(self, skill_name: str, key: str, default: Any = None) -> Any:
        """快捷读取 Skill 关联数据。"""
        return self._data.get(skill_name, {}).get(key, default)

    def clear(self):
        """清空所有数据（用于测试间隔离）。"""
        self._data.clear()
        self._files.clear()


@pytest.fixture
def fake_storage():
    """提供内存中的 FakeStorage 实例，function-scoped。"""
    return FakeStorage()

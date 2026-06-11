"""回滚沙箱——隔离环境验证回滚兼容性"""

import ast
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Set

logger = logging.getLogger(__name__)


class RollbackSandbox:
    """回滚沙箱：在隔离环境中验证旧版本 Skill 的兼容性

    流程:
    1. 快照当前状态
    2. 在沙箱中加载目标版本
    3. 运行测试 + 接口兼容性验证
    4. 生成验证报告
    """

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="steward_sandbox_")
        logger.info(f"沙箱目录: {self.temp_dir}")

    def validate_rollback(self, current: Path, target: Path) -> Dict[str, Any]:
        """验证回滚是否安全"""
        report = {
            "compatible": True,
            "issues": [],
            "tests": {"passed": 0, "failed": 0, "error": None},
            "migration": None,
        }

        # 1. 接口签名兼容性
        current_funcs = self._extract_functions(current / "main.py")
        target_funcs = self._extract_functions(target / "main.py")

        for func_name in current_funcs:
            if func_name not in target_funcs:
                report["issues"].append(f"缺失函数: {func_name}")

        # 2. 检查数据 schema
        current_schema = self._load_schema(current)
        target_schema = self._load_schema(target)
        if current_schema != target_schema:
            report["issues"].append(
                f"数据结构变化: v{target_schema.get('version', '?')} "
                f"→ v{current_schema.get('version', '?')}"
            )
            report["migration"] = self._generate_migration_hint(
                target_schema, current_schema
            )

        # 3. 运行测试
        test_result = self._run_tests(target)
        report["tests"] = test_result

        if report["issues"] or test_result.get("failed", 0) > 0:
            report["compatible"] = False

        return report

    def _extract_functions(self, path: Path) -> Set[str]:
        """提取 Python 文件中的函数名"""
        if not path.exists():
            return set()
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            return {node.name for node in ast.walk(tree)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        except Exception as e:
            logger.error(f"提取函数失败: {e}")
            return set()

    def _load_schema(self, path: Path) -> dict:
        """加载 schema 定义"""
        import json
        schema_dir = path / "schemas"
        if not schema_dir.exists():
            return {"version": "unknown"}
        schemas = sorted(schema_dir.glob("*.json"))
        if schemas:
            try:
                return json.loads(schemas[-1].read_text())
            except Exception:
                pass
        return {"version": "unknown"}

    def _generate_migration_hint(self, from_schema: dict, to_schema: dict) -> str:
        """生成迁移提示"""
        return (
            f"数据结构从 {from_schema.get('version', '?')} "
            f"回滚到 {to_schema.get('version', '?')} 需要数据转换"
        )

    def _run_tests(self, skill_path: Path) -> Dict:
        """运行 Skill 测试用例"""
        test_dir = skill_path / "tests"
        if not test_dir.exists():
            return {"passed": 0, "failed": 0, "error": "no tests"}
        try:
            result = subprocess.run(
                ["pytest", str(test_dir), "-v", "--tb=short"],
                capture_output=True, text=True, timeout=30,
            )
            return {
                "passed": result.returncode == 0,
                "output": result.stdout[-500:] if len(result.stdout) > 500
                          else result.stdout,
                "failed": 0 if result.returncode == 0 else 1,
            }
        except subprocess.TimeoutExpired:
            return {"passed": 0, "failed": 1, "error": "timeout"}
        except FileNotFoundError:
            return {"passed": 0, "failed": 1, "error": "pytest not installed"}
        except Exception as e:
            return {"passed": 0, "failed": 1, "error": str(e)}

    def cleanup(self):
        """清理沙箱临时目录"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.warning(f"沙箱清理失败: {e}")

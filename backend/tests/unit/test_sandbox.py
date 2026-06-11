"""Test Suite for RollbackSandbox — 13 tests covering all methods and edge cases."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from app.skill.sandbox import RollbackSandbox


# =========================================================================
# Helpers
# =========================================================================


def _make_skill_dir(tmp_path, name, functions=None, schema=None, has_tests=False):
    """Create a minimal skill directory with a main.py containing given functions."""
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    funcs = functions or ["handle"]
    func_lines = "\n\n".join(
        f"async def {fn}(intent, ctx): return {{'ok': True}}" for fn in funcs
    )
    (skill_dir / "main.py").write_text(func_lines)

    if schema:
        schemas_dir = skill_dir / "schemas"
        schemas_dir.mkdir(exist_ok=True)
        (schemas_dir / "v1.json").write_text(json.dumps(schema))

    if has_tests:
        tests_dir = skill_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test_main.py").write_text("def test_dummy(): pass\n")

    return skill_dir


# =========================================================================
# Tests
# =========================================================================


class TestRollbackSandbox:
    """Tests for RollbackSandbox."""

    def test_sandbox_creates_temp_dir_on_init(self):
        """Verify temp_dir exists after init."""
        sb = RollbackSandbox()
        try:
            temp_path = Path(sb.temp_dir)
            assert temp_path.exists()
            assert temp_path.is_dir()
            assert "steward_sandbox" in sb.temp_dir
        finally:
            sb.cleanup()

    def test_cleanup_removes_temp_dir(self):
        """Verify cleanup deletes the temp directory."""
        sb = RollbackSandbox()
        temp_path = Path(sb.temp_dir)
        assert temp_path.exists()
        sb.cleanup()
        assert not temp_path.exists()

    def test_extract_functions_valid(self, tmp_path):
        """Parse real Python and find function names."""
        py_file = tmp_path / "main.py"
        py_file.write_text(
            "async def handle(intent, ctx): pass\n"
            "\n"
            "def _helper(data): pass\n"
            "\n"
            "class Foo:\n"
            "    def method(self): pass\n"
        )
        sb = RollbackSandbox()
        try:
            funcs = sb._extract_functions(py_file)
            assert "handle" in funcs
            assert "_helper" in funcs
            # ast.walk traverses class bodies too
            assert "method" in funcs
        finally:
            sb.cleanup()

    def test_extract_functions_empty_file(self, tmp_path):
        """No functions defined -> empty set."""
        py_file = tmp_path / "main.py"
        py_file.write_text("# just a comment\nx = 1\n")
        sb = RollbackSandbox()
        try:
            funcs = sb._extract_functions(py_file)
            assert funcs == set()
        finally:
            sb.cleanup()

    def test_extract_functions_file_not_found(self, tmp_path):
        """Missing file -> empty set."""
        missing = tmp_path / "does_not_exist.py"
        sb = RollbackSandbox()
        try:
            funcs = sb._extract_functions(missing)
            assert funcs == set()
        finally:
            sb.cleanup()

    def test_load_schema_no_schemas_dir(self, tmp_path):
        """No schemas/ directory -> version 'unknown'."""
        skill_dir = tmp_path / "noschema"
        skill_dir.mkdir()
        sb = RollbackSandbox()
        try:
            schema = sb._load_schema(skill_dir)
            assert schema == {"version": "unknown"}
        finally:
            sb.cleanup()

    def test_load_schema_with_json(self, tmp_path):
        """Create schemas dir with JSON, verify parsed content."""
        skill_dir = tmp_path / "withschema"
        skill_dir.mkdir()
        schemas_dir = skill_dir / "schemas"
        schemas_dir.mkdir()
        (schemas_dir / "v1.json").write_text(
            json.dumps({"version": "2.0", "fields": ["name", "age"]})
        )
        sb = RollbackSandbox()
        try:
            schema = sb._load_schema(skill_dir)
            assert schema["version"] == "2.0"
            assert "fields" in schema
        finally:
            sb.cleanup()

    def test_load_schema_invalid_json(self, tmp_path):
        """Malformed JSON -> version 'unknown'."""
        skill_dir = tmp_path / "badschema"
        skill_dir.mkdir()
        schemas_dir = skill_dir / "schemas"
        schemas_dir.mkdir()
        (schemas_dir / "bad.json").write_text("not valid json{{{")
        sb = RollbackSandbox()
        try:
            schema = sb._load_schema(skill_dir)
            assert schema == {"version": "unknown"}
        finally:
            sb.cleanup()

    def test_run_tests_no_tests_dir(self, tmp_path):
        """No tests/ directory -> no-test result."""
        skill_dir = tmp_path / "notests"
        skill_dir.mkdir()
        sb = RollbackSandbox()
        try:
            result = sb._run_tests(skill_dir)
            assert result["passed"] == 0
            assert result["failed"] == 0
            assert result["error"] == "no tests"
        finally:
            sb.cleanup()

    def test_run_tests_pytest_not_found(self, tmp_path):
        """Patch subprocess to raise FileNotFoundError."""
        skill_dir = tmp_path / "skill_with_tests"
        skill_dir.mkdir()
        tests_dir = skill_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_dummy.py").write_text("def test_x(): pass\n")

        sb = RollbackSandbox()
        try:
            with patch.object(subprocess, "run", side_effect=FileNotFoundError):
                result = sb._run_tests(skill_dir)
            assert result["passed"] == 0
            assert result["failed"] == 1
            assert "pytest not installed" in result.get("error", "")
        finally:
            sb.cleanup()

    def test_validate_rollback_compatible(self, tmp_path):
        """Same functions in both -> compatible."""
        current = _make_skill_dir(tmp_path, "current", functions=["handle"])
        target = _make_skill_dir(tmp_path, "target", functions=["handle"])
        sb = RollbackSandbox()
        try:
            report = sb.validate_rollback(current, target)
            assert report["compatible"] is True
            assert report["issues"] == []
        finally:
            sb.cleanup()

    def test_validate_rollback_missing_function(self, tmp_path):
        """Current has more functions than target -> issues."""
        current_dir = tmp_path / "current"
        current_dir.mkdir()
        (current_dir / "main.py").write_text(
            "async def handle(intent, ctx): return {'ok': True}\n\n"
            "async def process_data(intent, ctx): return {'ok': True}\n",
            encoding="utf-8"
        )
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "main.py").write_text(
            "async def handle(intent, ctx): return {'ok': True}\n",
            encoding="utf-8"
        )
        sb = RollbackSandbox()
        try:
            report = sb.validate_rollback(current_dir, target_dir)
            assert report["compatible"] is False
            assert any("process_data" in issue for issue in report["issues"])
        finally:
            sb.cleanup()

    def test_validate_rollback_schema_change(self, tmp_path):
        """Different schemas -> migration hint."""
        current = _make_skill_dir(
            tmp_path, "current",
            functions=["handle"],
            schema={"version": "2.0", "fields": ["name", "age"]},
        )
        target = _make_skill_dir(
            tmp_path, "target",
            functions=["handle"],
            schema={"version": "1.0", "fields": ["name"]},
        )
        sb = RollbackSandbox()
        try:
            report = sb.validate_rollback(current, target)
            assert report["compatible"] is False
            assert report["migration"] is not None
            assert "数据结构" in report["migration"]
            assert "1.0" in report["migration"]
            assert "2.0" in report["migration"]
        finally:
            sb.cleanup()

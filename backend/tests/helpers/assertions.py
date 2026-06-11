"""Custom assertion helpers for Skill system tests."""


def assert_arbiter_resolution(result, expected_intent):
    """断言仲裁结果与预期一致（result 为 intent 或 None）。"""
    if expected_intent is None:
        assert result is None, f"Expected None, got {result}"
    else:
        assert result is expected_intent, (
            f"Expected intent object to be returned, got {result}"
        )


def assert_skill_error(result, expected_error_key: str):
    """断言 Skill 执行返回指定错误 key。"""
    assert result is not None, "Expected error dict, got None"
    assert "error" in result, f"Expected 'error' key in result, got {result}"
    assert result["error"] == expected_error_key, (
        f"Expected error={expected_error_key!r}, got {result['error']!r}"
    )

"""Unit tests for the HookResult model."""

import pytest
from pydantic import ValidationError

from adw.models import HookResult


class TestHookResult:
    """Tests for HookResult model."""

    def test_successful_hook_result(self) -> None:
        """Test creating a successful hook result."""
        result = HookResult(
            stdout="Hello from hook",
            stderr="",
            exit_code=0,
            duration_ms=123,
            hook_type="pre",
        )

        assert result.stdout == "Hello from hook"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.duration_ms == 123
        assert result.hook_type == "pre"

    def test_failed_hook_result(self) -> None:
        """Test creating a failed hook result with non-zero exit code."""
        result = HookResult(
            stdout="",
            stderr="Error: command not found",
            exit_code=127,
            duration_ms=50,
            hook_type="post",
        )

        assert result.stdout == ""
        assert result.stderr == "Error: command not found"
        assert result.exit_code == 127
        assert result.duration_ms == 50
        assert result.hook_type == "post"

    def test_hook_result_with_both_streams(self) -> None:
        """Test hook result with both stdout and stderr."""
        result = HookResult(
            stdout="Processing...\nDone.",
            stderr="Warning: deprecated API",
            exit_code=0,
            duration_ms=500,
            hook_type="pre",
        )

        assert "Processing" in result.stdout
        assert "Warning" in result.stderr
        assert result.exit_code == 0

    def test_hook_type_validation(self) -> None:
        """Test that hook_type only accepts 'pre' or 'post'."""
        with pytest.raises(ValidationError):
            HookResult(
                stdout="",
                stderr="",
                exit_code=0,
                duration_ms=0,
                hook_type="invalid",
            )

    def test_duration_must_be_non_negative(self) -> None:
        """Test that duration_ms must be non-negative."""
        with pytest.raises(ValidationError):
            HookResult(
                stdout="",
                stderr="",
                exit_code=0,
                duration_ms=-1,
                hook_type="pre",
            )

    def test_hook_result_serialization(self) -> None:
        """Test that HookResult can be serialized to dict/JSON."""
        result = HookResult(
            stdout="output",
            stderr="",
            exit_code=0,
            duration_ms=100,
            hook_type="pre",
        )

        data = result.model_dump()
        assert data == {
            "stdout": "output",
            "stderr": "",
            "exit_code": 0,
            "duration_ms": 100,
            "hook_type": "pre",
        }

    def test_is_success_property(self) -> None:
        """Test the is_success computed property."""
        success = HookResult(
            stdout="ok",
            stderr="",
            exit_code=0,
            duration_ms=10,
            hook_type="pre",
        )
        assert success.is_success is True

        failure = HookResult(
            stdout="",
            stderr="error",
            exit_code=1,
            duration_ms=10,
            hook_type="post",
        )
        assert failure.is_success is False

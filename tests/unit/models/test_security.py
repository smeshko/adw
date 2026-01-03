"""Tests for security-related models.

Tests for ToolCallLog model that records tool execution during LLM interactions.
"""

from datetime import datetime, timezone

import pytest

from adw.models.security import ToolCallLog


class TestToolCallLog:
    """Test suite for ToolCallLog model."""

    def test_create_basic_tool_call_log(self) -> None:
        """Test creating a basic tool call log entry."""
        log = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Bash",
            arguments={"command": "npm test"},
            result_summary="Exit code: 0",
            duration_ms=2500,
        )

        assert log.tool_name == "Bash"
        assert log.arguments == {"command": "npm test"}
        assert log.result_summary == "Exit code: 0"
        assert log.duration_ms == 2500
        assert log.blocked is False
        assert log.block_reason is None
        assert log.phase is None

    def test_create_blocked_tool_call(self) -> None:
        """Test creating a blocked tool call log entry."""
        log = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Bash",
            arguments={"command": "rm -rf /"},
            result_summary=None,
            duration_ms=0,
            blocked=True,
            block_reason="Dangerous command pattern detected",
            phase="build",
        )

        assert log.blocked is True
        assert log.block_reason == "Dangerous command pattern detected"
        assert log.phase == "build"
        assert log.duration_ms == 0

    def test_tool_call_with_all_fields(self) -> None:
        """Test creating a tool call log with all fields populated."""
        log = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Read",
            arguments={"file_path": "/src/main.py", "limit": 100},
            result_summary="File read successfully, 150 lines",
            duration_ms=15,
            blocked=False,
            block_reason=None,
            phase="plan",
        )

        assert log.timestamp == "2026-01-03T10:30:00.123Z"
        assert log.tool_name == "Read"
        assert log.arguments["file_path"] == "/src/main.py"
        assert log.arguments["limit"] == 100
        assert log.result_summary == "File read successfully, 150 lines"
        assert log.duration_ms == 15
        assert log.blocked is False
        assert log.phase == "plan"

    def test_serialize_to_json(self) -> None:
        """Test serialization to JSON for JSONL file format."""
        log = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Bash",
            arguments={"command": "npm test", "timeout": 30000},
            result_summary="Exit code: 0, output: 15 tests passed",
            duration_ms=2500,
            blocked=False,
            block_reason=None,
            phase="build",
        )

        json_str = log.model_dump_json()
        assert '"tool_name":"Bash"' in json_str or '"tool_name": "Bash"' in json_str
        assert "npm test" in json_str
        assert "2500" in json_str

    def test_deserialize_from_json(self) -> None:
        """Test deserialization from JSON string."""
        json_str = """{
            "timestamp": "2026-01-03T10:30:00.123Z",
            "tool_name": "Write",
            "arguments": {"file_path": "/test.txt", "content": "hello"},
            "result_summary": "File written",
            "duration_ms": 5,
            "blocked": false,
            "block_reason": null,
            "phase": "build"
        }"""

        log = ToolCallLog.model_validate_json(json_str)

        assert log.tool_name == "Write"
        assert log.arguments["file_path"] == "/test.txt"
        assert log.duration_ms == 5
        assert log.blocked is False

    def test_arguments_default_to_empty_dict(self) -> None:
        """Test that arguments default to empty dict if not provided."""
        log = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Read",
            result_summary="Success",
            duration_ms=10,
        )

        assert log.arguments == {}

    def test_duration_ms_must_be_non_negative(self) -> None:
        """Test that duration_ms must be non-negative."""
        # Non-negative values should work
        log = ToolCallLog(
            timestamp="2026-01-03T10:30:00.123Z",
            tool_name="Read",
            duration_ms=0,
        )
        assert log.duration_ms == 0

    def test_tool_name_is_required(self) -> None:
        """Test that tool_name is a required field."""
        with pytest.raises(ValueError):
            ToolCallLog(
                timestamp="2026-01-03T10:30:00.123Z",
                duration_ms=100,
            )  # type: ignore[call-arg]

    def test_timestamp_is_required(self) -> None:
        """Test that timestamp is a required field."""
        with pytest.raises(ValueError):
            ToolCallLog(
                tool_name="Bash",
                duration_ms=100,
            )  # type: ignore[call-arg]

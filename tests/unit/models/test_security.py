"""Tests for security-related Pydantic models.

Verifies BlockedPattern, SecurityConfig, and ToolCallLog models
work correctly with validation and serialization.
"""

import pytest
from pydantic import ValidationError

from adw.models.security import (
    BlockedPattern,
    SecurityConfig,
    ToolCallLog,
)


class TestBlockedPattern:
    """Tests for BlockedPattern model."""

    def test_create_minimal_pattern(self) -> None:
        """Test creating a pattern with minimal required fields."""
        pattern = BlockedPattern(
            pattern=r"rm\s+-rf",
            description="Recursive delete",
            category="destructive",
        )
        assert pattern.pattern == r"rm\s+-rf"
        assert pattern.description == "Recursive delete"
        assert pattern.category == "destructive"
        assert pattern.severity == "warning"  # default
        assert pattern.alternative == ""  # default

    def test_create_full_pattern(self) -> None:
        """Test creating a pattern with all fields."""
        pattern = BlockedPattern(
            pattern=r"chmod\s+777",
            description="World-writable permissions",
            severity="critical",
            category="permission",
            alternative="Use chmod 755 instead",
        )
        assert pattern.pattern == r"chmod\s+777"
        assert pattern.severity == "critical"
        assert pattern.category == "permission"
        assert pattern.alternative == "Use chmod 755 instead"

    def test_valid_categories(self) -> None:
        """Test all valid category values are accepted."""
        valid_categories = [
            "destructive", "permission", "git_dangerous", "secret_access"
        ]

        for category in valid_categories:
            pattern = BlockedPattern(
                pattern=r"test",
                description="Test pattern",
                category=category,  # type: ignore[arg-type]
            )
            assert pattern.category == category

    def test_invalid_category_rejected(self) -> None:
        """Test invalid category values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BlockedPattern(
                pattern=r"test",
                description="Test pattern",
                category="invalid_category",  # type: ignore[arg-type]
            )
        assert "category" in str(exc_info.value)

    def test_valid_severity_levels(self) -> None:
        """Test all valid severity levels are accepted."""
        valid_severities = ["critical", "warning", "info"]

        for severity in valid_severities:
            pattern = BlockedPattern(
                pattern=r"test",
                description="Test pattern",
                category="destructive",
                severity=severity,  # type: ignore[arg-type]
            )
            assert pattern.severity == severity

    def test_invalid_severity_rejected(self) -> None:
        """Test invalid severity values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BlockedPattern(
                pattern=r"test",
                description="Test pattern",
                category="destructive",
                severity="invalid",  # type: ignore[arg-type]
            )
        assert "severity" in str(exc_info.value)

    def test_serialization(self) -> None:
        """Test pattern serializes to dict correctly."""
        pattern = BlockedPattern(
            pattern=r"rm\s+-rf",
            description="Delete recursively",
            severity="critical",
            category="destructive",
            alternative="Use specific paths",
        )
        data = pattern.model_dump()
        assert data["pattern"] == r"rm\s+-rf"
        assert data["description"] == "Delete recursively"
        assert data["severity"] == "critical"
        assert data["category"] == "destructive"
        assert data["alternative"] == "Use specific paths"


class TestSecurityConfig:
    """Tests for SecurityConfig model."""

    def test_default_config(self) -> None:
        """Test creating config with all defaults."""
        config = SecurityConfig()
        assert config.blocked_patterns == []
        assert config.allow_dangerous is False
        assert config.blocked_env_files == []

    def test_config_with_patterns(self) -> None:
        """Test config with custom blocked patterns."""
        pattern = BlockedPattern(
            pattern=r"custom\s+pattern",
            description="Custom blocked pattern",
            category="permission",
        )
        config = SecurityConfig(blocked_patterns=[pattern])
        assert len(config.blocked_patterns) == 1
        assert config.blocked_patterns[0].pattern == r"custom\s+pattern"

    def test_allow_dangerous_flag(self) -> None:
        """Test allow_dangerous configuration."""
        config = SecurityConfig(allow_dangerous=True)
        assert config.allow_dangerous is True

    def test_blocked_env_files(self) -> None:
        """Test custom blocked env file patterns."""
        config = SecurityConfig(blocked_env_files=[r"\.secrets$", r"\.creds$"])
        assert len(config.blocked_env_files) == 2
        assert r"\.secrets$" in config.blocked_env_files


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

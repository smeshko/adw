"""Unit tests for security models."""

from datetime import datetime, timezone

import pytest

from adw.models.security import (
    BlockedPattern,
    SecurityConfig,
    SecuritySeverity,
    ToolCallLog,
)


class TestBlockedPattern:
    """Tests for BlockedPattern model."""

    def test_create_blocked_pattern(self) -> None:
        """Test creating a blocked pattern with all fields."""
        pattern = BlockedPattern(
            pattern=r"rm\s+-rf",
            description="Dangerous recursive delete command",
            severity=SecuritySeverity.CRITICAL,
        )
        assert pattern.pattern == r"rm\s+-rf"
        assert pattern.description == "Dangerous recursive delete command"
        assert pattern.severity == SecuritySeverity.CRITICAL

    def test_blocked_pattern_defaults(self) -> None:
        """Test that blocked pattern has sensible defaults."""
        pattern = BlockedPattern(
            pattern=r"chmod\s+777",
            description="Insecure permissions",
        )
        assert pattern.severity == SecuritySeverity.HIGH

    def test_blocked_pattern_serialization(self) -> None:
        """Test serializing blocked pattern to dict."""
        pattern = BlockedPattern(
            pattern=r"git\s+push\s+--force",
            description="Force push can destroy history",
            severity=SecuritySeverity.MEDIUM,
        )
        data = pattern.model_dump()
        assert data["pattern"] == r"git\s+push\s+--force"
        assert data["description"] == "Force push can destroy history"
        assert data["severity"] == "medium"


class TestSecurityConfig:
    """Tests for SecurityConfig model."""

    def test_create_security_config(self) -> None:
        """Test creating a security config with custom patterns."""
        config = SecurityConfig(
            blocked_patterns=[
                BlockedPattern(
                    pattern=r"rm\s+-rf",
                    description="Recursive delete",
                    severity=SecuritySeverity.CRITICAL,
                )
            ],
            allow_dangerous=False,
            blocked_env_files=[".env", ".adw.env"],
        )
        assert len(config.blocked_patterns) == 1
        assert config.allow_dangerous is False
        assert ".env" in config.blocked_env_files

    def test_security_config_defaults(self) -> None:
        """Test security config has sensible defaults."""
        config = SecurityConfig()
        assert config.allow_dangerous is False
        assert config.blocked_patterns == []
        assert ".env" in config.blocked_env_files
        assert ".adw.env" in config.blocked_env_files

    def test_allowed_env_patterns_default(self) -> None:
        """Test that allowed env patterns are set by default."""
        config = SecurityConfig()
        assert ".env.example" in config.allowed_env_patterns
        assert ".env.sample" in config.allowed_env_patterns
        assert ".env.template" in config.allowed_env_patterns


class TestToolCallLog:
    """Tests for ToolCallLog model."""

    def test_create_tool_call_log(self) -> None:
        """Test creating a tool call log entry."""
        log_entry = ToolCallLog(
            timestamp=datetime(2026, 1, 3, 10, 30, 0, tzinfo=timezone.utc),
            tool_name="Bash",
            arguments={"command": "ls -la"},
            result_summary="success",
            duration_ms=150,
            blocked=False,
            block_reason=None,
        )
        assert log_entry.tool_name == "Bash"
        assert log_entry.arguments == {"command": "ls -la"}
        assert log_entry.duration_ms == 150
        assert log_entry.blocked is False

    def test_create_blocked_tool_call_log(self) -> None:
        """Test creating a blocked tool call log entry."""
        log_entry = ToolCallLog(
            timestamp=datetime(2026, 1, 3, 10, 30, 0, tzinfo=timezone.utc),
            tool_name="Bash",
            arguments={"command": "rm -rf /"},
            result_summary="blocked",
            duration_ms=0,
            blocked=True,
            block_reason="Matches dangerous pattern: rm -rf",
        )
        assert log_entry.blocked is True
        assert log_entry.block_reason == "Matches dangerous pattern: rm -rf"

    def test_tool_call_log_default_timestamp(self) -> None:
        """Test that timestamp defaults to current time."""
        log_entry = ToolCallLog(
            tool_name="Read",
            arguments={"file_path": "/tmp/test.txt"},
            result_summary="success",
            duration_ms=50,
        )
        assert log_entry.timestamp is not None
        assert isinstance(log_entry.timestamp, datetime)

    def test_tool_call_log_json_serialization(self) -> None:
        """Test JSONL-compatible serialization."""
        log_entry = ToolCallLog(
            timestamp=datetime(2026, 1, 3, 10, 30, 0, tzinfo=timezone.utc),
            tool_name="Bash",
            arguments={"command": "rm -rf /tmp/test"},
            result_summary="blocked",
            duration_ms=0,
            blocked=True,
            block_reason="Matches dangerous pattern: rm -rf",
        )
        json_str = log_entry.model_dump_json()
        assert "Bash" in json_str
        assert "blocked" in json_str
        assert "rm -rf" in json_str

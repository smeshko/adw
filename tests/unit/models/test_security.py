"""Tests for security-related Pydantic models.

Verifies BlockedPattern, SecurityConfig, and ToolCallLog models
work correctly with validation and serialization.
"""

from datetime import datetime

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
        valid_categories = ["destructive", "permission", "git_dangerous", "secret_access"]

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
    """Tests for ToolCallLog model."""

    def test_minimal_log(self) -> None:
        """Test creating a log entry with minimal fields."""
        log = ToolCallLog(tool_name="Bash")
        assert log.tool_name == "Bash"
        assert log.blocked is False
        assert log.block_reason is None
        assert log.arguments == {}
        assert log.duration_ms == 0

    def test_blocked_log(self) -> None:
        """Test creating a blocked tool call log."""
        log = ToolCallLog(
            tool_name="Bash",
            arguments={"command": "rm -rf /"},
            result_summary="blocked",
            blocked=True,
            block_reason="Matches dangerous pattern: rm -rf",
        )
        assert log.blocked is True
        assert log.block_reason == "Matches dangerous pattern: rm -rf"
        assert log.result_summary == "blocked"

    def test_successful_log(self) -> None:
        """Test creating a successful tool call log."""
        log = ToolCallLog(
            tool_name="Read",
            arguments={"file_path": "/path/to/file.txt"},
            result_summary="File read successfully (1024 bytes)",
            duration_ms=150,
            blocked=False,
        )
        assert log.blocked is False
        assert log.duration_ms == 150
        assert "successfully" in log.result_summary

    def test_timestamp_auto_generated(self) -> None:
        """Test timestamp is auto-generated."""
        before = datetime.now()
        log = ToolCallLog(tool_name="Test")
        after = datetime.now()
        assert before <= log.timestamp <= after

    def test_explicit_timestamp(self) -> None:
        """Test explicit timestamp is used."""
        explicit_time = datetime(2026, 1, 3, 12, 0, 0)
        log = ToolCallLog(tool_name="Test", timestamp=explicit_time)
        assert log.timestamp == explicit_time

    def test_serialization_to_json(self) -> None:
        """Test log entry serializes to JSON correctly."""
        log = ToolCallLog(
            tool_name="Bash",
            arguments={"command": "ls -la"},
            result_summary="success",
            duration_ms=50,
            blocked=False,
        )
        json_str = log.model_dump_json()
        assert "Bash" in json_str
        assert "ls -la" in json_str
        assert "success" in json_str

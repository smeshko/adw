"""Tests for CLI evidence models.

Tests the Pydantic models used for CLI terminal output capture:
- CommandConfig: Configuration for a single command to execute
- CommandResult: Result of executing a command
- CLIEvidenceSummary: Summary of all command executions
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from adw.models.evidence import (
    CLIEvidenceSummary,
    CommandConfig,
    CommandResult,
)


class TestCommandConfig:
    """Tests for CommandConfig model."""

    def test_create_with_required_fields(self) -> None:
        """CommandConfig should require name and cmd."""
        config = CommandConfig(name="version", cmd="adw --version")
        assert config.name == "version"
        assert config.cmd == "adw --version"
        assert config.timeout == 30  # default

    def test_create_with_custom_timeout(self) -> None:
        """CommandConfig should accept custom timeout."""
        config = CommandConfig(name="build", cmd="npm run build", timeout=120)
        assert config.timeout == 120

    def test_name_required(self) -> None:
        """CommandConfig should require name field."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(cmd="adw --version")  # type: ignore[call-arg]
        assert "name" in str(exc_info.value)

    def test_cmd_required(self) -> None:
        """CommandConfig should require cmd field."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(name="version")  # type: ignore[call-arg]
        assert "cmd" in str(exc_info.value)

    def test_timeout_must_be_positive(self) -> None:
        """CommandConfig timeout must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            CommandConfig(name="test", cmd="echo hi", timeout=0)
        assert "timeout" in str(exc_info.value).lower()

    def test_serialization_to_dict(self) -> None:
        """CommandConfig should serialize to dict."""
        config = CommandConfig(name="help", cmd="adw --help", timeout=60)
        data = config.model_dump()
        assert data == {"name": "help", "cmd": "adw --help", "timeout": 60}


class TestCommandResult:
    """Tests for CommandResult model."""

    def test_create_successful_result(self) -> None:
        """CommandResult should capture successful execution."""
        result = CommandResult(
            command="adw --version",
            exit_code=0,
            stdout="adw version 1.0.0\n",
            stderr="",
            duration_seconds=0.125,
            success=True,
        )
        assert result.command == "adw --version"
        assert result.exit_code == 0
        assert result.stdout == "adw version 1.0.0\n"
        assert result.stderr == ""
        assert result.duration_seconds == 0.125
        assert result.success is True
        assert isinstance(result.executed_at, datetime)

    def test_create_failed_result(self) -> None:
        """CommandResult should capture failed execution."""
        result = CommandResult(
            command="invalid-command",
            exit_code=127,
            stdout="",
            stderr="command not found: invalid-command",
            duration_seconds=0.05,
            success=False,
        )
        assert result.exit_code == 127
        assert result.success is False

    def test_create_timeout_result(self) -> None:
        """CommandResult should handle timeout with exit_code -1."""
        result = CommandResult(
            command="sleep 100",
            exit_code=-1,
            stdout="",
            stderr="Command timed out",
            duration_seconds=30.0,
            success=False,
        )
        assert result.exit_code == -1
        assert result.success is False

    def test_executed_at_default(self) -> None:
        """CommandResult should set executed_at to current time."""
        before = datetime.now(timezone.utc)
        result = CommandResult(
            command="echo test",
            exit_code=0,
            stdout="test",
            stderr="",
            duration_seconds=0.01,
            success=True,
        )
        after = datetime.now(timezone.utc)

        # executed_at should be between before and after
        assert before <= result.executed_at <= after

    def test_custom_executed_at(self) -> None:
        """CommandResult should accept custom executed_at."""
        custom_time = datetime(2026, 1, 3, 10, 30, 45, tzinfo=timezone.utc)
        result = CommandResult(
            command="echo test",
            exit_code=0,
            stdout="test",
            stderr="",
            duration_seconds=0.01,
            success=True,
            executed_at=custom_time,
        )
        assert result.executed_at == custom_time

    def test_serialization_to_json(self) -> None:
        """CommandResult should serialize to JSON."""
        result = CommandResult(
            command="echo hi",
            exit_code=0,
            stdout="hi",
            stderr="",
            duration_seconds=0.05,
            success=True,
        )
        json_str = result.model_dump_json()
        assert '"command":"echo hi"' in json_str
        assert '"exit_code":0' in json_str
        assert '"success":true' in json_str


class TestCLIEvidenceSummary:
    """Tests for CLIEvidenceSummary model."""

    def test_create_empty_summary(self) -> None:
        """CLIEvidenceSummary should handle empty results."""
        summary = CLIEvidenceSummary(
            total_commands=0,
            passed=0,
            failed=0,
            results=[],
        )
        assert summary.total_commands == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.results == []

    def test_create_with_results(self) -> None:
        """CLIEvidenceSummary should store command results."""
        result1 = CommandResult(
            command="echo a",
            exit_code=0,
            stdout="a",
            stderr="",
            duration_seconds=0.01,
            success=True,
        )
        result2 = CommandResult(
            command="false",
            exit_code=1,
            stdout="",
            stderr="",
            duration_seconds=0.02,
            success=False,
        )
        summary = CLIEvidenceSummary(
            total_commands=2,
            passed=1,
            failed=1,
            results=[result1, result2],
        )
        assert summary.total_commands == 2
        assert summary.passed == 1
        assert summary.failed == 1
        assert len(summary.results) == 2

    def test_captured_at_default(self) -> None:
        """CLIEvidenceSummary should set captured_at to current time."""
        before = datetime.now(timezone.utc)
        summary = CLIEvidenceSummary(
            total_commands=0,
            passed=0,
            failed=0,
            results=[],
        )
        after = datetime.now(timezone.utc)
        assert before <= summary.captured_at <= after

    def test_platform_default(self) -> None:
        """CLIEvidenceSummary should default platform to 'cli'."""
        summary = CLIEvidenceSummary(
            total_commands=0,
            passed=0,
            failed=0,
            results=[],
        )
        assert summary.platform == "cli"

    def test_serialization_to_json(self) -> None:
        """CLIEvidenceSummary should serialize to JSON."""
        result = CommandResult(
            command="echo test",
            exit_code=0,
            stdout="test",
            stderr="",
            duration_seconds=0.01,
            success=True,
        )
        summary = CLIEvidenceSummary(
            total_commands=1,
            passed=1,
            failed=0,
            results=[result],
        )
        json_str = summary.model_dump_json()
        assert '"total_commands":1' in json_str
        assert '"passed":1' in json_str
        assert '"failed":0' in json_str
        assert '"platform":"cli"' in json_str

    def test_counts_must_be_non_negative(self) -> None:
        """CLIEvidenceSummary counts must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            CLIEvidenceSummary(
                total_commands=-1,
                passed=0,
                failed=0,
                results=[],
            )
        assert "total_commands" in str(exc_info.value).lower()

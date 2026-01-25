"""Unit tests for global commands CLI.

Tests for the `adw global` command group which provides cross-project
run listing, filtering, and statistics.
"""

from datetime import UTC, datetime, timedelta

import pytest
from typer.testing import CliRunner

from adw.cli.app import app
from adw.cli.global_commands import parse_duration

runner = CliRunner()


class TestGlobalCommandGroup:
    """Tests for the global command group registration."""

    def test_global_help_shows_command_group(self) -> None:
        """The global command group should be registered and show help."""
        result = runner.invoke(app, ["global", "--help"])
        assert result.exit_code == 0
        assert "Cross-project commands" in result.output

    def test_global_list_command_exists(self) -> None:
        """The global list command should be registered."""
        result = runner.invoke(app, ["global", "list", "--help"])
        assert result.exit_code == 0
        assert "List runs across all projects" in result.output


class TestParseDuration:
    """Tests for duration string parsing."""

    def test_parse_days(self) -> None:
        """7d should return datetime approximately 7 days ago."""
        result = parse_duration("7d")
        expected = datetime.now(UTC) - timedelta(days=7)
        # Allow 1 second tolerance for test execution time
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_hours(self) -> None:
        """24h should return datetime approximately 24 hours ago."""
        result = parse_duration("24h")
        expected = datetime.now(UTC) - timedelta(hours=24)
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_weeks(self) -> None:
        """2w should return datetime approximately 14 days ago."""
        result = parse_duration("2w")
        expected = datetime.now(UTC) - timedelta(weeks=2)
        assert abs((result - expected).total_seconds()) < 1

    def test_parse_minutes(self) -> None:
        """30m should return datetime approximately 30 minutes ago."""
        result = parse_duration("30m")
        expected = datetime.now(UTC) - timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 1

    def test_invalid_format_raises_value_error(self) -> None:
        """Invalid format should raise ValueError with helpful message."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("invalid")

    def test_missing_unit_raises_value_error(self) -> None:
        """Number without unit should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("7")

    def test_missing_number_raises_value_error(self) -> None:
        """Unit without number should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("d")

    def test_case_insensitive(self) -> None:
        """Duration parsing should be case insensitive."""
        result_lower = parse_duration("7d")
        result_upper = parse_duration("7D")
        # Both should be approximately equal (within 1 second)
        assert abs((result_lower - result_upper).total_seconds()) < 1

    def test_invalid_unit_raises_value_error(self) -> None:
        """Unknown unit should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid duration format"):
            parse_duration("7x")

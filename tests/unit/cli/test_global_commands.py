"""Unit tests for global commands CLI.

Tests for the `adw global` command group which provides cross-project
run listing, filtering, and statistics.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

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


class TestGlobalListCommand:
    """Tests for the global list command functionality."""

    def test_list_with_invalid_status_shows_error(self) -> None:
        """Invalid status value should show error message."""
        result = runner.invoke(app, ["global", "list", "--status", "invalid"])
        assert result.exit_code == 1
        assert "Invalid status" in result.output

    def test_list_with_invalid_since_shows_error(self) -> None:
        """Invalid since duration should show error message."""
        result = runner.invoke(app, ["global", "list", "--since", "invalid"])
        assert result.exit_code == 1
        assert "Invalid duration format" in result.output

    def test_list_help_shows_all_options(self) -> None:
        """Help should show all available options."""
        result = runner.invoke(app, ["global", "list", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output
        assert "--status" in result.output
        assert "--since" in result.output
        assert "--limit" in result.output
        assert "--offset" in result.output
        assert "--json" in result.output


class TestDashboardCommand:
    """Tests for the global dashboard command."""

    def test_dashboard_command_exists(self) -> None:
        """The dashboard command should be registered."""
        result = runner.invoke(app, ["global", "dashboard", "--help"])
        assert result.exit_code == 0
        assert "Launch the interactive TUI dashboard" in result.output

    def test_dashboard_help_shows_all_options(self) -> None:
        """Help should show all available options."""
        result = runner.invoke(app, ["global", "dashboard", "--help"])
        assert result.exit_code == 0
        assert "--refresh" in result.output
        assert "--project" in result.output
        assert "--no-auto-refresh" in result.output

    def test_dashboard_help_shows_keyboard_shortcuts(self) -> None:
        """Help should document keyboard shortcuts."""
        result = runner.invoke(app, ["global", "dashboard", "--help"])
        assert result.exit_code == 0
        # Check that keyboard shortcuts are documented
        assert "q" in result.output.lower() or "quit" in result.output.lower()

    @patch("adw.cli.dashboard.run_dashboard")
    def test_dashboard_calls_run_dashboard(self, mock_run: "MagicMock") -> None:
        """Dashboard command should call run_dashboard function."""
        result = runner.invoke(app, ["global", "dashboard"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            refresh_interval=30,
            project_filter=None,
            no_auto_refresh=False,
        )

    @patch("adw.cli.dashboard.run_dashboard")
    def test_dashboard_with_refresh_option(self, mock_run: "MagicMock") -> None:
        """Dashboard should pass refresh interval to run_dashboard."""
        result = runner.invoke(app, ["global", "dashboard", "--refresh", "60"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            refresh_interval=60,
            project_filter=None,
            no_auto_refresh=False,
        )

    @patch("adw.cli.dashboard.run_dashboard")
    def test_dashboard_with_project_filter(self, mock_run: "MagicMock") -> None:
        """Dashboard should pass project filter to run_dashboard."""
        result = runner.invoke(app, ["global", "dashboard", "--project", "my-api"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            refresh_interval=30,
            project_filter="my-api",
            no_auto_refresh=False,
        )

    @patch("adw.cli.dashboard.run_dashboard")
    def test_dashboard_with_no_auto_refresh(self, mock_run: "MagicMock") -> None:
        """Dashboard should pass no-auto-refresh flag to run_dashboard."""
        result = runner.invoke(app, ["global", "dashboard", "--no-auto-refresh"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            refresh_interval=30,
            project_filter=None,
            no_auto_refresh=True,
        )

    @patch("adw.cli.dashboard.run_dashboard")
    def test_dashboard_with_all_options(self, mock_run: "MagicMock") -> None:
        """Dashboard should handle all options together."""
        result = runner.invoke(
            app,
            [
                "global",
                "dashboard",
                "--refresh",
                "120",
                "--project",
                "test-proj",
                "--no-auto-refresh",
            ],
        )
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            refresh_interval=120,
            project_filter="test-proj",
            no_auto_refresh=True,
        )

    @patch("adw.cli.dashboard.run_dashboard")
    def test_dashboard_short_option_aliases(self, mock_run: "MagicMock") -> None:
        """Dashboard should accept short option aliases."""
        result = runner.invoke(app, ["global", "dashboard", "-r", "45", "-p", "api"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            refresh_interval=45,
            project_filter="api",
            no_auto_refresh=False,
        )

    def test_dashboard_refresh_min_validation(self) -> None:
        """Dashboard should reject refresh interval below minimum."""
        result = runner.invoke(app, ["global", "dashboard", "--refresh", "1"])
        # Typer should reject values below min=5
        assert result.exit_code != 0

    def test_dashboard_refresh_max_validation(self) -> None:
        """Dashboard should reject refresh interval above maximum."""
        result = runner.invoke(app, ["global", "dashboard", "--refresh", "500"])
        # Typer should reject values above max=300
        assert result.exit_code != 0

    @patch("adw.cli.dashboard.run_dashboard")
    def test_dashboard_handles_keyboard_interrupt(self, mock_run: "MagicMock") -> None:
        """Dashboard should handle KeyboardInterrupt gracefully."""
        mock_run.side_effect = KeyboardInterrupt()
        result = runner.invoke(app, ["global", "dashboard"])
        # Should exit cleanly with code 0
        assert result.exit_code == 0
        assert "Dashboard closed" in result.output
